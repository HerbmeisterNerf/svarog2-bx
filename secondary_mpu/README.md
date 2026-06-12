# secondary_mpu

**Not yet implemented.**

Placeholder for the secondary payload MCU software.

## Intended Role

The secondary MPU is expected to handle secondary payload data collection and report status back to the main MPU. The main MPU reads its status via `legacy/rpi_main_mpu/SendTelem.py` (`updateSecondaries` method, reading `Secondarystatus.txt`), indicating the communication interface is file/UART based.

## TODO

- Define hardware platform
- Define communication protocol with main MPU
- Implement data collection and status reporting
