from declarations import *

class PeripheralDriver(threading.Thread):
	'''
	Singleton. Do not make any new instances. Use instance `peripherals`.
	Manages reading and writing to peripherals via the MC74HC595A shift register.
	stop and start the thread with stop_t() and start_t()
	'''
	def __init__(self) -> None:
		super().__init__()

		global peripheral_requests

		gpio_P_nRST.write(1)
		gpio_P_OUT_EN.write(0)
		self.output  = np.zeros(8) # keeps track of values on output
		self.register = np.zeros(8) # keeps track of value in register
		self.continue_run = True
		self.bindings_iterable = [value for key, value in sorted(PERIPH_BINDINGS.items(), key = lambda item : item[1])] # sorted over values of PERIPH_BINDINGS

	def stop_t(self):
		self.continue_run = False
	
	def start_t(self):
		self.continue_run = True

	def add_element(self,x: int) -> None:
		gpio_P_SCLK.write(0)
		i = 1 if x else 0
		gpio_P_DIN.write(i)
		gpio_P_SCLK.write(1)
		self.register = np.roll(self.register)
		self.register[0] = i

	def output_highZ(x) -> None:
		gpio_P_OUT_EN.write(x)

	def send_output(self) -> None:
		gpio_P_LATCH_CLK.write(0)
		gpio_P_LATCH_CLK.write(1)
		gpio_P_LATCH_CLK.write(0)
		self.output[:] = self.register[:]

	def reset(self) -> None:
		with peripheral_requests_lock:
			for x in PERIPH_BINDINGS.keys(): peripheral_requests[x] = 0
		gpio_P_nRST.write(0)
		gpio_P_nRST.write(1)
		self.register[:] = 0
	
	def run(self):
		while self.continue_run():
			time.sleep(0.00001) # delay maybe not needed
			with peripheral_requests_lock:
				if peripheral_requests_reset:
					self.reset()
					continue
				if peripheral_requests_highZ:
					self.output_highZ()
					continue
			for peripheral_name in self.bindings_iterable:
				with peripheral_requests_lock:
					x = peripheral_requests[peripheral_name]
				self.add_element(x)
			self.send_output()


	def write_peripheral(self, peripheral: str | int, val: int):
		if isinstance(peripheral, int):
			i = peripheral
		elif isinstance(peripheral, str):
			i = PERIPH_BINDINGS[peripheral]
		else:
			raise TypeError
		for x in range(8):
			if x == i:
				self.add_element(val)
			else:
				self.add_element(self.output[8-x])

peripherals = PeripheralDriver()
# call peripheral run