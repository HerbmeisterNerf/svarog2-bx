# ground_station

Tkinter GUI for the ground control station. Connects to the flight computer over TCP/UDP.

## Running

```bash
python main.py
```

Requires Python 3 with `tkinter` (standard library).

## Network Topology

```
Ground Station                     Flight Computer
  TCP :12000  ──── commands ────►  TCP :12000
  UDP :11000  ◄─── telemetry ────  UDP :11000
  UDP :15000  ◄─── images ─────── UDP :15000
  UDP :50007  ◄──► keep-alive ─── UDP :50007
```

Set the server IP before deployment in `CommonData.py` (`server_name` field).

## Key Files

| File | Role |
|------|------|
| `TCPClientApp.py` | Main Tkinter window — heater/burn-wire/motor controls, telemetry table |
| `LiveUpdatesTelemetry.py` | Receives UDP telemetry, parses packets, updates GUI table |
| `LiveUpdatesCamera.py` | Requests images over TCP, displays in GUI |
| `MessagePack.py` | Local copy of 314-bit telemetry packet parser (canonical version in `shared/`) |
| `CommonData.py` | Shared state — server IP, ports, flags |
| `PingServer.py` | Pings flight computer to check connectivity |

## Dependencies

- Python 3 standard library only (`tkinter`, `socket`, `threading`)
