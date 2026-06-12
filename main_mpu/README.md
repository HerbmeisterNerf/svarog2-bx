# main_mpu

Onboard flight computer software for the Radxa Rock 3B.

## Structure

```
main_mpu/
├── hardware/        # All hardware drivers and flight logic (active development)
│   ├── tests/       # Standalone hardware test scripts
│   └── ...
└── server/          # TCP/UDP networking layer (NOT YET IMPLEMENTED)
```

## hardware/

The active Radxa-native implementation. Key files:

| File | Role |
|------|------|
| `main.py` | Entry point — starts peripheral driver, temp controllers, TCP server |
| `declarations.py` | GPIO pin bindings, peripheral map, shared thread locks |
| `peripherals.py` | `PeripheralDriver` thread — MC74HC595A shift register, controls 8 heaters/burn-wires |
| `DataSender.py` | `SendTelem` thread — async ADC + GPIO reads, formats and sends telemetry over TCP |
| `TempController.py` | `TempController` thread — FIR-filter-based thermal control loop |
| `TempControllerOld.py` | Archived previous TempController (simpler, kept for reference) |
| `RADXA_I2C_INTERFACE.py` | LPS22HB pressure sensor + MC6470 IMU via mraa I2C |
| `RADXA_SPI_INTERFACE.py` | ADC128S052 for PDU voltages/currents and thermal ADC via SPI |
| `RADXA_UART_INTERFACE.py` | 115200-baud UART for motor controller communication |
| `ImageSender.py` | Sends captured images to ground station |
| `WatchImage.py` | Monitors image-send flag, triggers `ImageSender` |
| `main_camera.py` | Entry point for camera integration |
| `start_video_record.py` | Starts GStreamer pipeline recording |
| `take_screenshot.py` | Captures JPEG from RTSP stream |
| `CommandReciever.py` | **STUB — not yet implemented** |

### Running

```bash
python main.py
```

Requires `mraa` Python bindings (Radxa hardware only).

## server/

**Not yet implemented.** This is where the TCP/UDP networking layer (command handling, telemetry dispatch, connection management) should live once ported from `legacy/rpi_main_mpu/` to use the `hardware/` drivers.
