from declarations import *
from DataSender import SendTelem
from TempController import TempController
from peripherals import peripherals
from CommandReciever import CommandReceiver
from RADXA_UART_INTERFACE import UARTInterface

import socket

controllers = []  # e.g. [TempController("HEAT_1")]


def make_uarts():
    """Instantiate one UARTInterface per motor Arduino defined in node_config."""
    uart_hw_ids = [1, 2]  # UART1 = flywheel/spinning, UART2 = deployment (CubeSat only)
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
    uart_flywheel = uarts[0] if len(uarts) > 0 else None
    uart_deployment = uarts[1] if len(uarts) > 1 else None

    try:
        for controller in controllers:
            controller.start()
        peripherals.start()
        print(f"[{NODE_ID}] Peripherals started")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as welcome_socket:
            welcome_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            welcome_socket.settimeout(DATA_WAIT_TIMEOUT)
            welcome_socket.bind(('0.0.0.0', 8005))
            welcome_socket.listen()

            while True:
                try:
                    print(f"[{NODE_ID}] Listening on :8005")
                    client, caddr = welcome_socket.accept()
                    print(f"[{NODE_ID}] Ground station connected from {caddr}")
                    with client:
                        telem = SendTelem(client, temp_controllers=controllers, uart_flywheel=uart_flywheel)
                        cmd_rx = CommandReceiver(
                            client,
                            uart_flywheel=uart_flywheel,
                            uart_deployment=uart_deployment,
                        )
                        telem.start()
                        cmd_rx.start()
                        telem.join()  # block until client disconnects or telem thread dies
                    print(f"[{NODE_ID}] Ground station disconnected, waiting for reconnect")

                except socket.timeout:
                    print(f"[{NODE_ID}] Waiting for connection...")
                except socket.error as e:
                    print(f"[{NODE_ID}] TCP error: {e}")
                except KeyboardInterrupt:
                    break

    except KeyboardInterrupt:
        print(f"[{NODE_ID}] Interrupt received, shutting down")
    finally:
        shutdown(uarts)
