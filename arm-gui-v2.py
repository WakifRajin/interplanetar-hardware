import sys
import numpy as np
import threading
import websocket
import json
import logging
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QGroupBox, QMainWindow, QButtonGroup
)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.setWindowTitle("Arm Control GUI")
        self.setGeometry(100, 100, 1280, 720)

        # Control variables
        self.gripper_state = 0  # 0: stop, 1: close, 2: open
        self.roller_state = 0   # 0: stop, 1: close, 2: open
        self.servo_angle = 90
        self.elbow_pwm = 0
        self.shoulder_pwm = 0
        self.base_pwm = 0
        self.shared_pwm = 0
        self.last_values = None

        # Motor states (0: stop, 1: forward, 2: backward)
        self.base_state = 0
        self.shoulder_state = 0
        self.elbow_state = 0

        # WebSocket client setup
        self.ws = None
        self.ws_connected = False
        self.setup_websocket_client()

        # GUI setup
        self.detached_window = None
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)

        self.init_controls()
        self.init_plot()

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_output)
        self.timer.start(50)  # Update every 50ms

    def setup_websocket_client(self):
        """Setup WebSocket client to connect to the main server"""
        def on_message(ws, message):
            try:
                if message.startswith('[') or message.startswith('{'):
                    data = json.loads(message)
                    logger.info(f"Received from server: {data}")
                else:
                    logger.info(f"Received: {message}")
            except json.JSONDecodeError:
                logger.info(f"Received text: {message}")

        def on_open(ws):
            logger.info("✅ Connected to WebSocket server")
            self.ws_connected = True
            ws.send("ARM GUI Connected!")

        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
            self.ws_connected = False

        def on_close(ws, close_status_code, close_msg):
            logger.info("Disconnected from WebSocket server")
            self.ws_connected = False

        def connect_websocket():
            while True:
                try:
                    logger.info("Attempting to connect to WebSocket server...")
                    self.ws = websocket.WebSocketApp(
                        "ws://192.168.0.101:8765",  # Connect to main server
                        on_open=on_open,
                        on_message=on_message,
                        on_error=on_error,
                        on_close=on_close
                    )
                    self.ws.run_forever()
                    
                    # If we get here, connection was closed
                    if hasattr(self, 'shutting_down') and self.shutting_down:
                        break
                        
                    logger.info("Attempting to reconnect in 5 seconds...")
                    threading.Event().wait(5)  # Sleep for 5 seconds
                    
                except Exception as e:
                    logger.error(f"Connection error: {e}")
                    threading.Event().wait(5)

        # Start WebSocket client in background thread
        self.ws_thread = threading.Thread(target=connect_websocket, daemon=True)
        self.ws_thread.start()

    def send_websocket_message(self, message):
        """Send message through WebSocket if connected"""
        if self.ws_connected and self.ws:
            try:
                if isinstance(message, (list, dict)):
                    message = json.dumps(message)
                self.ws.send(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                self.ws_connected = False
        return False

    def init_controls(self):
        control_panel = QVBoxLayout()
        control_panel.setAlignment(Qt.AlignTop)

        # Add connection status
        self.status_label = QLabel("🔴 Disconnected")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
        control_panel.addWidget(self.status_label)

        # Shared PWM slider for base, shoulder, and elbow motors
        control_panel.addWidget(self.create_pwm_slider("Shared Motor PWM", lambda val: setattr(self, 'shared_pwm', val), 0, 1023))
        
        # Motor control sections
        control_panel.addWidget(self.create_motor_control("Base Motor", 'base'))
        control_panel.addWidget(self.create_motor_control("Shoulder Motor", 'shoulder'))
        control_panel.addWidget(self.create_motor_control("Elbow Motor", 'elbow'))
        
        # Servo control
        control_panel.addWidget(self.create_pwm_slider("Wrist Servo (0-180°)", lambda val: setattr(self, 'servo_angle', val), 0, 180))
        
        # Gripper and Roller controls
        control_panel.addWidget(self.create_gripper_roller_control("Gripper", 'gripper'))
        control_panel.addWidget(self.create_gripper_roller_control("Roller", 'roller'))

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
            QWidget { background-color: #f4f4f4; font-family: 'Segoe UI', Arial; font-size: 12pt; }
            QGroupBox { border: 1px solid #cccccc; border-radius: 8px; margin-top: 1.5ex; padding: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { background-color: #2b2d42; color: white; border-radius: 8px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #1f2235; }
            QPushButton:checked { background-color: #4a4d6d; }
            QSlider::groove:horizontal { background: #cccccc; height: 10px; border-radius: 5px; }
            QSlider::handle:horizontal { background: #2b2d42; width: 30px; height: 30px; border-radius: 15px; margin: -10px 0; }
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

    def create_pwm_slider(self, label, callback, min_val=0, max_val=1023):
        group = QGroupBox(label)
        layout = QVBoxLayout()
        
        # Add value label
        value_label = QLabel(f"{(min_val + max_val) // 2}")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet("font-weight: bold; color: #2b2d42;")
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue((min_val + max_val) // 2)
        slider.setMinimumHeight(35)
        
        def on_value_change(val):
            value_label.setText(str(val))
            callback(val)
        
        slider.valueChanged.connect(on_value_change)
        
        layout.addWidget(value_label)
        layout.addWidget(slider)
        group.setLayout(layout)
        return group

    def create_motor_control(self, name, motor_type):
        group = QGroupBox(name)
        layout = QHBoxLayout()
        
        # Forward button
        fwd_btn = QPushButton("FWD")
        fwd_btn.setCheckable(True)
        fwd_btn.setMinimumHeight(40)
        fwd_btn.clicked.connect(lambda: self.set_motor_state(motor_type, 1))
        
        # Backward button
        bwd_btn = QPushButton("BWD")
        bwd_btn.setCheckable(True)
        bwd_btn.setMinimumHeight(40)
        bwd_btn.clicked.connect(lambda: self.set_motor_state(motor_type, 2))
        
        # Create button group for exclusive selection
        btn_group = QButtonGroup(group)
        btn_group.addButton(fwd_btn, 1)
        btn_group.addButton(bwd_btn, 2)
        btn_group.setExclusive(True)
        
        layout.addWidget(fwd_btn)
        layout.addWidget(bwd_btn)
        group.setLayout(layout)
        return group

    def create_gripper_roller_control(self, name, control_type):
        group = QGroupBox(name)
        layout = QHBoxLayout()
        
        # Open button
        open_btn = QPushButton("Open")
        open_btn.setCheckable(True)
        open_btn.setMinimumHeight(40)
        open_btn.clicked.connect(lambda: self.set_gripper_roller_state(control_type, 2))
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setCheckable(True)
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(lambda: self.set_gripper_roller_state(control_type, 1))
        
        # Stop button
        stop_btn = QPushButton("Stop")
        stop_btn.setCheckable(True)
        stop_btn.setMinimumHeight(40)
        stop_btn.clicked.connect(lambda: self.set_gripper_roller_state(control_type, 0))
        
        # Create button group for exclusive selection
        btn_group = QButtonGroup(group)
        btn_group.addButton(open_btn, 2)
        btn_group.addButton(close_btn, 1)
        btn_group.addButton(stop_btn, 0)
        btn_group.setExclusive(True)
        stop_btn.setChecked(True)  # Default to stop
        
        layout.addWidget(open_btn)
        layout.addWidget(close_btn)
        layout.addWidget(stop_btn)
        group.setLayout(layout)
        return group

    def set_motor_state(self, motor_type, state):
        if motor_type == 'base':
            self.base_state = state
        elif motor_type == 'shoulder':
            self.shoulder_state = state
        elif motor_type == 'elbow':
            self.elbow_state = state

    def set_gripper_roller_state(self, control_type, state):
        if control_type == 'gripper':
            self.gripper_state = state
        elif control_type == 'roller':
            self.roller_state = state

    def get_direction_and_value(self, state):
        if state == 1:  # Forward
            return [1, self.shared_pwm]
        elif state == 2:  # Backward
            return [0, self.shared_pwm]
        else:  # Stop
            return [0, 0]

    def get_current_values(self):
        return [
            self.gripper_state,
            self.roller_state,
            self.servo_angle,
            self.get_direction_and_value(self.elbow_state),
            self.get_direction_and_value(self.shoulder_state),
            self.get_direction_and_value(self.base_state),
        ]

    def reset_all(self):
        # Reset motor states
        self.base_state = 0
        self.shoulder_state = 0
        self.elbow_state = 0
        
        # Reset gripper and roller states
        self.gripper_state = 0
        self.roller_state = 0
        
        # Reset servo angle
        self.servo_angle = 90
        
        # Reset PWM values
        self.shared_pwm = 0
        
        # Reset UI components
        for widget in self.findChildren(QSlider):
            if widget.minimum() == 0 and widget.maximum() == 180:  # Servo slider
                widget.setValue(90)
            else:  # PWM sliders
                widget.setValue(0)
        
        # Reset button groups
        for btn_group in self.findChildren(QButtonGroup):
            btn_group.setExclusive(False)
            for button in btn_group.buttons():
                button.setChecked(False)
            btn_group.setExclusive(True)
            
            # Set stop buttons to checked
            for button in btn_group.buttons():
                if btn_group.id(button) == 0:
                    button.setChecked(True)

    def update_output(self):
        values = self.get_current_values()
        
        # Update connection status
        if self.ws_connected:
            self.status_label.setText("🟢 Connected")
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px; color: green;")
        else:
            self.status_label.setText("🔴 Disconnected") 
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px; color: red;")
        
        # Only send and update if values changed
        if values != self.last_values:
            print(f"ARM Values: {values}")
            
            # Send via WebSocket
            self.send_websocket_message(values)
            
            # Update plot
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
        self.ax.plot([x0, x1, x2, x3], [y0, y1, y2, y3], [z0, z1, z2, z3], 
                    color='#3f72af', marker='o', linewidth=3, markersize=8)
        
        # Add joint labels
        self.ax.text(x0, y0, z0, 'Base', fontsize=8)
        self.ax.text(x1, y1, z1, 'Shoulder', fontsize=8)
        self.ax.text(x2, y2, z2, 'Elbow', fontsize=8)
        self.ax.text(x3, y3, z3, 'Wrist', fontsize=8)
        
        # Set limits and labels
        self.ax.set_xlim(-30, 30)
        self.ax.set_ylim(-30, 30)
        self.ax.set_zlim(0, 50)
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_zlabel("Z")
        self.ax.set_title("3D Arm Position")
        self.ax.grid(True)
        self.canvas.draw()

    def closeEvent(self, event):
        """Clean shutdown when GUI is closed"""
        logger.info("Shutting down ARM Control GUI...")
        self.shutting_down = True
        
        if self.ws_connected and self.ws:
            try:
                self.ws.send("ARM GUI Disconnecting...")
                self.ws.close()
            except:
                pass
        
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ArmControlGUI()
    window.show()
    sys.exit(app.exec_())
