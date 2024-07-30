############ standard libraries ############
from dataclasses import dataclass
import socket

############ class ############
@dataclass
class CommonData:

    client_TCP_socket: socket.socket

    telemetryParameters: int

    camera_port_UDP: int = 15000

    telemetry_port_UDP: int = 11000

    comms_port_TCP: int = 12000

    TCPSTATUS: bool = False

    runTelemetry: bool = False

    runCamera: bool = False
