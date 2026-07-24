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
    server_name: str = "127.0.0.1"

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

    # UDP transport (Space Packet Protocol)
    udp_tc_socket: socket.socket = None   # single socket for sending TC to either node
    ebox_tc_seq: int = 0                  # rolling 14-bit TC sequence counter (EBOX)
    cs_tc_seq:   int = 0                  # rolling 14-bit TC sequence counter (CubeSat)
    last_ebox_tc_ack: int = 0             # last_tc_seq echoed in EBOX TM
    last_cs_tc_ack:   int = 0             # last_tc_seq echoed in CubeSat TM
    last_ebox_tm_time: float = 0.0        # time.time() of last received EBOX TM packet
    last_cs_tm_time:   float = 0.0        # time.time() of last received CS TM packet

    # Camera / motor UI state
    selected_camera: int = 1   # 1-4 = EBOX RZ1-4, 5-6 = CS RZ1-2

    # Parsed FOC motor telemetry — filled by the TM reader, read by MotorPanel.
    # (class-level shared singleton, like the queues below)
    motor_state = {"angle": 0.0, "vel": 0.0, "cur": 0.0, "trq": 0.0,
                   "hall": "---", "t": 0.0}

    # Telemetry queues (class-level, shared singletons)
    ebox_telem_queue = queue.Queue()
    cs_telem_queue = queue.Queue()
