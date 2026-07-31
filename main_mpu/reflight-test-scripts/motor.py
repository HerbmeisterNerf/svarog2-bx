#!/usr/bin/env python3
import subprocess, time, sys, os

UART = "/dev/ttyS7"

def uart_write(cmd):
    subprocess.run(["sh", "-c", f'echo "{cmd}" > {UART}'],
                   check=True, timeout=2)

def uart_read(timeout=1.0):
    try:
        r = subprocess.run(["timeout", str(timeout), "cat", UART],
                           capture_output=True, text=True, timeout=timeout + 0.5)
        return r.stdout.strip() if r.stdout else None
    except subprocess.TimeoutExpired:
        return None

def cmd(cmd_str, read=True, timeout=1.0):
    uart_write(cmd_str)
    time.sleep(0.05)
    if read:
        return uart_read(timeout)

def ping():
    return cmd("PING")

def set_mode(mode):
    return cmd(f"TC{mode}")

def set_current(val):
    return cmd(f"C{val}")

def set_speed(speed):
    return cmd(f"T{speed}")

def get_status():
    return cmd("GS")

def enable_motor():
    return cmd("SM1")

def disable_motor():
    return cmd("SM0")

def ce():
    return cmd("CE")

def raw(text):
    return cmd(text)

if __name__ == "__main__":
    if not os.path.exists(UART):
        print(f"Error: {UART} not found")
        sys.exit(1)

    print(f"Motor UART: {UART}")
    print("Commands: TC<0-3> (mode)  C<val> (current)  T<val> (speed)")
    print("          GS (status)  SM0/1 (off/on)  CE (errors)  q (quit)")
    try:
        while True:
            inp = input("> ").strip()
            if inp == "q":
                break
            print(cmd(inp))
    except KeyboardInterrupt:
        pass
