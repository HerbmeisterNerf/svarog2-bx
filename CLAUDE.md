# Svarog BEXUS 36 — Project Context for Claude

## Repository
Gen 2 of the Svarog BEXUS balloon experiment (Imperial College team). Upgraded from RPi (Gen 1: `BigKoala33/SvarogBX-Code`) to Radxa Rock 3B.
Active development branch: `R3B-wip`. `main` is the older RPi-era baseline.

## Reference Documents
- SED V4 (authoritative electronics reference): `Nextcloud/Documents/00_Imperial/Svarog/Svarog Shared/General/02_BEXUS_36_2024-2025/24_SEDV4/BX36_SVAROG2_SED_V4_0_01Sept25_HIGHLIGHTED.pdf`

## Electronics Architecture

Two SBCs both located **on the balloon** — not ground vs balloon. They communicate via fiber optic through a spring slip ring (handles CubeSat rotation).

**Full comms chain:** Ground Station → Gondola Ethernet → EBOX R3B (eth0) → EBOX R3B (eth1) → Fiber Modem → Fiber + slip ring → Fiber Modem → CubeSat R3B (eth0)

**Network topology:** The Ethernet cable from the antenna plugs into the EBOX R3B's eth0. The CubeSat R3B is chained off the EBOX R3B's eth1 via the fiber modems. The EBOX R3B runs a **kernel-level Linux bridge** (br0 = eth0 + eth1) so ground can address both R3Bs directly on the same subnet (192.168.1.x) — and the bridge survives a Python software crash on EBOX. See `main_mpu/network_setup/` for the boot script and systemd unit.

**IP addresses:** Ground=192.168.1.1, EBOX R3B=192.168.1.10, CubeSat R3B=192.168.1.20

### EBOX (gondola-mounted electronics box)
- **Main MPU**: Radxa Rock 3B+ (R3B) — connected to ground via Gondola Ethernet, to CubeSat via fiber optic modem
- **4× Secondary MPUs** (Radxa Rock Zero) + **4× Cameras** (Arducam OV9281, monochrome global shutter) via USB-as-network
- **Motor Controller Spinning** → Spinning Motor
- **PDU** — 28V in, distributes 5V/9V/12V
- **Sensor Board** (IMU MC6470, Pressure sensor LPS22HBTR)
- **5× Peripheral Driver Boards** → 4× Heaters + 1× Burn Resistor Module
- **4× Temp Sensors**
- **Optical Modem** → Fiber → CubeSat

### CubeSat (deployable payload)
- **Main MPU**: Radxa Rock 3B+ (R3B) — connected to EBOX via fiber optic modem (ETH)
- **2× Secondary MPUs** + **2× Cameras** via USB
- **Motor Controller Flywheel** → Flywheel Motor (12V)
- **Motor Controller Deployment** → Deployment Motor (12V)
- **PDU** — 28V in, distributes 5V/9V/12V
- **Sensor Board**
- **7× Peripheral Driver Boards** → 5× BW Modules + 2× Heaters (internal camera)
- **6× Temp Sensors**
- **Optical Modem** → Fiber → EBOX

### PCB Stack (per node)
Each node (EBOX and CubeSat) has two boards connected via 40-pin GPIO cable:
- **Top Board (200×200mm)**: Main MPU (R3B), Secondary MPUs, PDU, peripheral drivers, temp sensors
- **Bottom Board (200×200mm)**: Motor drivers (Infineon BLDC_SHIELD_TLE9879), current limiter, sensor board, fiber-optic modem
- Motor control: Arduino Nano on bottom board, UART to R3B

### Key Terms
- **R3B** = Radxa Rock 3B (main flight computer, gen 2 upgrade from RPi 3)
- **BW Modules** = Burn Wire/Resistor modules (sail deployment release)
- **SED** = Student Experiment Document (BEXUS programme requirement)
