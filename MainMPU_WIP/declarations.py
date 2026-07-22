import mraa
import time
import numpy as np
import threading

PERIPH_BINDINGS = {
    "BW_1" : 0,
    "BW_2" : 1,
    "BW_3" : 2,
    "BW_4" : 3,
    "HEAT_1" : 4,
    "HEAT_2" : 5,
    "HEAT_3" : 6,
    "HEAT_4" : 7
}

assert set(PERIPH_BINDINGS.values()) == set(range(8)) # all ports must have a binding. peripheral doesn't actually have to exist but they need to be bound.


# thread shared variable to submit requests for enable/disable of peripherals
peripheral_requests = {x : 0 for x in PERIPH_BINDINGS.keys()}
peripheral_requests_reset = False
peripheral_requests_highZ = False
peripheral_requests_lock = threading.Lock() # use this lock for the 3 variables above


DATA_WAIT_TIMEOUT = 5   

I2C_SDA = 3
I2C_SCL = 5
MPU1_EN = 11
MPU3_EN = 13
MPU4_EN = 15
SPI_M0 = 17
SPI_MOSI = 19
SPI_MISO = 21
SPI_SCLK = 23
P_LATCH_CLK = 27
P_nRST = 29
P_SCLK = 31
P_DIN = 33
P_OUT_EN = 35
UART_TX = 8
UART_RX = 10
MPU2_EN = 12
MOTCON_EFUSE_FLT = 18
PDU_SPI_CS = 24
THERMAL_SPI_CS = 26
PG_5 = 36
PG_9 = 38
PG_12 = 40

gpio_MPU1_EN        = mraa.Gpio(MPU1_EN)
gpio_MPU2_EN        = mraa.Gpio(MPU2_EN)
gpio_MPU3_EN        = mraa.Gpio(MPU3_EN)
gpio_MPU4_EN        = mraa.Gpio(MPU4_EN)

gpio_P_LATCH_CLK    = mraa.Gpio(P_LATCH_CLK)
gpio_P_nRST         = mraa.Gpio(P_nRST)
gpio_P_SCLK         = mraa.Gpio(P_SCLK)
gpio_P_DIN          = mraa.Gpio(P_DIN)
gpio_P_OUT_EN       = mraa.Gpio(P_OUT_EN)

gpio_MPU1_EN.dir(mraa.DIR_OUT)
gpio_MPU2_EN.dir(mraa.DIR_OUT)
gpio_MPU3_EN.dir(mraa.DIR_OUT)
gpio_MPU4_EN.dir(mraa.DIR_OUT)

gpio_P_LATCH_CLK.dir(mraa.DIR_OUT)
gpio_P_nRST.dir(mraa.DIR_OUT)
gpio_P_SCLK.dir(mraa.DIR_OUT)
gpio_P_DIN.dir(mraa.DIR_OUT)
gpio_P_OUT_EN.dir(mraa.DIR_OUT)

gpio_MOTCON_EFUSE_FLT   = mraa.Gpio(MOTCON_EFUSE_FLT)
gpio_PG_5               = mraa.Gpio(PG_5)
gpio_PG_9               = mraa.Gpio(PG_9)
gpio_PG_12              = mraa.Gpio(PG_12)

gpio_MOTCON_EFUSE_FLT.dir(mraa.DIR_IN)
gpio_PG_5.dir(mraa.DIR_IN)
gpio_PG_9.dir(mraa.DIR_IN)
gpio_PG_12.dir(mraa.DIR_IN)    