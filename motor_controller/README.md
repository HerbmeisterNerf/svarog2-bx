# motor_controller

SimpleFOC-based BLDC motor controller firmware for the STM32 B-G431B-ESC1 board.

## Files

| File | Role |
|------|------|
| `motor_controller.ino` | Main Arduino sketch — SimpleFOC torque control with Hall sensor feedback |
| `build_opt.h` | Build flag: `-DHAL_OPAMP_MODULE_ENABLED` (required for B-G431B-ESC1) |
| `main.cpp` | WIP C++ rewrite of the serial command parser (same command protocol) |

## Hardware

- **Board**: STM32 B-G431B-ESC1
- **Motor**: 4-pole BLDC, 3.9 Ω phase resistance, KV 273
- **Sensor**: Hall sensors on A_HALL1/2/3
- **Power supply**: 24 V

## Serial Command Protocol

Sent from the Radxa via UART at 115200 baud:

| Command | Format | Description |
|---------|--------|-------------|
| `HI` | `HI` | Handshake — returns "Arduino says hello :)" |
| `SS` | `SS_<board>_<speed>` | Set speed |
| `SM` | `SM_<board>_<mode>` | Set mode |
| `SP` | `SP_<board>_<param>=<val>` | Set parameter |
| `GS` | `GS_<board>` | Get status |
| `CE` | `CE_<board>` | Command execute |

## Dependencies

- [SimpleFOC library](https://simplefoc.com/) v2.x
- Arduino IDE or PlatformIO

## Setup

1. Open `motor_controller.ino` in Arduino IDE
2. Select board: **STM32 B-G431B-ESC1** (via STM32duino board manager)
3. Flash — motor will await serial commands
