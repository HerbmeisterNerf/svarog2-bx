from declarations import *
import time

REG_NOP      = 0x0000
REG_ERRFL    = 0x0001
REG_DIAAGC   = 0x3FFC
REG_ANGLECOM = 0x3FFF


def with_parity(v):
    """Even parity over the lower 15 bits, placed into bit 15."""
    p = v & 0x7FFF
    p ^= p >> 8
    p ^= p >> 4
    p ^= p >> 2
    p ^= p >> 1
    if p & 1:
        v |= 0x8000
    return v

# TODO: test pin 28 can be gpioget/set-ed

class SPIEncoder:
    """AS5047P register-based SPI encoder (mode 1, 1 MHz, pipelined reads).

    Commands follow the AS5047 protocol: a 16-bit frame of
    [parity|read=1|addr|wr_data]. Reads are pipelined - issue the read
    command, then a NOP command, and the next frame returns the answer.
    Response strips parity (bit15) and error flag (bit14).
    """
    def __init__(self, cs_pin=ENCODER_SPI_CS, spi_index=3, freq=1000000, mode=1):
        self.cs = mraa.Gpio(cs_pin)
        self.cs.dir(mraa.DIR_OUT)
        self.cs.write(1)
        self.spi = mraa.Spi(spi_index)
        self.spi.frequency(freq)
        self.spi.lsbmode(False)
        self.spi.mode(mode)

    def _xfer16(self, frame):
        """Send one 16-bit frame (big-endian), return the 16-bit response."""
        # tx = bytearray([(frame >> 8) & 0xFF, frame & 0xFF])
        tx = frame & 0xFFFF
        self.cs.write(0)
        time.sleep(1e-6)
        # rx = self.spi.write(tx)
        rx = self.spi.writeWord(tx)
        self.cs.write(1)
        time.sleep(1e-6)
        return rx
        # if len(rx) < 2:
        #     return 0
        # return (rx[0] << 8) | rx[1]

    def write_reg(self, addr, value):
        self._xfer16(with_parity((addr & 0x3FFF) | (value & 0x3FFF)))

    def read_reg(self, addr):
        # cmd = with_parity((addr & 0x3FFF) | 0x4000)  # bit14 = read
        cmd = with_parity(addr | 0x4000)  # bit14 = read
        self._xfer16(cmd)
        resp = self._xfer16(with_parity(REG_NOP | 0x4000))
        return resp & 0x3FFF

    def read_all(self):
        """Read DIAAGC diagnostics + ANGLECOM, return a dict of readings."""
        diag = self.read_reg(REG_DIAAGC)
        angle = self.read_reg(REG_ANGLECOM)
        return {
            "angle_raw": angle,
            "angle_deg": angle * 360.0 / 16384.0,
            "agc": diag & 0xFF,
            "mag_low": bool(diag & (1 << 11)),
            "mag_high": bool(diag & (1 << 10)),
            "cof": bool(diag & (1 << 9)),
            "lf": bool(diag & (1 << 8)),
            "diag_raw": diag,
            "raw_hex": f"diag={diag:04X} angle={angle:04X}",
        }

    def read_angle(self):
        """Read and return angle in degrees."""
        return self.read_all()["angle_deg"]

    def close(self):
        self.spi = None
        self.cs = None


class AS5048A(SPIEncoder):
    """Compatibility driver for AS5048A/B (raw 14-bit framing, mode 1)."""
    def __init__(self, cs_pin=ENCODER_SPI_CS, spi_index=3):
        super().__init__(cs_pin, spi_index, freq=1000000, mode=1)

    def read_raw_angle(self):
        rx = self._xfer16(0xFFFF)
        return ((rx >> 6) & 0x3F) << 8 | (rx & 0xFF)

    def read_angle(self):
        return self.read_raw_angle() * 360.0 / 16384.0

    def read_all(self):
        rx = self._xfer16(0xFFFF)
        raw = ((rx >> 6) & 0x3F) << 8 | (rx & 0xFF)
        return {
            "angle_raw": raw,
            "angle_deg": raw * 360.0 / 16384.0,
            "ocf": (rx >> 14) & 1,
            "cof": (rx >> 13) & 1,
            "raw_hex": f"{rx:04X}",
        }


if __name__ == "__main__":
    import sys
    cs_pin = int(sys.argv[1]) if len(sys.argv) > 1 else ENCODER_SPI_CS
    print(f"AS5047 encoder test on CS pin {cs_pin} (SPI3)")
    enc = SPIEncoder(cs_pin=cs_pin)
    try:
        while True:
            print(f"  {enc.read_angle()}")
            time.sleep(0.25)
    except KeyboardInterrupt:
        enc.close()
        print("Done")