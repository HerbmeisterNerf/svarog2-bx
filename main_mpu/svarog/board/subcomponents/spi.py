import threading

import declarations as d


class SPIBus:
    """Single shared SPI bus with a lock serialising every transfer.

    All peripherals (ADC, encoder, ...) use the one mraa.Spi instance and drive
    their own chip-select GPIO. ``transfer`` acquires the bus lock, sets the
    clock/lsb-mode/SPI-mode for this transaction, asserts the CS pin, and
    releases it back to its idle state afterwards.
    """

    def __init__(self, spi_index=None, freq=1000000, lsbmode=False, mode=0):
        self._lock = threading.Lock()
        self._gpios = {}
        self.available = False
        if spi_index is None:
            spi_index = d.SPI_INDEX
        try:
            self._spi = d.mraa.Spi(spi_index)
            self._spi.frequency(freq)
            self._spi.lsbmode(lsbmode)
            self._spi.mode(mode)
            self.available = True
        except Exception as e:
            print(f"[spi] init failed (bus {spi_index}): {e}")
            self._spi = None

    def _cs(self, pin):
        """Look up / create an output GPIO for the given CS chip select."""
        g = self._gpios.get(pin)
        if g is None:
            g = d.mraa.Gpio(pin)
            g.dir(d.mraa.DIR_OUT)
            self._gpios[pin] = g
        return g

    def transfer(self, tx: bytearray, cs_pin, freq: int, inv: bool = True,
                 lsbmode: bool = None, mode: int = None) -> bytes:
        """One atomic SPI transaction.

        Parameters
        ----------
        tx : bytearray
            data to clock out (MISO data is returned).
        cs_pin : int
            the CS GPIO that selects the target peripheral.
        freq : int
            SPI clock (Hz) to use for this single transfer.
        inv : bool
            True if CS is active-low (normal): held high at idle, pulled low
            during the transfer, and returned to high after.
        lsbmode, mode : optional overrides for the underlying mraa.Spi.
        """
        if self._spi is None:
            return b"\x00" * len(tx)
        with self._lock:
            self._spi.frequency(freq)
            if lsbmode is not None:
                self._spi.lsbmode(lsbmode)
            if mode is not None:
                self._spi.mode(mode)
            cs = self._cs(cs_pin)
            idle = 1 if inv else 0      # normal / idle state of the pin
            cs.write(1 - idle)          # assert (active) edge
            try:
                rx = self._spi.write(tx)
            finally:
                cs.write(idle)          # back to normal state
            return rx


SPI = SPIBus()