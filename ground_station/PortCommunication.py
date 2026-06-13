import socket
from CommonData import CommonData


class PortCommunication:
    '''Opens and closes UDP and TCP sockets between ground station and flight computers.'''

    def __init__(self):
        pass

    # UDP (legacy camera/ping)

    def open_UDP(client_UDP_port: int) -> socket.socket:
        UDP_info = ("", client_UDP_port)
        client_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_UDP_socket.bind(UDP_info)
        return client_UDP_socket

    def close_UDP(client_UDP_socket: socket.socket) -> None:
        client_UDP_socket.close()

    # EBOX TCP

    def open_TCP() -> None:
        CommonData.client_TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        CommonData.client_TCP_socket.connect(
            (CommonData.server_name, CommonData.server_TCP_port)
        )
        CommonData.TCPSTATUS = True

    def close_TCP() -> None:
        try:
            CommonData.client_TCP_socket.close()
        except Exception:
            pass
        CommonData.client_TCP_socket = None
        CommonData.TCPSTATUS = False

    # CubeSat TCP

    def open_TCP_cubesat() -> None:
        CommonData.client_TCP_socket_cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        CommonData.client_TCP_socket_cs.connect(
            (CommonData.server_name_cs, CommonData.server_TCP_port_cs)
        )
        CommonData.TCPSTATUS_cs = True

    def close_TCP_cubesat() -> None:
        try:
            CommonData.client_TCP_socket_cs.close()
        except Exception:
            pass
        CommonData.client_TCP_socket_cs = None
        CommonData.TCPSTATUS_cs = False


if __name__ == '__main__':
    print('Cannot run this file directly')
