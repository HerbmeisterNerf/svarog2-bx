"""Bench test: B-G431B-ESC1 (SimpleFOC) motor over the Radxa motor UART.

Standalone Phase-1 bring-up. Drives MotorController over RADXA_UART_INTERFACE:
sets velocity mode + safe limits, ramps the target, prints the TEL telemetry the
firmware streams back, then stops. Confirms the Radxa <-> ESC UART link and that
the Commander protocol reaches the motor before wiring into flight code.

PRE-REQ: the ESC firmware's Commander/telemetry must be on the physical UART
wired to the Radxa (not only the ST-Link USB VCP). See rspro-bldc-foc/src/main.cpp
`Commander command = Commander(Serial)` — may need binding to a HardwareSerial.

Run on the board:  python3 motor_uart_test.py [--uart 1] [--target 6]
SAFETY: shaft will spin. Ensure the motor is clamped and clear.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from RADXA_UART_INTERFACE import UARTInterface
from motor_interface import MotorController


def main():
    ap = argparse.ArgumentParser(description="ESC1 SimpleFOC motor UART bench test")
    ap.add_argument("--uart", type=int, default=1, help="mraa UART id (default 1)")
    ap.add_argument("--target", type=float, default=6.0, help="velocity rad/s")
    ap.add_argument("--seconds", type=float, default=5.0, help="run duration")
    ap.add_argument("--vlimit", type=float, default=3.0, help="voltage limit V")
    ap.add_argument("--climit", type=float, default=1.2, help="current limit A")
    args = ap.parse_args()

    uart = UARTInterface(uart_id=args.uart, baudrate=115200)
    motor = MotorController(uart, name="bench")

    print(f"UART{args.uart} @115200. Setting velocity mode + limits...")
    motor.set_mode("velocity")
    time.sleep(0.1)
    motor.set_limits(voltage=args.vlimit, current=args.climit)
    time.sleep(0.2)

    # Read a few telemetry frames at idle first (proves the link both ways).
    print("Idle telemetry (target 0):")
    for _ in range(5):
        print("  ", motor.get_telemetry(timeout=0.5))
        time.sleep(0.2)

    try:
        print(f"\nSpinning: target {args.target} rad/s for {args.seconds}s")
        motor.set_target(args.target)
        t_end = time.time() + args.seconds
        while time.time() < t_end:
            tel = motor.get_telemetry(timeout=0.5)
            if tel:
                print(f"  vel={tel['velocity']:7.3f} rad/s  angle={tel['angle']:8.3f}  "
                      f"cur={tel['current']:.3f}A  target={tel['target']}")
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopping (T0)...")
        motor.stop()
        time.sleep(0.3)
        motor.close()
        print("done.")


if __name__ == "__main__":
    main()
