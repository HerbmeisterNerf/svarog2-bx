"""Flight computer entry point.

Transport architecture (CCSDS-inspired, full UDP):
  TC receive:  bind UDP 0.0.0.0:8005  — ground station sends telecommands here
  TM transmit: broadcast UDP to 255.255.255.255:8006 every 5 s

No TCP connection is needed.  After a radio link drop the ground station
receives the next TM broadcast immediately when connectivity restores.
tc_ack is a dict shared between SendTelem (reads) and CommandReceiver (writes)
to carry `last_accepted_tc_seq` in the TM secondary header — poor-man's CLCW.
"""

import os
import sys
import socket

from declarations import *
from DataSender import SendTelem
from TempController import TempController
from peripherals import peripherals
from CommandReciever import CommandReceiver
from RADXA_UART_INTERFACE import UARTInterface

_shared = os.path.join(os.path.dirname(__file__), '..', '..', 'shared')
sys.path.insert(0, _shared)
from space_packet import TC_UDP_PORT

controllers = []  # populate with e.g. [TempController("HEAT_1")] for auto-heating

# Shared mutable state for TC acknowledgement
tc_ack = {"seq": 0}


def make_uarts():
    """Instantiate one UARTInterface per motor Arduino defined in node_config."""
    uart_hw_ids = [1, 2]   # UART1 = flywheel/spinning, UART2 = deployment (CubeSat only)
    return [UARTInterface(uart_id=uart_hw_ids[i]) for i in range(len(UART_MOTOR_IDS))]


def shutdown(uarts):
    for controller in controllers:
        controller.stop_t()
    peripherals.stop_t()
    peripherals.reset()
    peripherals.send_output()
    for u in uarts:
        u.close()
    print(f"[{NODE_ID}] Shutdown complete")


if __name__ == "__main__":
    uarts = make_uarts()
    uart_flywheel   = uarts[0] if len(uarts) > 0 else None
    uart_deployment = uarts[1] if len(uarts) > 1 else None

    # UDP receive socket: ground → flight (telecommands)
    rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx_sock.bind(("0.0.0.0", TC_UDP_PORT))

    # UDP broadcast socket: flight → ground (telemetry)
    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        for controller in controllers:
            controller.start()
        peripherals.start()
        print(f"[{NODE_ID}] Ready — TC on UDP:{TC_UDP_PORT}, TM broadcast")

        telem = SendTelem(
            tx_sock,
            temp_controllers=controllers,
            uart_flywheel=uart_flywheel,
            tc_ack=tc_ack,
        )
        cmd_rx = CommandReceiver(
            rx_sock,
            uart_flywheel=uart_flywheel,
            uart_deployment=uart_deployment,
            tc_ack=tc_ack,
        )
        telem.start()
        cmd_rx.start()
        telem.join()   # block main thread until telem thread exits (shouldn't happen)

    except KeyboardInterrupt:
        print(f"[{NODE_ID}] Interrupt received, shutting down")
    finally:
        rx_sock.close()
        tx_sock.close()
        shutdown(uarts)
