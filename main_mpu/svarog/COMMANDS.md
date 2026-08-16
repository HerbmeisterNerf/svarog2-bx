# Command Reference: Frontend → Backend

Every command is a single newline-terminated text line sent over the **command
TCP socket** (default port `8006`, on both EBOX and CUBESAT). The backend
responds with one line (or a multi-line block) followed by `\n`.

Command handler: `board/subcomponents/commands.py` (`handle_command`).
Server loop: `board/subcomponents/command_server.py` (`cmd_server`).

Peripheral names are defined in `board/declarations.py` (`PERIPH_BINDINGS`):

| Board   | Peripherals                                  |
|---------|----------------------------------------------|
| EBOX    | `BW_1`, `HEAT_1`, `HEAT_2`, `HEAT_3`, `HEAT_4` |
| CUBESAT | `BW_1`, `BW_2`, `BW_3`, `BW_4`, `HEAT_1`     |

---

## Frontend → Backend commands

| Command sent by GUI                 | GUI widget                          | Backend action                                             | Reply            |
|-------------------------------------|-------------------------------------|------------------------------------------------------------|------------------|
| `STATUS`                            | Connection bar "STATUS" button      | Full status snapshot (power-good, faults, enables, sensors) | text block       |
| `EN <name> 1`                       | Burnwire/heater "ON" button         | Drive enable GPIO high                                       | `OK`             |
| `EN <name> 0`                       | Burnwire/heater "OFF" button        | Drive enable GPIO low                                        | `OK`             |
| `BW <name> 3000`                    | Burnwire quick-fire button          | Pulse enable GPIO high for 3000 ms                           | `OK`             |
| `BW <name> <ms>`                | Burnwire advanced "Pulse" (custom ms) | Pulse enable GPIO high for `<ms>` ms                         | `OK`             |
| `MOTOR TC<mode>`                | Motor "Mode TC0-3" + "Set"          | Set motor control mode (0–3)                                 | `OK` / motor reply |
| `MOTOR T<speed>`              | Motor "Speed" + "Set"               | Set motor speed target                                       | `OK` / motor reply |
| `MOTOR C<current>`            | Motor "Current" + "Set"             | Set motor current target                                     | `OK` / motor reply |
| `MOTOR PING`                     | Motor "PING" button                 | Ping the motor controller UART                               | reply / `NO RESPONSE` |
| `MOTOR RAW <cmd>`              | Motor "RAW" dialog                  | Send raw UART bytes to motor controller                      | `OK` / reply     |
| `<any text>`                     | Command entry box (`self.link.send`) | Dispatched to `handle_command`                               | per command      |
| `SET_TRANS_PERIOD <seconds>`    | Top-bar "Retransmit period" Set     | Set telemetry push interval (both boards if connected)       | `OK interval=N`  |

> The heater-duty indicator LEDs in the GUI are passive: they colour from the
> telemetry stream, not from these commands.

## Full backend command set

These respond to anything the GUI (or a manual telnet/script client) sends.

| Command                                      | Backend action                                                     | Reply             |
|----------------------------------------------|--------------------------------------------------------------------|-------------------|
| `PING`                                       | Liveness check                                                     | `PONG`            |
| `STATUS`                                     | Full snapshot from the live sensor reader                          | text block        |
| `STATUS PG`                                  | Only power-good readings                                           | `KEY=val` lines   |
| `STATUS FLT`                                 | Only fault readings                                                | `KEY=val` lines   |
| `STATUS EN`                                  | Only peripheral enable states                                      | `KEY=val` lines   |
| `EN <name> <0|1>`                           | Set enable GPIO for `<name>`                                       | `OK` / error      |
| `BW <name> [ms]`                            | Enable GPIO for `<ms>` ms (default 1500 ms), then off              | `OK`              |
| `MOTOR TC<x>`                               | Set motor mode                                                     | `OK` / error      |
| `MOTOR T<x>`                                | Set motor speed                                                    | `OK` / error      |
| `MOTOR C<x>`                                | Set motor current                                                  | `OK` / error      |
| `MOTOR RAW <...>`                           | Send raw UART bytes to motor controller                            | `OK` / reply      |
| `TEMP`                                        | Latest thermal sensor snapshot (EBOX)                               | `KEY=value` lines |
| `PDU`                                         | Latest PDU sensor snapshot (EBOX)                                  | `KEY=value` lines |
| `ENCODER`                                     | Read AS5047 angle + diagnostics                                    | `KEY=value` lines |
| `I2C`                                         | Scan I2C bus                                                       | `OK`              |
| `HEATER <name> <duty>`                     | Drive heater GPIO on (`>0`), off (`0`)                             | `OK`              |
| `SET_TRANS_PERIOD <seconds>`               | Change telemetry push interval                                     | `OK interval=N`   |
| `HEATER_SETPOINT <name> <temp_C>`          | Set heater controller setpoint temperature                         | `OK ...C`         |
| `HEATER_CONTROL <0|1>`                     | Stop the heater controller thread (`0`) or start/ensure it runs (`1`) | `OK heaters ...`   |

Every `<name>`, `<duty>`, `<seconds>`, etc. is validated by the backend handler
before any hardware access. Unknown commands or bad values reply with `ERR: ...`.