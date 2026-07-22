"""Bench test: AS5047 magnetic encoder on the Radxa 40-pin SPI bus.

Standalone Phase-1 bring-up. Exercises RADXA_ENCODER_INTERFACE.AS5047 directly:
prints absolute angle + magnet-health diagnostics so you can confirm wiring,
CS pin, power and SPI mode before wiring the encoder into flight telemetry.

Run on the board:  python3 encoder_spi_test.py
Bring a diametrically-magnetised magnet over the chip and rotate it; the angle
should track 0..360 and AGC should drop from 255 into ~30..200 with magLow=0.
"""
import os
import sys
import time

# import the flight modules from the parent hardware/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from RADXA_ENCODER_INTERFACE import AS5047

try:
    from declarations import ENCODER_SPI_CS
except Exception:
    # declarations pulls in the whole GPIO map; allow an override if it can't load
    ENCODER_SPI_CS = int(os.environ.get("ENCODER_SPI_CS", "22"))
    print(f"[warn] using ENCODER_SPI_CS={ENCODER_SPI_CS} (declarations import failed)")


def main():
    enc = AS5047(ENCODER_SPI_CS)
    print(f"AS5047 on SPI(3) CS=pin{ENCODER_SPI_CS} @ Mode 1. Ctrl+C to stop.\n")
    bad = 0
    try:
        while True:
            d = enc.read_diagnostics()
            if not d["valid"]:
                bad += 1
                print(f"[{bad}] No valid response (0x{d['raw']:04X}) -> "
                      f"check MOSI/MISO/SCLK/CS wiring, 5V/3V3 power, SPI Mode 1")
            else:
                bad = 0
                angle = enc.read_angle()
                flags = []
                if d["mag_low"]:  flags.append("MAG_LOW(too far)")
                if d["mag_high"]: flags.append("MAG_HIGH(too close)")
                if not d["offset_ready"]: flags.append("not-ready")
                status = " ".join(flags) if flags else "OK"
                print(f"angle={angle:6.1f} deg  raw={enc.read_raw():5d}  "
                      f"AGC={d['agc']:3d}  {status}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        enc.close()
        print("\nclosed.")


if __name__ == "__main__":
    main()
