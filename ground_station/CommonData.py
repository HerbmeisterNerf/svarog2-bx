from dataclasses import dataclass
import queue
import socket


@dataclass
class CommonData:
    '''Shared state used by all ground station classes.'''

    # EBOX socket
    client_TCP_socket: socket.socket = None
    telemetryParameters: int = 35

    # CubeSat socket
    client_TCP_socket_cs: socket.socket = None

    # UDP ports (legacy)
    camera_port_UDP: int = 15000
    telemetry_port_UDP: int = 11000
    probe_port: int = 50007

    # EBOX TCP
    server_TCP_port: int = 8005
    server_name: str = "192.168.1.10"

    # CubeSat TCP
    server_TCP_port_cs: int = 8005
    server_name_cs: str = "192.168.1.20"

    # EBOX flags
    TCPSTATUS: bool = False
    runTelemetry: bool = False
    runCamera: bool = False

    # CubeSat flags
    TCPSTATUS_cs: bool = False
    runTelemetry_cs: bool = False

    # Output flags
    firstCSV: bool = True
    outputTelemetry: bool = False
    outputTelemetryDir: str = "telemetry_output/"

    # Timers / rates
    TelemFreqVal: float = 5.0
    ImgFreqVal: float = 10
    imgbaudrate: int = 32

    # Telemetry queues (class-level, shared singletons)
    ebox_telem_queue = queue.Queue()
    cs_telem_queue = queue.Queue()
