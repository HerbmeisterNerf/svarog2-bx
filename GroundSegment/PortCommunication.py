############ standard libraries ############
import socket

############ custom libraries ############
from CommonData import CommonData

############ class ############
class PortCommunication:
    '''
    This class is responsible for opening and closing the UDP and TCP sockets between the server and the client
    '''

############ Initializer ############

    def __init__(self):
        pass

############ Methods ############

    ###### UDP sockets ######

    def open_UDP(client_UDP_port: int) -> socket.socket:
        UDP_info = ("", client_UDP_port)
        client_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_UDP_socket.bind(UDP_info)

        return client_UDP_socket

    def close_UDP(client_UDP_socket: socket.socket) -> None:
        client_UDP_socket.close()

    ###### TCP sockets ######

    def open_TCP() -> None:
        CommonData.client_TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        CommonData.client_TCP_socket.connect((CommonData.server_name, CommonData.server_TCP_port))
        CommonData.TCPSTATUS = True
    
    def close_TCP() -> None:
        CommonData.client_TCP_socket.close()
        CommonData.TCPSTATUS = False

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
