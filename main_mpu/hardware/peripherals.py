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
		self.output = np.zeros(8)  # keeps track of values on output
		self.register = np.zeros(8)  # keeps track of value in register
		self.continue_run = True
		self.bindings_iterable = [key for key, value in sorted(PERIPH_BINDINGS.items(
		# sorted over values of PERIPH_BINDINGS
		), key=lambda item: item[1], reverse=True)]
		print(self.bindings_iterable)

	def stop_t(self):
		self.continue_run = False

	def start_t(self):
		self.continue_run = True

	def add_element(self, x: int) -> None:
		gpio_P_SCLK.write(0)
		gpio_P_DIN.write(x)
		time.sleep(0.001)
		gpio_P_SCLK.write(1)
		gpio_P_SCLK.write(0)
		self.register = np.roll(self.register, 1)
		self.register[0] = x
		# print(f"reg: {self.register}")

	def output_highZ(x) -> None:
		gpio_P_OUT_EN.write(x)

	def send_output(self) -> None:
		gpio_P_LATCH_CLK.write(0)
		time.sleep(0.001)
		gpio_P_LATCH_CLK.write(1)
		gpio_P_LATCH_CLK.write(0)
		self.output[:] = self.register[:]
		print(f"output: {self.output}")

	def reset(self) -> None:
		with peripheral_requests_lock:
			for x in PERIPH_BINDINGS.keys(): peripheral_requests[x] = 0
		gpio_P_nRST.write(0)
		gpio_P_nRST.write(1)
		self.register = np.zeros(8)

	def run(self):
		while self.continue_run:
			time.sleep(1)  # delay maybe not needed
			with peripheral_requests_lock:
				print(
				    f"periph requests: {peripheral_requests}, HZ: {peripheral_requests_highZ}, RST: {peripheral_requests_reset}")
				if peripheral_requests_reset:
					self.reset()
					continue
				if peripheral_requests_highZ:
					self.output_highZ()
					continue
				for peripheral_name in self.bindings_iterable:
					x = peripheral_requests[peripheral_name]
					# print(f"periph: {peripheral_name} is {x}")
					self.add_element(x)
				self.send_output()


	def bw_on(self):
		# bw on 1, 2, 7, 8
		self.add_element(0) # 8
		self.add_element(0) # 7
		self.add_element(0) # 6
		self.add_element(0) # 5
		self.add_element(0) # 4
		self.add_element(0) # 3
		self.add_element(0) # 2
		self.add_element(1) # 1
		self.send_output()

	def bw_set1(self):
		self.add_element(0)
		self.add_element(0)
		self.add_element(0)
		self.add_element(0)
		self.add_element(0)
		self.add_element(0)
		self.add_element(0)
		self.add_element(0)
		self.add_element(1)
		self.send_output()
		time.sleep(3)
		self.reset()
		self.send_output()

	def bw_set2(self):
                self.add_element(0)
                self.add_element(0)
                self.add_element(0)
                self.add_element(0)
                self.add_element(0)
                self.add_element(0)
                self.add_element(0)
                self.add_element(1)
                self.add_element(1)
                self.send_output()
                time.sleep(2)
                self.reset()
                self.send_output()

	def write_peripheral(self, peripheral, val: int):
		if isinstance(peripheral, int):
			i = peripheral
		elif isinstance(peripheral, str):
			i = PERIPH_BINDINGS[peripheral]
		else:
			raise TypeError
		for x in range(8):
			if x == 7-i:
				self.add_element(val)
			else:
				self.add_element(self.output[7-x])

peripherals = PeripheralDriver()
# call peripheral run

# test
if __name__ == "__main__":
	while True:
		print("send 3ON = turn peripheral 3 on.")

		x = input()

		if("DOOR_SET1" in x):
			peripherals.bw_set1()
			continue

		if "DOOR_SET2" in x:
			peripherals.bw_set2()
			continue

		if("OFF" in x):
			peripherals.reset()
			peripherals.send_output()
			continue

		p = int(x[0])
		on = x[1:3] == "ON"
		print(on, p)
		peripherals.write_peripheral(p,on)


