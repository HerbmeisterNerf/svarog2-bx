############ standard libraries ############
from dataclasses import dataclass
import socket

############ class ############
@dataclass
class CommonData:
    '''
    This class contains the shared data that is used by all the classes in the project
    '''

    # sockets

    client_TCP_socket: socket.socket

    telemetryParameters: int

    # UDP ports

    camera_port_UDP: int = 15000

    telemetry_port_UDP: int = 11000

    probe_port: int = 50007

    # TCP ports and server name

    server_TCP_port: int = 12000

    server_name: str = "192.168.1.81"

    # Flags

    TCPSTATUS: bool = False

    runTelemetry: bool = False

    runCamera: bool = False

    # Output flags

    outputTelemetry: bool = False

    # Directories

    outputTelemetryDir: str = "telemetry_output/"

    # timers

    TelemFreqVal: float = 0.1

    ImgFreqVal: float = 0.1

    # data rates

    imgbaudrate: int = 32
