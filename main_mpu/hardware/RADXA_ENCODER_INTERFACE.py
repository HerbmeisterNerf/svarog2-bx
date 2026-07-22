"""AS5047(P) magnetic rotary encoder over the Radxa 40-pin SPI bus.

Ported from as5047-tool/as5047_test/as5047_test.ino to mraa. Read by the Radxa
for system telemetry (absolute shaft angle + magnet-health diagnostics).

IMPORTANT — shared SPI bus:
  The AS5047 sits on mraa.Spi(3), the SAME bus as the two ADC128S052 ADCs
  (RADXA_SPI_INTERFACE.py). The ADCs run SPI **Mode 0**; the AS5047 runs
  **Mode 1**. mraa bus mode/frequency is global to the bus, so this class
  re-applies mode(1)+frequency at the top of every transaction. The ADC class
  must likewise re-apply mode(0) per transaction (it does, see
  RADXA_SPI_INTERFACE.SPI_ADC128S052.read_channel) so the two can interleave
  safely on one bus.

Wiring (AS5047 -> Radxa 40-pin header):
  MOSI -> pin 19   MISO -> pin 21   SCLK -> pin 23   CS -> ENCODER_SPI_CS
  (see declarations.ENCODER_SPI_CS — confirm the CS pin against the PCB).
"""

import mraa
import time

# AS5047 volatile register addresses (14-bit address space)
REG_NOP      = 0x0000
REG_ERRFL    = 0x0001
REG_DIAAGC   = 0x3FFC   # diagnostics + automatic gain control
REG_ANGLECOM = 0x3FFF   # dynamic-angle-error-compensated angle

_CMD_READ = 0x4000      # bit14 set = read
_ANGLE_FS = 16384.0     # 14-bit full scale (2^14)


def _with_parity(v):
    """Set bit15 to even parity over the lower 15 bits (AS5047 command format)."""
    p = v & 0x7FFF
    p ^= p >> 8
    p ^= p >> 4
    p ^= p >> 2
    p ^= p >> 1
    if p & 1:
        v |= 0x8000
    return v & 0xFFFF


class AS5047:
    def __init__(self, cs_pin, spi_index=3, freq=1000000):
        self.spi = mraa.Spi(spi_index)
        self.cs = mraa.Gpio(cs_pin)
        self.cs.dir(mraa.DIR_OUT)
        self.cs.write(1)               # idle high (deselected)
        self._freq = freq
        self._apply_bus()

    def _apply_bus(self):
        """(Re)assert this device's bus settings — call before every transaction
        because the ADCs share the bus and use a different SPI mode."""
        self.spi.frequency(self._freq)
        self.spi.lsbmode(False)        # MSB first
        self.spi.mode(1)               # AS5047 is SPI Mode 1 (CPOL0, CPHA1)

    def _xfer(self, frame):
        """One 16-bit frame, MSB first, manual CS. Returns the 16-bit response."""
        tx = bytearray([(frame >> 8) & 0xFF, frame & 0xFF])
        self.cs.write(0)
        rx = self.spi.write(tx)
        self.cs.write(1)
        return ((rx[0] << 8) | rx[1]) & 0xFFFF

    def _read_reg(self, addr):
        """AS5047 reads are pipelined: issue the read command, the NEXT frame
        returns the data. Returns the 14-bit payload (parity + error stripped)."""
        self._apply_bus()
        self._xfer(_with_parity(addr | _CMD_READ))
        resp = self._xfer(_with_parity(REG_NOP | _CMD_READ))
        return resp & 0x3FFF

    def read_raw(self):
        """Raw 14-bit compensated angle (0..16383)."""
        return self._read_reg(REG_ANGLECOM)

    def read_angle(self):
        """Absolute shaft angle in degrees (0..360)."""
        return self._read_reg(REG_ANGLECOM) * 360.0 / _ANGLE_FS

    def read_diagnostics(self):
        """Decode DIAAGC: automatic gain + magnet-field health flags."""
        diag = self._read_reg(REG_DIAAGC)
        return {
            "raw": diag,
            "agc": diag & 0xFF,               # 0 (strong field) .. 255 (weak)
            "mag_low": bool(diag & (1 << 11)),  # MAGL: field too weak / too far
            "mag_high": bool(diag & (1 << 10)), # MAGH: field too strong / too close
            "cordic_overflow": bool(diag & (1 << 9)),  # COF
            "offset_ready": bool(diag & (1 << 8)),      # LF: offset loop finished
            "valid": diag not in (0x0000, 0x3FFF),      # both = no valid response
        }

    def close(self):
        self.spi = None
        self.cs = None


if __name__ == "__main__":
    # Minimal smoke test. For the fuller bench test see
    # test_scripts/encoder_spi_test.py. CS pin comes from declarations.
    from declarations import ENCODER_SPI_CS

    enc = AS5047(ENCODER_SPI_CS)
    try:
        while True:
            d = enc.read_diagnostics()
            if not d["valid"]:
                print("No valid response (0x0000/0x3FFF) -> check wiring, CS, power, SPI mode")
            else:
                print(f"angle={enc.read_angle():6.1f} deg  AGC={d['agc']:3d}  "
                      f"magLow={int(d['mag_low'])} magHigh={int(d['mag_high'])} "
                      f"ready={'yes' if d['offset_ready'] else 'no'}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        enc.close()
