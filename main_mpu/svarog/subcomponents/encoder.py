import declarations as d
import time


class SPIEncoder:
    def __init__(self, cs_pin=None, spi_index=3, freq=1000000, mode=0):
        if cs_pin is None:
            cs_pin = d.ENCODER_SPI_CS
        self.cs = d.mraa.Gpio(cs_pin)
        self.cs.dir(d.mraa.DIR_OUT)
        self.cs.write(1)
        self.spi = d.mraa.Spi(spi_index)
        self.spi.frequency(freq)
        self.spi.lsbmode(False)
        self.spi.mode(mode)

    def read_raw(self, tx_bytes):
        tx = bytearray(tx_bytes)
        self.cs.write(0)
        rx = self.spi.write(tx)
        self.cs.write(1)
        return bytes(rx)

    def read_angle(self):
        rx = self.read_raw([0xFF, 0xFF])
        angle = ((rx[0] << 8) | rx[1]) & 0x3FFF
        return angle * 360.0 / 16384.0

    def read_all(self):
        rx = self.read_raw([0xFF, 0xFF])
        angle_raw = ((rx[0] << 8) | rx[1]) & 0x3FFF
        return {
            "angle_raw": angle_raw,
            "angle_deg": angle_raw * 360.0 / 16384.0,
            "raw_hex": rx.hex(),
        }

    def close(self):
        self.spi = None
        self.cs = None


class AS5048A(SPIEncoder):
    def __init__(self, cs_pin=None, spi_index=3):
        if cs_pin is None:
            cs_pin = d.ENCODER_SPI_CS
        super().__init__(cs_pin, spi_index, freq=1000000, mode=1)

    def read_raw_angle(self):
        rx = self.read_raw([0xFF, 0xFF])
        return ((rx[0] & 0x3F) << 8) | rx[1]

    def read_angle(self):
        raw = self.read_raw_angle()
        return raw * 360.0 / 16384.0

    def read_all(self):
        rx = self.read_raw([0xFF, 0xFF])
        raw = ((rx[0] & 0x3F) << 8) | rx[1]
        ocf = (rx[0] >> 6) & 1
        cof = (rx[0] >> 7)  & 1
        parity = rx[1] >> 7 if len(rx) > 1 else 0
        return {
            "angle_raw": raw,
            "angle_deg": raw * 360.0 / 16384.0,
            "ocf": ocf,
            "cof": cof,
            "raw_hex": rx.hex(),
        }
