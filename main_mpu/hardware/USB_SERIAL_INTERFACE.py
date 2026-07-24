"""USB CDC-ACM serial link to the B-G431B-ESC1 (SimpleFOC Commander firmware).

Drop-in replacement for ``RADXA_UART_INTERFACE.UARTInterface`` — exposes the
same ``send`` / ``receive`` / ``close`` contract so ``MotorController`` doesn't
care which transport it wraps.

Why USB and not the 40-pin UART: the ESC's hardwired UART (USART2 on J3) is
shared with the on-board ST-Link VCP, so the Radxa's TX contends with the
ST-Link and the motor never receives clean commands. Plugging the ESC's USB
into a Radxa port instead exposes it as ``/dev/ttyACM0`` — a reliable local
link (only the ground<->balloon RF hop is lossy, never this one).

Pure stdlib (os + termios + fcntl) — no pyserial needed on the flight image.
The ST-Link VCP only forwards the ESC's serial stream once DTR **and** RTS are
asserted, so we raise both right after opening (mirrors the PC driver's
DtrEnable/RtsEnable, proven working in acmread.py / uart_bridge.py).
"""

import os
import time
import select

try:
    import fcntl
    import termios
    import struct
    _HAVE_TERMIOS = True
except ImportError:            # non-POSIX (e.g. dev on Windows) — import-safe
    _HAVE_TERMIOS = False

_TIOCM_DTR = 0x002
_TIOCM_RTS = 0x004


class USBSerialInterface:
    """Blocking-free CDC-ACM wrapper for the ESC, matching UARTInterface's API."""

    def __init__(self, device="/dev/ttyACM0", baudrate=115200):
        self.device = device
        self.fd = None
        # Put the tty in raw mode at the right baud before opening the fd.
        os.system("stty -F %s %d cs8 -cstopb -parenb -crtscts raw -echo"
                  % (device, baudrate))
        self.fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        if _HAVE_TERMIOS:
            # Assert DTR + RTS so the ST-Link VCP forwards the ESC's stream.
            try:
                fcntl.ioctl(self.fd, termios.TIOCMBIS,
                            struct.pack('I', _TIOCM_DTR | _TIOCM_RTS))
            except OSError:
                pass
            # Drop any stale bytes buffered before we asserted the lines.
            try:
                termios.tcflush(self.fd, termios.TCIFLUSH)
            except OSError:
                pass
        # Give the VCP a moment to start streaming after the line change.
        time.sleep(0.2)

    # ------------------------------------------------------------------ send
    def send(self, message):
        """Send a string (or bytes) command to the ESC."""
        if self.fd is None:
            return
        if isinstance(message, str):
            message = message.encode('ascii')
        try:
            os.write(self.fd, message)
        except OSError:
            pass

    # --------------------------------------------------------------- receive
    def receive(self, max_length=128, timeout=1.0):
        """Read the incoming burst and return it as a string, or None.

        Returns as soon as at least one complete line (terminated by '\\n')
        has arrived — the Commander telemetry stream is line-oriented at
        ~20 Hz, so this yields a full TEL line for the parser. Falls back to
        whatever partial data is present when ``timeout`` expires.
        """
        if self.fd is None:
            return None
        deadline = time.time() + timeout
        buf = b""
        while time.time() < deadline:
            remaining = deadline - time.time()
            r, _, _ = select.select([self.fd], [], [], max(0.0, remaining))
            if self.fd in r:
                try:
                    chunk = os.read(self.fd, max_length)
                except OSError:
                    break
                if chunk:
                    buf += chunk
                    # A complete line is enough for one telemetry sample.
                    if b"\n" in buf:
                        break
        if not buf:
            return None
        return buf.decode('ascii', errors='ignore')

    # ----------------------------------------------------------------- close
    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None


# Alias so callers can import either name (the flight code refers to the
# transport generically as "UARTInterface").
UARTInterface = USBSerialInterface
