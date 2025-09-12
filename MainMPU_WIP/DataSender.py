## Overall system design
# SendTelem - runs on a thread and has awaits with timeouts to gather data from each datasource
from declarations import *
from RADXA_SPI_INTERFACE import SPI_ADC128S052
from RADXA_I2C_INTERFACE import SensorInterface
import asyncio

class SendTelem(threading.Thread):
    """Handles data gathering and sending of telemetry"""
    def __init__(self, socket):
        """socket must be a TCP socket with a timeout set."""
        self.socket = socket

        # Create ADC objects (do this once in your main program)
        self.pdu_adc = SPI_ADC128S052(3, PDU_SPI_CS_PIN)
        self.pdu_adc_readings = [0]*8
        self.thermal_adc = SPI_ADC128S052(3, THERMAL_SPI_CS_PIN)
        self.thermal_adc_readings = [0]*8

        # Create I2C objects 
        self.sensor_interface = SensorInterface()

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
            asyncio.run(self.send_telem_loop()) # runs as coroutine

    async def send_telem_loop(self):
        # 1) async fetch all data, with a timeout
        # 2) aggregate data to packet
        # 3) send over tcp

        # data fetch
        gpio_tasks = [self.read_gpio(i) for i in range(4)]
        try:
            async with asyncio.timeout(5): # 5 seconds wait max. for total data gathering
                self.results = await asyncio.gather(
                    self.read_adcs(),
                    *gpio_tasks,
                    return_exceptions=True)
        except TimeoutError:
            print("Data gathering timed out")

        # data aggregation
        results_string = ""
        
        results_string += f"PDU={self.results[0][0]}\n"
        results_string += f"TEMP={self.results[0][1]}\n"
        for idx, result in enumerate(self.results[1:]):
            results_string += f"{self.gpio_names[idx]}={result}\n"

        #todo: send to control loop

        # TCP sending
        self.socket.sendall(results_string.encode("utf-8"))
        print("Sent Telemetry")


    async def read_adcs(self):
        # ADCs have to be read in sequence as they use common SPI bus
        try:
            pdu = [self.pdu_adc.read_channel(i) for i in range(8)] 
        except:
            pdu = "ERROR"
            print("ERROR: PDU Read Failed")
        try:
            thermal = [self.thermal_adc.read_channel(i) for i in range(8)]
        except:
            thermal = "ERROR"
            print("ERROR: Thermal Read Failed")
        return pdu, thermal

    async def read_gpio(self, idx):
        try:
            return self.gpios[idx].read()
        except:
            print(f"Fetch from GPIO {self.gpio_names[idx]} Timeout")
            return "ERROR"

            

