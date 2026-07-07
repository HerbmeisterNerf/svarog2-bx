from declarations import *

try:
    import LMT87_LookUpTable
    HAS_LMT87 = True
except ImportError:
    HAS_LMT87 = False

class SPI_ADC128S052:
    def __init__(self, cs_pin, spi_index=3, freq=3200000):
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
        voltage = (value * 5) / 4096
        return voltage

    def close(self):
        self.spi = None
        self.cs = None


class PDU_ADC(SPI_ADC128S052):
    def __init__(self):
        super().__init__(PDU_SPI_CS)

    def poll(self):
        return {
            "V_SENSE5":  self.read_channel(0),
            "V_SENSE9":  self.read_channel(1),
            "V_SENSE12": self.read_channel(2),
            "ADC_V5":    self.read_channel(3),
            "ADC_V9":    self.read_channel(4),
            "ADC_V12":   self.read_channel(5),
            "ADC_V28":   self.read_channel(6),
        }


class THERMAL_ADC(SPI_ADC128S052):
    def __init__(self):
        super().__init__(THERMAL_SPI_CS)

    def poll(self):
        raw = [self.read_channel(ch) for ch in range(8)]
        if HAS_LMT87:
            return {
                "THERMAL_SENS_OUT_1": LMT87_LookUpTable.lookup_closest(1000 * raw[0]),
                "THERMAL_SENS_OUT_2": LMT87_LookUpTable.lookup_closest(1000 * raw[1]),
                "THERMAL_SENS_OUT_3": LMT87_LookUpTable.lookup_closest(1000 * raw[2]),
                "THERMAL_SENS_OUT_4": LMT87_LookUpTable.lookup_closest(1000 * raw[3]),
                "THERMAL_SENS_OUT_5": LMT87_LookUpTable.lookup_closest(1000 * raw[4]),
                "THERMAL_SENS_OUT_6": LMT87_LookUpTable.lookup_closest(1000 * raw[5]),
                "THERMAL_SENS_INT_1": LMT87_LookUpTable.lookup_closest(1000 * raw[6]),
                "THERMAL_SENS_INT_2": LMT87_LookUpTable.lookup_closest(1000 * raw[7]),
            }
        else:
            labels = [
                "THERMAL_SENS_OUT_1", "THERMAL_SENS_OUT_2",
                "THERMAL_SENS_OUT_3", "THERMAL_SENS_OUT_4",
                "THERMAL_SENS_OUT_5", "THERMAL_SENS_OUT_6",
                "THERMAL_SENS_INT_1", "THERMAL_SENS_INT_2",
            ]
            return {k: v for k, v in zip(labels, raw)}


if __name__ == "__main__":
    pdu_adc = PDU_ADC()
    thermal_adc = THERMAL_ADC()

    def close_adcs():
        pdu_adc.close()
        thermal_adc.close()

    try:
        while True:
            time.sleep(1)
            print("PDU ADC:", pdu_adc.poll())
            print("TEMP ADC:", thermal_adc.poll())
    except KeyboardInterrupt:
        close_adcs()
