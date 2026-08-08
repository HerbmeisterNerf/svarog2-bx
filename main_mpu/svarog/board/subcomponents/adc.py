import declarations
from spi import SPI

ADC_FREQ = 4800000

try:
    import LMT87_LookUpTable
    HAS_LMT87 = True
except ImportError:
    HAS_LMT87 = False


class SPI_ADC128S052:
    def __init__(self, cs_pin):
        self.cs_pin = cs_pin

    def read_channel(self, channel):
        if not SPI.available:
            return 0.0
        cmd = (channel & 0x07) << 3
        tx = bytearray([cmd, 0x00, 0x00, 0x00])
        rx = SPI.transfer(tx, self.cs_pin, ADC_FREQ, inv=True)
        value = ((rx[2] & 0xFF) << 8) | rx[3]
        voltage = (value * 5) / 4096
        return voltage

    # def read_all(self):
    #     if not SPI.available:
    #         return [0.0] * (len(self.read_tx) // 2)
    #     raws = SPI.transfer(self.read_tx, self.cs_pin, ADC_FREQ, inv=True)
    #     ret = [
    #         (int.from_bytes(raws[i:i+2], byteorder="big") & 0x0FFF) * 5/4096
    #         for i in range(0, len(self.read_tx), 2)
    #     ]
    #     return ret


class PDU_ADC(SPI_ADC128S052):
    def __init__(self):
        super().__init__(declarations.PDU_SPI_CS)

    def poll(self):
        return {
            "V_SENSE5":  2 * self.read_channel(1),
            "V_SENSE9":  2 * self.read_channel(2),
            "V_SENSE12": 2 * self.read_channel(3),
            "ADC_V5":    116 / 16 * self.read_channel(4),
            "ADC_V9":    116 / 16 * self.read_channel(5),
            "ADC_V12":   116 / 16 * self.read_channel(6),
            "ADC_V28":   116 / 16 * self.read_channel(7),
        }


class THERMAL_ADC(SPI_ADC128S052):
    def __init__(self):
        super().__init__(declarations.THERMAL_SPI_CS)

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

    # def poll_all(self):
    #     raw = self.read_all()
    #     ret = {}
    #     for i in range(len(raw)):
    #         ret[declarations.THERMAL_LABELS] = LMT87_LookUpTable.lookup_closest(1000 * raw[i])
    #     return ret