## Overall system design
# SendTelem - runs on a thread and has awaits with timeouts to gather data from each datasource
from declarations import *
from RADXA_SPI_INTERFACE import PDU_ADC, THERMAL_ADC
from RADXA_I2C_INTERFACE import I2CInterface
import asyncio
import struct

class SendImage(threading.Thread):
    """Handles data gathering and sending of telemetry"""
    def __init__(self, socketUDP, socketTCP, temp_controllers, forwarded_telem=b""):
        """socket must be a UDP and TCP socket with a timeout set.
        temp_controllers is a dict mapping thermal"""
        super().__init__()
        self.socketUDP = socketUDP
        self.socketTCP = socketTCP
'''
        # Create ADC objects (do this once in your main program)
        self.pdu_adc = PDU_ADC()
        self.pdu_adc_readings = [0]*8
        self.thermal_adc = THERMAL_ADC()
        self.thermal_adc_readings = [0]*7

        # List of all temp controllers in the system
        self.controllers = temp_controllers

        #Telemetry forwarded from other boards, if present
        self.forwarded_telem = forwarded_telem

        # Create I2C objects 
        #self.i2c = I2CInterface()

        # GPIO general
        self.gpio_PG_5 = gpio_PG_5            
        self.gpio_PG_9 = gpio_PG_9
        self.gpio_PG_12 = gpio_PG_12
        self.gpio_readings = [0]*3
        self.gpios = [self.gpio_PG_5, self.gpio_PG_9, self.gpio_PG_12]
        self.gpio_names = ["PG_5", "PG_9", "PG_12"]

        self.results = []

        self.error_report = "" # string that accumulates errors to send back to base station for each telem set sent
'''  
    # todo: saving data to files
    def run(self):
        while True:
            # time.sleep(0.5)
            asyncio.run(self.send_image_loop()) # runs as coroutine

    async def send_image_loop(self):
        # 1) async fetch all data, with a timeout
        # 2) aggregate data to packet
        # 3) send over tcp
'''
        # data fetch
        gpio_tasks = [self.read_gpio(i) for i in range(3)]
        try:
            self.results = await asyncio.wait_for(
                asyncio.gather(
                    self.read_adcs(),
                    self.read_i2c_sensors(),
                    *gpio_tasks,
                    return_exceptions=True),
                    DATA_WAIT_TIMEOUT
                )
        except TimeoutError:
            print("Data gathering timed out")

        # data aggregation
        results_string = ",0," #The 0 is a placeholder for the timestamp.
        
        results_string += f"{self.results[0][0][0]},"#5V
        results_string += f"{self.results[0][0][1]},"#12V
        results_string += f"{self.results[0][0][2]},"#9V
        results_string += f"{self.results[0][0][3]},"#28V
        results_string += f"{self.results[0][0][4]},"#5V_I
        results_string += f"{self.results[0][0][5]},"#12V_I
        results_string += f"{self.results[0][0][6]},"#9V_I
        temperatures = self.results[0][1]
        for temperature in temperatures[:4]:
            results_string += f"{temperature},"#TEMP - This is just for testing.
        results_string += f"{self.results[1][0]},"#PRESSURE_hPa
        results_string += f"{self.results[1][1][0]},"#XACC_mg
        results_string += f"{self.results[1][1][1]},"#YACC_mg
        results_string += f"{self.results[1][1][2]},"#ZACC_mg
        results_string += f"{self.results[1][2][0]},"#XMAG_uT
        results_string += f"{self.results[1][2][1]},"#YMAG_uT
        results_string += f"{self.results[1][2][2]},"#ZMAG_uT
        for idx, result in enumerate(self.results[2:]):
            results_string += f"{result},"#GPIOs

        results_string += "2000," #Placeholder for motor rotation count
        
        results_bytes = results_string.encode('utf-8') + self.forwarded_telem
        length_prefix = struct.pack('>I', len(results_bytes))

        results_bytes = length_prefix + results_bytes

        # send to control loop
        for controller in self.controllers:
            print(f"Temps: {temperatures}")
            controller.add_datapoint(temperatures[HEATER_SENSOR_PAIRS[controller.peripheral_name]])
'''
        # Image sending
        os.system('./takeImage.sh') #placeholder to call Golf's code
        print("Sending image...")
        path = "RealTime.jpg" #path from Golf's code
        total_size = os.path.getsize(path)

        self.socket.sendall(results_bytes)

        print("Size: ", total_size)
        self.rate, add = self.socket.recvfrom(10) #rate from ground station, address of ground station
        print("Rate: ", self.rate.decode())

        with open(path, 'rb') as f:
             while True:
                    time.sleep(float(self.rate))
                    bytes_read = f.read(self.buffer)
                    #print("Bytes: ", bytes_read)
                    if not bytes_read:
                        break  # File transmitting is done
                    self.socket.sendto(bytes_read, self.UDP_info)
            print("Image sent.")

        except Exception as e:
            print(f'An exception occurred in SendImage: {e}')
        

'''
    async def read_adcs(self):
        # ADCs have to be read in sequence as they use common SPI bus
        try:
            pdu = self.pdu_adc.poll()
        except Exception as e:
            pdu = [0]*8#"ERROR"
            print(f"ERROR: PDU Read Failed\n{e}")
        try:
            thermal = self.thermal_adc.poll()
        except:
            thermal = [0]*7#"ERROR"
            print("ERROR: Thermal Read Failed")
        return pdu, thermal
    
    async def read_i2c_sensors(self):

        pressure = 0
        acc = (0,0,0)
        mag_field = (0,0,0)

        try:
            pressure = self.i2c.read_pressure()
            acc = self.i2c.read_accelerometer_data()
            mag_field = self.i2c.read_magnetometer_data()
        except:
            print("ERROR: I2C Read Failed")

        return pressure, acc, mag_field

    async def read_gpio(self, idx):
        try:
            return self.gpios[idx].read()
        except:
            print(f"Fetch from GPIO {self.gpio_names[idx]} Timeout")
            return 0#"ERROR"
'''