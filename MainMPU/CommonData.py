############ standard libraries ############
from dataclasses import dataclass
import socket

############ class ############
@dataclass
class CommonData:
    '''
    This class contains the shared data that is used by all the classes in the server
    '''

    commandSocket: socket.socket

    commandSocketStatus: bool = False

    commandAdd: str = ""
