# Svarog-BX

Software for the Svarog BEXUS balloon experiment. Runs on a Radxa Rock 3B flight computer with a ground-station laptop GUI.

## Architecture

```
Ground Station (laptop)          Flight Computer (Radxa Rock 3B)
┌─────────────────────┐          ┌──────────────────────────────────┐
│   ground_station/   │◄── TCP ──►   main_mpu/                      │
│   Tkinter GUI        │          │   ├── server/   (TCP/UDP layer)  │
│   Live telemetry    │◄── UDP ──►   └── hardware/ (Radxa drivers)  │
│   Camera viewer     │          ├── streaming/  (GStreamer RTSP)    │
└─────────────────────┘          └──────────────────────────────────┘
                                          │ UART
                                  ┌───────▼────────┐
                                  │motor_controller │
                                  │ STM32/SimpleFOC │
                                  └─────────────────┘
```

## Folders

| Folder | Purpose | Hardware |
|--------|---------|----------|
| `main_mpu/hardware/` | Radxa Rock 3B onboard software — sensor drivers (I2C, SPI, UART), peripheral shift-register control, thermal management, telemetry gathering | Radxa Rock 3B (`mraa` library required) |
| `main_mpu/server/` | TCP/UDP networking integration layer (in progress — see `legacy/rpi_main_mpu/` for the architecture to port) | Radxa Rock 3B |
| `ground_station/` | Ground control Tkinter GUI — live telemetry display, camera viewer, heater/burn-wire/motor commands | Any Python 3 laptop |
| `streaming/` | GStreamer RTSP server for up to 5 camera streams + screenshot/recording commands | Radxa Rock 3B (GStreamer + `gi` bindings) |
| `motor_controller/` | SimpleFOC ESC firmware for BLDC motor, STM32 serial command interface | STM32 B-G431B-ESC1 board |
| `secondary_mpu/` | Secondary payload MCU — not yet implemented | TBD |
| `shared/` | Canonical 314-bit telemetry packet format (`message_pack.py`) and LMT87 temperature lookup table | — |
| `legacy/rpi_main_mpu/` | Archived RPi-based flight software using shell-script sensor integration | Raspberry Pi |
| `legacy/telemetry_prototype/` | Early TCP/UDP telemetry prototypes (V1/V2) predating current architecture | — |

## Hardware Requirements

- **Flight computer**: Radxa Rock 3B, Linux, `mraa` Python bindings
- **Ground station**: Any machine with Python 3 + `tkinter`
- **Streaming**: GStreamer 1.0 with `python3-gi`, `gstreamer1.0-plugins-good`, `gstreamer1.0-rtsp-server`
- **Motor controller**: Arduino IDE + [SimpleFOC library](https://simplefoc.com/)

## Branches

| Branch | Description |
|--------|-------------|
| `R3B-wip` | Active development — Radxa Rock 3B hardware integration |
| `main` | Older baseline (pre-Radxa, RPi era) |

## Known TODOs

- `main_mpu/hardware/CommandReciever.py` — stub, not yet implemented
- `main_mpu/server/` — empty; networking layer from `legacy/rpi_main_mpu/` needs porting to use the Radxa hardware drivers
- `secondary_mpu/` — placeholder only, no implementation
- `shared/message_pack.py` — 314-bit format; `legacy/rpi_main_mpu/messagePack.py` uses 311-bit variant — these need to be reconciled before the server integration
