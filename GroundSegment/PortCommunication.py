############ standard libraries ############
import socket

############ custom libraries ############


############ class ############
class PortCommunication:

############ Initializer ############

    def __init__(self):
        pass

############ Methods ############

    def open_UDP(client_UDP_port: int) -> socket.socket:
        UDP_info = ("", client_UDP_port)
        client_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_UDP_socket.bind(UDP_info)

        return client_UDP_socket

    def close_UDP(client_UDP_socket: socket.socket) -> None:
        client_UDP_socket.close()

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
