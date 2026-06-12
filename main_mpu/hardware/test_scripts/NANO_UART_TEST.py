import mraa
import time

class UARTInterface:
    def __init__(self, uart_id=1, baudrate=115200, databits=8, stopbits=1, parity=mraa.UART_PARITY_NONE):
        self.uart = mraa.Uart(uart_id)
        self.uart.setBaudRate(baudrate)
        self.uart.setMode(databits, parity, stopbits)
        self.uart.setFlowcontrol(False, False)

    def send(self, message):
        """Send a string message over UART."""
        if isinstance(message, str):
            message = message.encode('ascii')
        self.uart.write(message)
        self.uart.flush()

    def receive(self, max_length=128, timeout=1.0):
        """Receive a string from UART. Waits up to timeout seconds."""
        start = time.time()
        received = b""
        while time.time() - start < timeout:
            if self.uart.dataAvailable():
                received += self.uart.readStr(max_length).encode('ascii')
            if received:
                break
            time.sleep(0.01)
        return received.decode('ascii') if received else None

    def close(self):
        self.uart = None

if __name__ == '__main__':
    uart = UARTInterface(uart_id=2, baudrate=115200, databits=8, stopbits=1)
    # NOTE: follow https://wiki.radxa.com/Rock3/dev/uart to use UART2 as a normal serial port and not a debug port

    ############ try:
    ############     while True:
    ############         uart.send("Hello Arduino!\n")
    ############         response = uart.receive()
    ############         if response:
    ############             print("Received:", response)
    ############         time.sleep(1)
    ############ except KeyboardInterrupt:
    ############     print("Exiting...")
    ############ finally:
    ############     uart.close()

    # Motor controller test
    # Commands:
    # SS_[BOARD_NUM]_[SPEED] - set speed
    # GS_[BOARD_NUM]         - get speed
    # SM_[BOARD_NUM]_[MODE]  - set mode (0=off, 1=on)
    # CE                     - check errors
    # SP_[BOARD_NUM]_[PARAM]=[VAL] - set parameter (see https://www.infineon.com/assets/row/public/documents/10/44/infineon-bldc-shield-usermanual-en.pdf#_OPENTOPIC_TOC_PROCESSING_d131e2703)
    # HI                     - debug
    try:
        uart.send("HI\n")
        response = uart.receive()
        if response:
            print("Received:", response)
            if "Arduino says hello :)" in response:
                print("HI TEST SUCCESS")
        
        # uart.send("SM_0_0\n")
        # time.sleep(10)
        # uart.send("SM_0_1\n")
    finally:
        uart.close()