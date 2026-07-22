# see test script ADC_SPI_TEST.py for explanation
# This module provides functions to read from the two ADC128S052 ADCs connected via SPI
# Call poll_pdu_adc() and poll_thermal_adc() to get lists of readings from each ADC
# Call close_adcs() at shutdown to clean up
# Can add further error handling as needed...
import mraa
import time
import LMT87_LookUpTable
from declarations import *


class SPI_ADC128S052:
    def __init__(self, cs_pin,  spi_index=3, freq=3200000):
        self.spi = mraa.Spi(spi_index)
        self.cs = mraa.Gpio(cs_pin)
        self.cs.dir(mraa.DIR_OUT)
        self.cs.write(1)
        self._freq = freq
        self._apply_bus()

    def _apply_bus(self):
        """(Re)assert this device's bus settings. Required because the AS5047
        encoder shares SPI(3) at Mode 1 (see RADXA_ENCODER_INTERFACE); the mraa
        bus mode is global, so re-apply Mode 0 before every ADC transaction."""
        self.spi.frequency(self._freq)
        self.spi.lsbmode(False)
        self.spi.mode(0)

    def read_channel(self, channel):
        self._apply_bus()
        cmd = (channel & 0x07) << 3
        tx = bytearray([cmd, 0x00])
        self.cs.write(0)
        rx = self.spi.write(tx)
        self.cs.write(1)
        value = ((rx[0] & 0x0F) << 8) | rx[1]
        voltage = (value * 5) / 4096  # Assuming Vref = 5V, convert to voltage
        return voltage

    def close(self):
        self.spi = None
        self.cs = None


class PDU_ADC(SPI_ADC128S052):
    def __init__(self):
        super().__init__(PDU_SPI_CS)

    def poll(self):
        """Poll all channels of the PDU ADC and return a list of values."""
        ret = []
        ret.append(self.read_channel(1))
        ret.append(self.read_channel(2)*12/4.32203)
        ret.append(self.read_channel(3)*9/4.1917)
        ret.append(self.read_channel(4)*28/4.30769)
        for _i in range(5, 8):
            ret.append(self.read_channel(_i) * 2)
        return ret

class THERMAL_ADC(SPI_ADC128S052):
    def __init__(self):
        super().__init__(THERMAL_SPI_CS)

    def poll(self):
        """Poll all channels of the PDU ADC and return a list of values."""
        return [LMT87_LookUpTable.lookup_closest(1000*thermal_adc.read_channel(ch)) for ch in range(8)]


if __name__ == "__main__":

    # Create ADC objects (do this once in your main program)
    pdu_adc = PDU_ADC()
    thermal_adc = THERMAL_ADC()

    def close_adcs():
        """Call this at shutdown to clean up."""
        pdu_adc.close()

        thermal_adc.close()

    while True:
        try:
            time.sleep(1)
            print(f"PDU ADC: {pdu_adc.poll()}")
            print(f"TEMP ADC: {thermal_adc.poll()}")
        except KeyboardInterrupt:
            close_adcs()
            quit()