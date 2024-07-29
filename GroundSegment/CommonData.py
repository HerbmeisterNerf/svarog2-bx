############ standard libraries ############
from dataclasses import dataclass
import socket

############ class ############
@dataclass
class CommonData:

    client_TCP_socket: socket.socket

    TCPSTATUS: bool = False

    # def __init__(self) -> None:
    #     pass

    # def set_client_TCP_socket(self, inp):
    #     self.client_TCP_socket = inp

    # def obtain_client_TCP_socket(self):
    #     return self.client_TCP_socket
