from declarations import *
from DataSender import *
from TempController import TempController
from peripherals import peripherals

import socket

# temp controllers run regardless
controllers = [] #[TempController("HEAT_1")]

def shutdown():
    """Include all code that must run in the event of a fatal exception or keyboardInterrupt here."""
    for controller in controllers:
        # stop all control loops
        controller.stop_t()
    print("Closed all controller threads")
    peripherals.stop_t() # stop peripheral thread
    peripherals.reset()
    peripherals.send_output() # manual turn off of all peripherals
    print("Reset peripherals and killed thread")


if __name__ == "__main__":
    try:
        server_port = 8005
        for controller in controllers:
            print("running controller")
            controller.start()
        # todo: currently gathers data only if connect, but it should do so either way
        peripherals.start()
        print("Started peripherals")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as welcome_socket:
            welcome_socket.settimeout(DATA_WAIT_TIMEOUT)
            welcome_socket.bind(('0.0.0.0', server_port))
            welcome_socket.listen()

            while True:
                try:
                    print("Socket listening")
                    client, caddr = welcome_socket.accept()
                    with client:  # Client will be automatically closed
                        print("Client found!")
                        telem = SendTelem(client,temp_controllers=controllers)
                        telem.run()
                        break
                        
                except socket.timeout:
                    print("ERROR: Socket operation timed out.")
                except socket.error as e:
                    print(f"ERROR: TCP connection failed. Error details: {e}")
                except KeyboardInterrupt:
                    print("Closing sockets gracefully")
                    welcome_socket.close()
                    break
        while True:
            time.sleep(10)
            print("Main thread idling")
    except KeyboardInterrupt:
        print("Attempting graceful shutdown")
    finally:
        shutdown()
