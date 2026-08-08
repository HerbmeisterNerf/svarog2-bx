from declarations import *

try:
    import LMT87_LookUpTable
    HAS_LMT87 = True
except ImportError:
    HAS_LMT87 = False


class SPI_ADC128S052:
    def __init__(self, cs_pin):
        self.cs = mraa.Gpio(cs_pin)
        self.cs.dir(mraa.DIR_OUT)
        self.read_tx = bytearray([
                        (0 & 0x7)<<3, 0,
                        (1 & 0x7)<<3, 0,
                        (2 & 0x7)<<3, 0,
                        (3 & 0x7)<<3, 0,
                        (4 & 0x7)<<3, 0,
                        (5 & 0x7)<<3, 0,
                        (6 & 0x7)<<3, 0,
                        (7 & 0x7)<<3, 0])
        # print(self.read_tx)
    def read_channel(self, channel):
        cmd = (channel & 0x07) << 3
        tx = bytearray([cmd, 0x00])
        # tx = bytearray([0x00, cmd])
        # send first 3 zeros,
        # then 3 bits for address
        # writebyte of the channel is fine
        # cmd = channel & 0xFF
        # cmd = cmd << 3
        self.cs.write(0)
        time.sleep(1e-6)
        rx = spi.write(tx)
        # rx = spi.writeWord(cmd) & 0x0FFF
        time.sleep(1e-6)
        self.cs.write(1)
        value = ((rx[0] & 0xFF) << 8) | rx[1] # swapped
        # print(f"RXed: {rx}")
        # value = rx
        # print(value)
        voltage = (value * 5) / 4096
        return voltage

    def read_all(self):
        self.cs.write(0)
        raws = (spi.write(self.read_tx))
        self.cs.write(1)
        # print(raws)
        ret = [
            (int.from_bytes(raws[i:i+2], byteorder="big") & 0x0FFF) * 5/4096
            for i in range(0, len(self.read_tx), 2)
        ]
        return ret



class PDU_ADC(SPI_ADC128S052):
    def __init__(self):
        super().__init__(PDU_SPI_CS)

    def poll(self):
        return {
            "V_SENSE5":  2* self.read_channel(1),
            "V_SENSE9":  2* self.read_channel(2),
            "V_SENSE12": 2* self.read_channel(3),
            "ADC_V5":    116/16 * self.read_channel(4),
            "ADC_V9":    116/16 * self.read_channel(5),
            "ADC_V12":   116/16 * self.read_channel(6),
            "ADC_V28":   116/16 * self.read_channel(7),
        }


class THERMAL_ADC(SPI_ADC128S052):
    def __init__(self):
        super().__init__(THERMAL_SPI_CS)

    def poll(self):
        raw = [self.read_channel(ch) for ch in range(8)]
        print(raw)
        if HAS_LMT87:
            ret = {
                "THERMAL_SENS_OUT_1": LMT87_LookUpTable.lookup_closest(1000 * raw[0]),
                "THERMAL_SENS_OUT_2": LMT87_LookUpTable.lookup_closest(1000 * raw[1]),
                "THERMAL_SENS_OUT_3": LMT87_LookUpTable.lookup_closest(1000 * raw[2]),
                "THERMAL_SENS_OUT_4": LMT87_LookUpTable.lookup_closest(1000 * raw[3]),
                "THERMAL_SENS_OUT_5": LMT87_LookUpTable.lookup_closest(1000 * raw[4]),
                "THERMAL_SENS_OUT_6": LMT87_LookUpTable.lookup_closest(1000 * raw[5]),
                "THERMAL_SENS_INT_1": LMT87_LookUpTable.lookup_closest(1000 * raw[6]),
                "THERMAL_SENS_INT_2": LMT87_LookUpTable.lookup_closest(1000 * raw[7]),
            }
            return [r for r in ret.items() if r[1] != -50]
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
            # print(thermal_adc.read_all())
    except KeyboardInterrupt:
        close_adcs()
