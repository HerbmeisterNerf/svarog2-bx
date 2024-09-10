############ standard libraries ############
from dataclasses import dataclass
import socket
import queue

############ class ############
@dataclass
class CommonData:
    '''
    This class contains the shared data that is used by all the classes in the server
    '''

    # sockets

    commandSocket: socket.socket

    telemetrySocket: socket.socket

    imageSocket: socket.socket

    awkSocket: socket.socket

    # status

    commandSocketStatus: bool = False

    # addresses

    commandAdd: str = ""

    # ports

    imageSocketPort: int = 15000

    telemetrySocketPort: int = 11000

    awkSocketPort: int = 50007

    # values

    imgbuffer: int = 4096
