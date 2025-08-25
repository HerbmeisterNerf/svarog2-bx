import numpy as np

from declarations import (
	gpio_P_LATCH_CLK,
	gpio_P_nRST,
	gpio_P_SCLK,
	gpio_P_DIN,
	gpio_P_OUT_EN
)


class PeripheralDriver:
	'''
	Singleton. Do not make any new instances. Use instance `peripherals`.
	Manages reading and writing to peripherals via the MC74HC595A shift register.
	'''
	def __init__(self, bindings=None) -> None:
		gpio_P_nRST.write(1)
		gpio_P_OUT_EN.write(0)
		self.output  = np.zeros(8) # keeps track of values on output
		self.register = np.zeros(8) # keeps track of value in register
		if bindings is None:
			self.bindings = {  # change this to be specific
				"P_1": 0,
				"P_2": 1,
				"P_3": 2,
				"P_4": 3,
				"P_5": 4,
				"P_6": 5,
				"P_7": 6,
				"P_8": 7
			}
		else:
			self.bindings = bindings

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
		gpio_P_nRST.write(0)
		gpio_P_nRST.write(1)
		self.register[:] = 0


	def write_peripheral(self, peripheral: str | int, val: int):
		if isinstance(peripheral, int):
			i = peripheral
		elif isinstance(peripheral, str):
			i = self.bindings[peripheral]
		else:
			raise TypeError
		for x in range(8):
			if x == i:
				self.add_element(val)
			else:
				self.add_element(self.output[8-x])

peripherals = PeripheralDriver()