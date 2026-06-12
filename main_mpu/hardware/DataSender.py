## Overall system design
# SendTelem - runs on a thread and has awaits with timeouts to gather data from each datasource
from declarations import *
from RADXA_SPI_INTERFACE import PDU_ADC, THERMAL_ADC
from RADXA_I2C_INTERFACE import I2CInterface
import asyncio

class SendTelem(threading.Thread):
    """Handles data gathering and sending of telemetry"""
    def __init__(self, socket, temp_controllers):
        """socket must be a TCP socket with a timeout set.
        temp_controllers is a dict mapping thermal"""
        super().__init__()
        self.socket = socket

        # Create ADC objects (do this once in your main program)
        self.pdu_adc = PDU_ADC()
        self.pdu_adc_readings = [0]*8
        self.thermal_adc = THERMAL_ADC()
        self.thermal_adc_readings = [0]*7

        # List of all temp controllers in the system
        self.controllers = temp_controllers

        # Create I2C objects 
        # self.i2c = I2CInterface()

        # GPIO general
        self.gpio_MOTCON_EFUSE_FLT = gpio_MOTCON_EFUSE_FLT   
        self.gpio_PG_5 = gpio_PG_5            
        self.gpio_PG_9 = gpio_PG_9
        self.gpio_PG_12 = gpio_PG_12
        self.gpio_readings = [0]*4
        self.gpios = [self.gpio_MOTCON_EFUSE_FLT, self.gpio_PG_5, self.gpio_PG_9, self.gpio_PG_12]
        self.gpio_names = ["MOTCON_EFUSE_FLT", "PG_5", "PG_9", "PG_12"]

        self.results = []

        self.error_report = "" # string that accumulates errors to send back to base station for each telem set sent
    
    # todo: saving data to files
    def run(self):
        while True:
            time.sleep(5)
            asyncio.run(self.send_telem_loop()) # runs as coroutine

    async def send_telem_loop(self):
        # 1) async fetch all data, with a timeout
        # 2) aggregate data to packet
        # 3) send over tcp

        # data fetch
        gpio_tasks = [self.read_gpio(i) for i in range(4)]
        try:
            self.results = await asyncio.wait_for(
                asyncio.gather(
                    self.read_adcs(),
                    # self.read_i2c_sensors(),
                    *gpio_tasks,
                    return_exceptions=True),
                    DATA_WAIT_TIMEOUT
                )
        except TimeoutError:
            print("Data gathering timed out")

        # data aggregation
        results_string = ""
        
        results_string += f"5V={self.results[0][0][0]}\n"
        results_string += f"12V={self.results[0][0][1]}\n"
        results_string += f"9V={self.results[0][0][2]}\n"
        results_string += f"28V={self.results[0][0][3]}\n"
        results_string += f"5V_I={self.results[0][0][4]}\n"
        results_string += f"5V_I={self.results[0][0][5]}\n"
        results_string += f"5V_I={self.results[0][0][6]}\n"
        temperature = self.results[0][1]
        # results_string += f"TEMP={temperature}\n"
        # results_string += f"PRESSURE_hPa={self.results[1][0]}\n"
        # results_string += f"XACC_mg={self.results[1][1][0]}\n"
        # results_string += f"YACC_mg={self.results[1][1][1]}\n"
        # results_string += f"ZACC_mg={self.results[1][1][2]}\n"
        # results_string += f"XMAG_uT={self.results[1][2][0]}\n"
        # results_string += f"YMAG_uT={self.results[1][2][1]}\n"
        # results_string += f"ZMAG_uT={self.results[1][2][2]}\n"
        # for idx, result in enumerate(self.results[2:]):
        #     results_string += f"{self.gpio_names[idx]}={result}\n"
        for idx, result in enumerate(self.results[1:]):
            results_string += f"{self.gpio_names[idx]}={result}\n"

        #@debdut have removed the floating point format above to test if returning errors works

        # send to control loop
        for controller in self.controllers:
            print(f"Temps: {temperature}")
            controller.add_datapoint(temperature[HEATER_SENSOR_PAIRS[controller.peripheral_name]])

        # TCP sending
        self.socket.sendall(results_string.encode("utf-8"))
        # print("Sent Telemetry")


    async def read_adcs(self):
        # ADCs have to be read in sequence as they use common SPI bus
        try:
            pdu = self.pdu_adc.poll()
        except Exception as e:
            pdu = "ERROR"
            print(f"ERROR: PDU Read Failed\n{e}")
        try:
            thermal = self.thermal_adc.poll()
        except:
            thermal = "ERROR"
            print("ERROR: Thermal Read Failed")
        return pdu, thermal
    
    async def read_i2c_sensors(self):

        pressure = 0
        acc = 0
        mag_field = 0

        try:
            pressure = self.i2c.read_pressure()
            acc = self.i2c.read_accelerometer_data()
            mag_field = self.i2c.read_magnetometer_data()
        except:
            print("ERROR: I2C Read Failed")
            return "ERROR"

        return pressure, acc, mag_field

    async def read_gpio(self, idx):
        try:
            return self.gpios[idx].read()
        except:
            print(f"Fetch from GPIO {self.gpio_names[idx]} Timeout")
            return "ERROR"

            

