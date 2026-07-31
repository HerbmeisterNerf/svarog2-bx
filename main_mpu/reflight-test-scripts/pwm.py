import os
import sys
import time

PWM_PIN = 15   # physical pin = EN_P2 / PWM2_M1
PERIOD_NS = 1000000  # 1 kHz (1,000,000 ns)

# ── helpers ──────────────────────────────────────────────────────────

def _list_pwmchips():
    chips = []
    for entry in os.listdir("/sys/class/pwm/"):
        if entry.startswith("pwmchip"):
            try:
                chips.append(int(entry[7:]))
            except ValueError:
                pass
    return sorted(chips)

def _export(chip, channel=0):
    ch_path = f"/sys/class/pwm/pwmchip{chip}/pwm{channel}"
    if os.path.exists(ch_path):
        return True
    try:
        with open(f"/sys/class/pwm/pwmchip{chip}/export", "w") as f:
            f.write(str(channel))
        time.sleep(0.1)
        return os.path.exists(ch_path)
    except OSError as e:
        print(f"  export pwmchip{chip} ch{channel} failed: {e}")
        return False

def _unexport(chip, channel):
    ch_path = f"/sys/class/pwm/pwmchip{chip}/pwm{channel}"
    if not os.path.exists(ch_path):
        return
    try:
        with open(f"/sys/class/pwm/pwmchip{chip}/unexport", "w") as f:
            f.write(str(channel))
    except OSError:
        pass

def _write(path, value):
    with open(path, "w") as f:
        f.write(str(value))

# ── find working chip+channel ───────────────────────────────────────

if len(sys.argv) > 2:
    chip = int(sys.argv[1])
    channel = int(sys.argv[2])
    if not _export(chip, channel):
        print(f"Failed to export pwmchip{chip} ch{channel}")
        sys.exit(1)
    found = (chip, channel)
else:
    found = None
    for chip in _list_pwmchips():
        for ch in range(4):
            if not _export(chip, ch):
                continue
            try:
                _write(f"/sys/class/pwm/pwmchip{chip}/pwm{ch}/period", str(PERIOD_NS))
                found = (chip, ch)
                break
            except OSError:
                _unexport(chip, ch)
        if found:
            break

if found is None:
    chips = _list_pwmchips()
    print(f"Could not set period {PERIOD_NS}ns on any PWM chip.")
    print(f"Available chips: {chips}")
    print("Specify chip and channel:  python3 pwm.py <chip> <channel>")
    if chips:
        print(f"  Try:  python3 pwm.py {chips[0]} 0")
    sys.exit(1)

chip, channel = found
base = f"/sys/class/pwm/pwmchip{chip}/pwm{channel}"
print(f"Using pwmchip{chip} channel {channel}  ({base})")

# ── interactive duty control ────────────────────────────────────────

def set_duty(percent):
    pct = max(0.0, min(100.0, percent))
    duty_ns = int(PERIOD_NS * pct / 100.0)
    _write(f"{base}/duty_cycle", str(duty_ns))
    if pct > 0:
        _write(f"{base}/enable", "1")
    else:
        _write(f"{base}/enable", "0")
    return duty_ns

def stop():
    _write(f"{base}/enable", "0")
    _write(f"{base}/duty_cycle", "0")

stop()

print(f"PWM active on pin {PWM_PIN} (EN_P2 / PWM2_M1) at {1e9/PERIOD_NS:.0f}Hz")
print("Enter duty cycle 0-100 (%), or q to quit")

try:
    while True:
        inp = input("duty> ").strip()
        if inp == "q":
            break
        try:
            val = float(inp)
            duty_ns = set_duty(val)
            print(f"  duty={val:.1f}%  ({duty_ns}ns)")
        except ValueError:
            print("invalid")
except KeyboardInterrupt:
    pass
finally:
    stop()
    print("PWM stopped")
