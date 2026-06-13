import socket
from CommonData import CommonData


class PortCommunication:
    """Manages UDP sockets and node connection state for the ground station.

    Transport is now full UDP (Space Packet Protocol).
    'Connecting' to a node means setting its target IP for TC datagrams —
    there is no TCP handshake.  TM is received passively by UDPTelemReader.
    """

    def __init__(self):
        pass

    # -------------------------------------------------------------- UDP TC socket

    def setup_udp_tc() -> None:
        """Create the shared UDP socket used to send TC to either node."""
        if CommonData.udp_tc_socket is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        CommonData.udp_tc_socket = sock

    def teardown_udp_tc() -> None:
        if CommonData.udp_tc_socket:
            try:
                CommonData.udp_tc_socket.close()
            except Exception:
                pass
            CommonData.udp_tc_socket = None

    # -------------------------------------------------------------- EBOX

    def connect_ebox(ip: str) -> None:
        """Set EBOX target IP and enable TC sending."""
        CommonData.server_name = ip
        CommonData.TCPSTATUS = True
        PortCommunication.setup_udp_tc()

    def disconnect_ebox() -> None:
        CommonData.TCPSTATUS = False

    # Kept for any callers that use the old names
    def open_TCP() -> None:
        PortCommunication.connect_ebox(CommonData.server_name)

    def close_TCP() -> None:
        PortCommunication.disconnect_ebox()

    # -------------------------------------------------------------- CubeSat

    def connect_cubesat(ip: str) -> None:
        """Set CubeSat target IP and enable TC sending."""
        CommonData.server_name_cs = ip
        CommonData.TCPSTATUS_cs = True
        PortCommunication.setup_udp_tc()

    def disconnect_cubesat() -> None:
        CommonData.TCPSTATUS_cs = False

    def open_TCP_cubesat() -> None:
        PortCommunication.connect_cubesat(CommonData.server_name_cs)

    def close_TCP_cubesat() -> None:
        PortCommunication.disconnect_cubesat()

    # -------------------------------------------------------------- legacy UDP helpers

    def open_UDP(client_UDP_port: int) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", client_UDP_port))
        return sock

    def close_UDP(client_UDP_socket: socket.socket) -> None:
        client_UDP_socket.close()


if __name__ == '__main__':
    print('Cannot run this file directly')
