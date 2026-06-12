# main_mpu/server — NOT YET IMPLEMENTED

This directory is the integration target for the TCP/UDP networking layer.

The architecture to port lives in `legacy/rpi_main_mpu/`. It provides:
- TCP command socket (port 12000) — receives commands from ground station
- UDP telemetry socket (port 11000) — sends telemetry packets
- UDP image socket (port 15000) — sends image data
- UDP keep-alive socket (port 50007)

The porting task is to replace the shell-script sensor calls in `legacy/rpi_main_mpu/SendTelem.py`
with calls to the `hardware/` Radxa drivers (`DataSender.py`, `RADXA_*_INTERFACE.py`).
