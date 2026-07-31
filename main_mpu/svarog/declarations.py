import mraa
import time
import numpy as np
import threading
import socket
import queue

from BOARD_SELECT import is_ebox

SAT_TELEMETRY_PORT = 6000
SAT_COMMAND_PORT = 6001
SAT_IP = '192.168.78.3'

GS_IP = '172.16.18.190'
GS_TELEMETRY_PORT = 7000
GS_COMMAND_PORT = 7001

EBOX_IP = '172.16.18.191'
EBOX_TELEMETRY_PORT = 6000
EBOX_COMMAND_PORT = 6001

from dataclasses import dataclass

@dataclass
class ImageDeclarations:
    send_image: bool = False
    image_sleep_time: int = 10
    view_camera: int = 1

imageSocket: socket.socket
imageSocketPort: int = 15000
commandSocketStatus: bool = False
commandAdd: str = '10.104.81.192'
imgbuffer: int = 4096

THERMAL_LABELS = [
    "THERMAL_SENS_OUT_1", "THERMAL_SENS_OUT_2",
    "THERMAL_SENS_OUT_3", "THERMAL_SENS_OUT_4",
    "THERMAL_SENS_OUT_5", "THERMAL_SENS_OUT_6",
    "THERMAL_SENS_INT_1", "THERMAL_SENS_INT_2",
]

HEATER_SENSOR_PAIRS = {
    "HEAT_1": THERMAL_LABELS[0],
    "HEAT_2": THERMAL_LABELS[1],
    "HEAT_3": THERMAL_LABELS[2],
    "HEAT_4": THERMAL_LABELS[3],
} if is_ebox else {
    "HEAT_1": THERMAL_LABELS[0],
}

# PERIPH_BINDINGS is assigned below, after GPIO objects exist

peripheral_requests_reset = False
peripheral_requests_highZ = False
peripheral_requests_lock = threading.Lock()

DATA_WAIT_TIMEOUT = 5

SPI_INDEX = 3
SPI_FREQ = 4800000
SPI_LSBMODE = False

spi = None
try:
    spi = mraa.Spi(SPI_INDEX)
    spi.frequency(SPI_FREQ)
    spi.lsbmode(SPI_LSBMODE)
    spi.mode(0)
except Exception as e:
    print(f"[declarations] SPI init failed (bus {SPI_INDEX}): {e}")


I2C_BUS = "/dev/i2c-3"

LPS22HB_ADDR = 0x5C
MC6470_ACC_ADDR = 0x4C
MC6470_MAG_ADDR = 0x0C

LPS_PRESS_OUT_XL = 0x28
XOUT_EX_L = 0x0D

I2C_SDA = 3
I2C_SCL = 5
SPI_MOSI = 19
SPI_MISO = 21
SPI_SCLK = 23
PDU_SPI_CS = 24
THERMAL_SPI_CS = 26
ENCODER_SPI_CS = 28
UART_TX = 11
UART_RX = 13

EN_P1 = 29
EN_P2 = 15
EN_P3 = 31
EN_P4 = 18
EN_P5 = 12

FLT_P2 = 35
FLT_P3 = 33

PG_5 = 36
PG_9 = 38
PG_12 = 40

nBACKUP_EN = 32

gpio_EN_P1  = mraa.Gpio(EN_P1)
gpio_EN_P2  = mraa.Gpio(EN_P2)
gpio_EN_P3  = mraa.Gpio(EN_P3)
gpio_EN_P4  = mraa.Gpio(EN_P4)
gpio_EN_P5  = mraa.Gpio(EN_P5)

gpio_EN_P1.dir(mraa.DIR_OUT)
gpio_EN_P2.dir(mraa.DIR_OUT)
gpio_EN_P3.dir(mraa.DIR_OUT)
gpio_EN_P4.dir(mraa.DIR_OUT)
gpio_EN_P5.dir(mraa.DIR_OUT)

_PERIPH_SLOTS = [gpio_EN_P1, gpio_EN_P2, gpio_EN_P3, gpio_EN_P4, gpio_EN_P5]

if is_ebox:
    PERIPH_BINDINGS = {
        "HEAT_1": _PERIPH_SLOTS[0],
        "BW_1":   _PERIPH_SLOTS[1],
        "HEAT_2": _PERIPH_SLOTS[2],
        "HEAT_3": _PERIPH_SLOTS[3],
        "HEAT_4": _PERIPH_SLOTS[4],
    }
else:
    PERIPH_BINDINGS = {
        "BW_1":   _PERIPH_SLOTS[0],
        "BW_2":   _PERIPH_SLOTS[1],
        "BW_3":   _PERIPH_SLOTS[2],
        "BW_4":   _PERIPH_SLOTS[3],
        "HEAT_1": _PERIPH_SLOTS[4],
    }

peripheral_requests = {x : 0 for x in PERIPH_BINDINGS.keys()}

gpio_FLT_P2 = mraa.Gpio(FLT_P2)
gpio_FLT_P3 = mraa.Gpio(FLT_P3)

gpio_FLT_P2.dir(mraa.DIR_IN)
gpio_FLT_P3.dir(mraa.DIR_IN)

gpio_PG_5  = mraa.Gpio(PG_5)
gpio_PG_9  = mraa.Gpio(PG_9)
gpio_PG_12 = mraa.Gpio(PG_12)

gpio_PG_5.dir(mraa.DIR_IN)
gpio_PG_9.dir(mraa.DIR_IN)
gpio_PG_12.dir(mraa.DIR_IN)
