# see test script ADC_SPI_TEST.py for explanation
# This module provides functions to read from the two ADC128S052 ADCs connected via SPI
# Call poll_pdu_adc() and poll_thermal_adc() to get lists of readings from each ADC
# Call close_adcs() at shutdown to clean up
# Can add further error handling as needed...
import mraa
import time
import LMT87_LookUpTable

class SPI_ADC128S052:
    def __init__(self, spi_index, cs_pin, freq=3200000):
        self.spi = mraa.Spi(spi_index)
        self.cs = mraa.Gpio(cs_pin)
        self.cs.dir(mraa.DIR_OUT)
        self.cs.write(1)
        self.spi.frequency(freq)
        self.spi.lsbmode(False)
        self.spi.mode(0)

    def read_channel(self, channel):
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

if __name__ == "__main__":
    PDU_SPI_CS_PIN = 150
    THERMAL_SPI_CS_PIN = 153

    # Create ADC objects (do this once in your main program)
    pdu_adc = SPI_ADC128S052(3, PDU_SPI_CS_PIN)
    thermal_adc = SPI_ADC128S052(3, THERMAL_SPI_CS_PIN)

    def poll_pdu_adc():
        """Poll all channels of the PDU ADC and return a list of values."""
        return [pdu_adc.read_channel(ch) for ch in range(8)]

    def poll_thermal_adc():
        """Poll all channels of the Thermal ADC and return a list of values."""
        return [LMT87_LookUpTable.lookup_closest(1000*thermal_adc.read_channel(ch)) for ch in range(8)]

    def close_adcs():
        """Call this at shutdown to clean up."""
        pdu_adc.close()

        thermal_adc.close()

    while True:
        time.sleep(1)
        print(f"PDU ADC: {poll_pdu_adc()}")
        # print(f"TEMP ADC: {poll_pdu_adc()}")