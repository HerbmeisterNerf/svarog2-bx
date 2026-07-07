import mraa
import time
import sys

class PWMHeater:
    def __init__(self, pwm_pin, freq_hz=1000):
        self.pwm = mraa.Pwm(pwm_pin)
        self.duty = 0.0
        self.freq_hz = freq_hz
        if self.pwm is None:
            raise RuntimeError(f"Failed to open PWM on pin {pwm_pin}")
        period_us = int(1e6 / freq_hz)
        if self.pwm.period_us(period_us) != mraa.SUCCESS:
            self.pwm.close()
            raise RuntimeError(f"Failed to set PWM period {period_us}us")
        if self.pwm.enable(True) != mraa.SUCCESS:
            self.pwm.close()
            raise RuntimeError("Failed to enable PWM")

    def set_duty(self, duty):
        self.duty = max(0.0, min(1.0, duty))
        self.pwm.write(self.duty)

    def close(self):
        self.pwm.write(0)
        self.pwm.disable()
        self.pwm.close()


class PIDController:
    def __init__(self, kp=1.0, ki=0.0, kd=0.0, setpoint=0.0, output_limits=(0.0, 1.0)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, measured, dt):
        error = self.setpoint - measured
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        lo, hi = self.output_limits
        return max(lo, min(hi, output))

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0


def open_loop_test(heater, high_duty=1.0, low_duty=0.0, high_sec=2, low_sec=8):
    print(f"Open loop: {high_duty:.2f} for {high_sec}s, {low_duty:.2f} for {low_sec}s")
    try:
        while True:
            heater.set_duty(high_duty)
            print(f"[ON ] duty={heater.duty:.3f}")
            time.sleep(high_sec)
            heater.set_duty(low_duty)
            print(f"[OFF] duty={heater.duty:.3f}")
            time.sleep(low_sec)
    except KeyboardInterrupt:
        pass


def sweep_test(heater, step=0.05, interval=0.5):
    print(f"Sweeping duty cycle 0.0 -> 1.0 -> 0.0 (step={step})")
    try:
        while True:
            for d in [i * step for i in range(int(1 / step) + 1)] + \
                     [i * step for i in range(int(1 / step) - 1, -1, -1)]:
                heater.set_duty(d)
                print(f"duty={heater.duty:.3f}")
                time.sleep(interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    pwm_pin = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    mode = sys.argv[2] if len(sys.argv) > 2 else "open"
    heater = PWMHeater(pwm_pin, freq_hz=1000)
    try:
        if mode == "sweep":
            sweep_test(heater)
        elif mode == "closed":
            kp = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
            setpoint = float(sys.argv[4]) if len(sys.argv) > 4 else 30.0
            pid = PIDController(kp=kp, setpoint=setpoint)
            print(f"Closed loop PID (kp={kp}, setpoint={setpoint}C)")
            print("Enter measured temp on stdin, or 'q' to quit")
            while True:
                line = input("temp> ").strip()
                if line == "q":
                    break
                try:
                    measured = float(line)
                    duty = pid.update(measured, dt=1.0)
                    heater.set_duty(duty)
                    print(f"  duty={duty:.3f}")
                except ValueError:
                    print("  invalid")
        else:
            high_duty = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
            high_sec = float(sys.argv[4]) if len(sys.argv) > 4 else 2
            low_sec = float(sys.argv[5]) if len(sys.argv) > 5 else 8
            open_loop_test(heater, high_duty, 0.0, high_sec, low_sec)
    finally:
        heater.close()
        print("PWM stopped")
