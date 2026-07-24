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
from USB_SERIAL_INTERFACE import USBSerialInterface
from motor_interface import MotorController
from CameraService import CameraService

_shared = os.path.join(os.path.dirname(__file__), '..', '..', 'shared')
sys.path.insert(0, _shared)
from space_packet import TC_UDP_PORT

controllers = []  # populate with e.g. [TempController("HEAT_1")] for auto-heating

# Shared mutable state for TC acknowledgement
tc_ack = {"seq": 0}


def make_uarts():
    """Open one USB CDC-ACM link per ESC listed in node_config.MOTOR_USB_DEVICES.

    The ESC's hardwired UART contends with the on-board ST-Link, so the motor
    is driven over its USB port (/dev/ttyACM*) instead. A device that fails to
    open (ESC not plugged in) yields None so the rest of the flight code runs.
    """
    uarts = []
    for dev in MOTOR_USB_DEVICES:
        try:
            uarts.append(USBSerialInterface(device=dev))
            print(f"[{NODE_ID}] ESC link open on {dev}")
        except OSError as e:
            print(f"[{NODE_ID}] WARNING: could not open ESC on {dev}: {e}")
            uarts.append(None)
    return uarts


def shutdown(uarts):
    for controller in controllers:
        controller.stop_t()
    peripherals.stop_t()
    peripherals.reset()
    peripherals.send_output()
    for u in uarts:
        if u is not None:
            u.close()
    print(f"[{NODE_ID}] Shutdown complete")


if __name__ == "__main__":
    uarts = make_uarts()
    uart_flywheel   = uarts[0] if len(uarts) > 0 else None
    uart_deployment = uarts[1] if len(uarts) > 1 else None

    # Wrap the motor UARTs in the SimpleFOC Commander driver (B-G431B-ESC1).
    motor_flywheel   = MotorController(uart_flywheel, name="flywheel") if uart_flywheel else None
    motor_deployment = MotorController(uart_deployment, name="deployment") if uart_deployment else None

    # Local camera snapshot service (grabs /dev/video0 on CMD_CAM_SNAPSHOT).
    camera_service = CameraService(device="/dev/video0")

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
            motor_flywheel=motor_flywheel,
            tc_ack=tc_ack,
        )
        cmd_rx = CommandReceiver(
            rx_sock,
            motor_flywheel=motor_flywheel,
            motor_deployment=motor_deployment,
            camera_service=camera_service,
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
