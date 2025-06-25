import tkinter as tk
from tkinter import ttk

class ArmControlGUI:
    def __init__(self, root):
        self.root = root
        root.title("Arm Control GUI")
        root.geometry("600x700")

        self.output_label = tk.Label(root, text="Output: ", font=("Helvetica", 14), fg="blue")
        self.output_label.pack(pady=10)

        # Variables
        self.gripper_state = tk.BooleanVar(value=False)
        self.roller_state = tk.BooleanVar(value=False)
        self.servo_angle = tk.IntVar(value=90)
        self.elbow_pwm = tk.IntVar(value=0)
        self.shoulder_pwm = tk.IntVar(value=0)
        self.base_pwm = tk.IntVar(value=0)

        # Components
        self.create_pwm_slider("Elbow", self.elbow_pwm)
        self.create_pwm_slider("Shoulder", self.shoulder_pwm)
        self.create_pwm_slider("Base", self.base_pwm)

        self.create_gripper_control()
        self.create_roller_control()
        self.create_servo_control()

        # Start continuous update
        self.update_output_loop()

    def create_pwm_slider(self, name, var):
        frame = tk.LabelFrame(self.root, text=name.upper(), padx=10, pady=5)
        frame.pack(fill="x", padx=20, pady=5)

        slider = tk.Scale(frame, from_=-1023, to=1023, variable=var, orient="horizontal", length=400, resolution=1)
        slider.pack()
        label = tk.Label(frame, text=f"{name} PWM")
        label.pack()

    def create_gripper_control(self):
        frame = tk.LabelFrame(self.root, text="GRIPPER", padx=10, pady=5)
        frame.pack(fill="x", padx=20, pady=5)

        self.gripper_label = tk.Label(frame, text="OFF", font=("Helvetica", 12), fg="red")
        self.gripper_label.pack()

        on_btn = ttk.Button(frame, text="Toggle ON/OFF", command=self.toggle_gripper)
        on_btn.pack()

    def toggle_gripper(self):
        current = self.gripper_state.get()
        new_state = not current
        self.gripper_state.set(new_state)
        self.gripper_label.config(text="ON" if new_state else "OFF", fg="green" if new_state else "red")

    def create_roller_control(self):
        frame = tk.LabelFrame(self.root, text="ROLLER", padx=10, pady=5)
        frame.pack(fill="x", padx=20, pady=5)

        self.roller_label = tk.Label(frame, text="OFF", font=("Helvetica", 12), fg="red")
        self.roller_label.pack()

        on_btn = ttk.Button(frame, text="Toggle ON/OFF", command=self.toggle_roller)
        on_btn.pack()

    def toggle_roller(self):
        current = self.roller_state.get()
        new_state = not current
        self.roller_state.set(new_state)
        self.roller_label.config(text="ON" if new_state else "OFF", fg="green" if new_state else "red")

    def create_servo_control(self):
        frame = tk.LabelFrame(self.root, text="SERVO (Wrist)", padx=10, pady=5)
        frame.pack(fill="x", padx=20, pady=5)

        slider = ttk.Scale(frame, from_=0, to=180, orient="horizontal", variable=self.servo_angle)
        slider.pack(fill="x", padx=5)
        label = tk.Label(frame, text="0–180°")
        label.pack()

    def get_direction_and_value(self, pwm):
        if pwm > 0:
            return [1, pwm]
        elif pwm < 0:
            return [0, abs(pwm)]
        else:
            return [0, 0]

    def get_current_values(self):
        gripper = 1 if self.gripper_state.get() else 0
        roller = 1 if self.roller_state.get() else 0
        wrist = self.servo_angle.get()

        elbow = self.get_direction_and_value(self.elbow_pwm.get())
        shoulder = self.get_direction_and_value(self.shoulder_pwm.get())
        base = self.get_direction_and_value(self.base_pwm.get())

        result = [gripper, roller, wrist, elbow, shoulder, base]
        return result

    def update_output_loop(self):
        result = self.get_current_values()
        print(result)
        self.output_label.config(text=f"Output: {result}")
        self.root.after(100, self.update_output_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = ArmControlGUI(root)
    root.mainloop()
