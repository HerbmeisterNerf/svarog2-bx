from declarations import *
from adc import THERMAL_ADC
import sys, select

THERMAL_LABELS = [
    "THERMAL_SENS_OUT_1", "THERMAL_SENS_OUT_2",
    "THERMAL_SENS_OUT_3", "THERMAL_SENS_OUT_4",
    "THERMAL_SENS_OUT_5", "THERMAL_SENS_OUT_6",
    "THERMAL_SENS_INT_1", "THERMAL_SENS_INT_2",
]

EN_PINS = [gpio_EN_P1, gpio_EN_P2, gpio_EN_P3, gpio_EN_P4, gpio_EN_P5]

thermal_adc = THERMAL_ADC()

# Heater state
setpoints = {h: 30.0 for h in HEATER_SENSOR_PAIRS}  # default 30°C
duty_cycle = {h: 0.0 for h in HEATER_SENSOR_PAIRS}

print("Heater control loop running (1 Hz, max 50% duty)")
print("Enter setpoint as: <name> <temp_C>, or 'q' to quit")
print("Heaters:", ", ".join(HEATER_SENSOR_PAIRS.keys()))
print()

try:
    while True:
        t0 = time.time()

        # Poll thermal sensors
        thermal = thermal_adc.poll()

        # Control each heater
        cycle_pos = t0 % 1.0  # 0.0 - 1.0
        for htr, sensor_ch in HEATER_SENSOR_PAIRS.items():
            sensor_idx = sensor_ch - 1  # 1-indexed → 0-indexed
            skey = THERMAL_LABELS[sensor_idx] if sensor_idx < len(THERMAL_LABELS) else None
            temp = thermal.get(skey, 0.0)

            # GPIO index: PERIPH_BINDINGS is 1-indexed
            gpio_idx = PERIPH_BINDINGS[htr] - 1
            gpio = EN_PINS[gpio_idx] if 0 <= gpio_idx < len(EN_PINS) else None

            sp = setpoints[htr]
            should_heat = temp < (sp - 0.5)  # 0.5°C hysteresis

            if should_heat and cycle_pos < 0.5:
                if gpio: gpio.write(1)
                duty_cycle[htr] = 50.0
            else:
                if gpio: gpio.write(0)
                duty_cycle[htr] = 0.0

        # Print status
        for htr in HEATER_SENSOR_PAIRS:
            sensor_idx = HEATER_SENSOR_PAIRS[htr] - 1
            skey = THERMAL_LABELS[sensor_idx]
            temp = thermal.get(skey, 0.0)
            print(f"{htr}  temp={temp:.1f}°C  duty={duty_cycle[htr]:.0f}%  sp={setpoints[htr]:.0f}°C  {'HEATING' if duty_cycle[htr] > 0 else 'OFF'}  ", end="")
        print()

        # Check for user input (non-blocking)
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip()
            if line == "q":
                break
            parts = line.split()
            if len(parts) >= 2 and parts[0] in HEATER_SENSOR_PAIRS:
                try:
                    setpoints[parts[0]] = float(parts[1])
                    print(f"  {parts[0]} setpoint → {parts[1]}°C")
                except ValueError:
                    print("  invalid temperature")
            else:
                print("  usage: <name> <temp_C>")

        # Sleep to maintain 1 Hz cycle
        elapsed = time.time() - t0
        time.sleep(max(0, 1.0 - elapsed))

except KeyboardInterrupt:
    pass
finally:
    for htr in HEATER_SENSOR_PAIRS:
        gpio_idx = PERIPH_BINDINGS[htr] - 1
        gpio = EN_PINS[gpio_idx] if 0 <= gpio_idx < len(EN_PINS) else None
        if gpio: gpio.write(0)
    print("\nAll heaters off")
