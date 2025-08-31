# tests the spi interface to both adcs 
import mraa
import time

class SPI_ADC128S052:
    def __init__(self, spi_index, cs_pin, freq=4000000):
        #initialize SPI and CS pin
        self.spi = mraa.Spi(spi_index) 
        self.cs = mraa.Gpio(cs_pin) 
        self.cs.dir(mraa.DIR_OUT) # Set as output
        self.cs.write(1)  # initialize CS high (not selected)
        self.spi.frequency(freq)
        self.spi.lsbmode(False) # MSB first as per ADC datasheet
        self.spi.mode(0) # SPI mode 0 (Clock Polarity 0, Clock Phase 0)

    def read_channel(self, channel):
        # Read a single channel (0-7) from the ADC
        cmd = (channel & 0x07) << 3 # Command byte for ADC128S052, bits 3-5 are channel, rest don't care
        tx = bytearray([cmd, 0x00]) # Send command and dummy byte, dummy required to clock out data
        self.cs.write(0)  # Select ADC
        rx = self.spi.write(tx) # sends the command and reads back 2 bytes
        self.cs.write(1)  # Deselect ADC
        # first 3 cycles are null, next 12 bits are data
        value = ((rx[0] & 0x0F) << 8) | rx[1]
        return value

    def close(self):
        self.spi = None
        self.cs = None

if __name__ == '__main__':

    PDU_SPI_CS_PIN = 150
    THERMAL_SPI_CS_PIN = 153

    pdu_adc = SPI_ADC128S052(3, PDU_SPI_CS_PIN)
    thermal_adc = SPI_ADC128S052(3, THERMAL_SPI_CS_PIN)

    try:
        while True:
            for ch in range(8):
                # Read from both ADCs, all input channels and print values
                val1 = pdu_adc.read_channel(ch)
                val2 = thermal_adc.read_channel(ch)
                print(f"PDI_ADC Ch{ch}: {val1:04X}  THERMAL_ADC Ch{ch}: {val2:04X}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        # exit on Ctrl+C
        print("Exiting...")
    finally:
        pdu_adc.close()

        thermal_adc.close()

