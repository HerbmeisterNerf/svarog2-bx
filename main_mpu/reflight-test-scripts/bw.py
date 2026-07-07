from declarations import *

EN_GPIO = {
    "1": gpio_EN_P1,
    "2": gpio_EN_P2,
    "3": gpio_EN_P3,
    "4": gpio_EN_P4,
    "5": gpio_EN_P5,
}

for gpio in EN_GPIO.values():
    gpio.write(0)

print("Enter peripheral number (1-5) to activate for 3s, or q to quit")
try:
    while True:
        inp = input("> ").strip()
        if inp == "q":
            break
        if inp in EN_GPIO:
            print(f"Activating P{inp} for 3s...")
            EN_GPIO[inp].write(1)
            time.sleep(3)
            EN_GPIO[inp].write(0)
            print(f"P{inp} deactivated")
        else:
            print("Invalid. Enter 1-5 or q")
except KeyboardInterrupt:
    pass
finally:
    for gpio in EN_GPIO.values():
        gpio.write(0)
