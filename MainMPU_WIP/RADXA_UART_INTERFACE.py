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

