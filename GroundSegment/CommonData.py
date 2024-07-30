############ standard libraries ############
from dataclasses import dataclass
import socket

############ class ############
@dataclass
class CommonData:

    client_TCP_socket: socket.socket

    telemetryParameters: int

    TCPSTATUS: bool = False
