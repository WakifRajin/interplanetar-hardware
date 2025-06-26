import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QCheckBox, QGroupBox, QMainWindow
)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Arm segment lengths
L1, L2, L3 = 10, 10, 5

class DetachedPlotWindow(QMainWindow):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.setWindowTitle("Detached Plot")
        self.setGeometry(300, 300, 600, 600)
        self.setCentralWidget(gui.canvas)
        
    def closeEvent(self, event):
        self.gui.reattach_plot()
        event.accept()

class ArmControlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Professional Arm Control GUI")
        self.setGeometry(100, 100, 1280, 720)

        self.gripper_state = False
        self.roller_state = False
        self.servo_angle = 90
        self.elbow_pwm = 0
        self.shoulder_pwm = 0
        self.base_pwm = 0
        self.last_values = None

        self.detached_window = None

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)

        self.init_controls()
        self.init_plot()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_output)
        self.timer.start(50)  # Update every 50ms

    def init_controls(self):
        control_panel = QVBoxLayout()
        control_panel.setAlignment(Qt.AlignTop)

        control_panel.addWidget(self.create_pwm_slider("Base", lambda val: setattr(self, 'base_pwm', val)))
        control_panel.addWidget(self.create_pwm_slider("Shoulder", lambda val: setattr(self, 'shoulder_pwm', val)))
        control_panel.addWidget(self.create_pwm_slider("Elbow", lambda val: setattr(self, 'elbow_pwm', val)))
        control_panel.addWidget(self.create_pwm_slider("Wrist Servo (0-180°)", lambda val: setattr(self, 'servo_angle', val), 0, 180))
        control_panel.addWidget(self.create_toggle("Gripper", lambda: self.toggle_state('gripper_state')))
        control_panel.addWidget(self.create_toggle("Roller", lambda: self.toggle_state('roller_state')))

        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset")
        reset_btn.setMinimumHeight(40)
        reset_btn.clicked.connect(self.reset_all)

        self.detach_btn = QPushButton("Detach Plot")
        self.detach_btn.setMinimumHeight(40)
        self.detach_btn.clicked.connect(self.toggle_plot_detach)

        btn_layout.addWidget(reset_btn)
        btn_layout.addWidget(self.detach_btn)
        control_panel.addLayout(btn_layout)

        wrapper = QWidget()
        wrapper.setLayout(control_panel)
        wrapper.setStyleSheet("""
            QWidget { 
                background-color: #f4f4f4; 
                font-family: 'Segoe UI', Arial; 
                font-size: 12pt; 
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 8px;
                margin-top: 1.5ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton { 
                background-color: #2b2d42; 
                color: white; 
                border-radius: 8px; 
                padding: 8px; 
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #1f2235; 
            }
            QSlider::groove:horizontal {
                background: #cccccc;
                height: 10px;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #2b2d42;
                width: 30px;
                height: 30px;
                border-radius: 15px;
                margin: -10px 0;
            }
        """)

        self.main_layout.addWidget(wrapper, 4)

    def init_plot(self):
        self.figure = Figure(figsize=(6, 6))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.main_layout.addWidget(self.canvas, 5)

    def reattach_plot(self):
        if self.detached_window:
            self.detached_window.close()
            self.detached_window = None
            self.main_layout.addWidget(self.canvas, 5)
            self.detach_btn.setText("Detach Plot")

    def toggle_plot_detach(self):
        if self.detached_window:
            self.reattach_plot()
        else:
            self.main_layout.removeWidget(self.canvas)
            self.detached_window = DetachedPlotWindow(self)
            self.detached_window.show()
            self.detach_btn.setText("Attach Plot")

    def create_pwm_slider(self, label, callback, min_val=-1023, max_val=1023):
        group = QGroupBox(label)
        layout = QVBoxLayout()

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue((min_val + max_val) // 2)
        slider.setMinimumHeight(35)
        slider.valueChanged.connect(callback)
        layout.addWidget(slider)

        group.setLayout(layout)
        return group

    def create_toggle(self, name, callback):
        box = QGroupBox(name)
        layout = QVBoxLayout()
        checkbox = QCheckBox("ON")
        checkbox.setStyleSheet("font-weight: bold;")
        checkbox.stateChanged.connect(callback)
        layout.addWidget(checkbox)
        box.setLayout(layout)
        return box

    def toggle_state(self, attr):
        setattr(self, attr, not getattr(self, attr))

    def get_direction_and_value(self, pwm):
        return [1, pwm] if pwm > 0 else ([0, -pwm] if pwm < 0 else [0, 0])

    def get_current_values(self):
        return [
            int(self.gripper_state),
            int(self.roller_state),
            self.servo_angle,
            self.get_direction_and_value(self.elbow_pwm),
            self.get_direction_and_value(self.shoulder_pwm),
            self.get_direction_and_value(self.base_pwm),
        ]

    def reset_all(self):
        self.gripper_state = False
        self.roller_state = False
        self.servo_angle = 90
        self.elbow_pwm = 0
        self.shoulder_pwm = 0
        self.base_pwm = 0

    def update_output(self):
        values = self.get_current_values()
        print(values)  # Print every 50ms regardless of changes
        
        if values != self.last_values:
            self.update_plot(values)
            self.last_values = values

    def update_plot(self, values):
        _, _, wrist, elbow, shoulder, base = values
        base_angle = (base[0]*2 - 1) * (base[1] / 1023) * 90
        shoulder_angle = (shoulder[0]*2 - 1) * (shoulder[1] / 1023) * 90
        elbow_angle = (elbow[0]*2 - 1) * (elbow[1] / 1023) * 90

        x0, y0, z0 = 0, 0, 0
        x1 = L1 * np.cos(np.radians(base_angle)) * np.cos(np.radians(shoulder_angle))
        y1 = L1 * np.sin(np.radians(base_angle)) * np.cos(np.radians(shoulder_angle))
        z1 = L1 * np.sin(np.radians(shoulder_angle))

        x2 = x1 + L2 * np.cos(np.radians(base_angle)) * np.cos(np.radians(shoulder_angle + elbow_angle))
        y2 = y1 + L2 * np.sin(np.radians(base_angle)) * np.cos(np.radians(shoulder_angle + elbow_angle))
        z2 = z1 + L2 * np.sin(np.radians(shoulder_angle + elbow_angle))

        x3 = x2 + L3 * np.cos(np.radians(base_angle)) * np.cos(np.radians(wrist))
        y3 = y2 + L3 * np.sin(np.radians(base_angle)) * np.cos(np.radians(wrist))
        z3 = z2 + L3 * np.sin(np.radians(wrist))

        self.ax.cla()
        self.ax.plot([x0, x1, x2, x3], [y0, y1, y2, y3], [z0, z1, z2, z3], color='#3f72af', marker='o', linewidth=3)
        self.ax.text(x0, y0, z0, 'Base')
        self.ax.text(x1, y1, z1, 'Shoulder')
        self.ax.text(x2, y2, z2, 'Elbow')
        self.ax.text(x3, y3, z3, 'Wrist')
        self.ax.set_xlim(-30, 30)
        self.ax.set_ylim(-30, 30)
        self.ax.set_zlim(0, 50)
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_zlabel("Z")
        self.ax.set_title("3D Arm Position")
        self.ax.grid(True)
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ArmControlGUI()
    window.show()
    sys.exit(app.exec_())
