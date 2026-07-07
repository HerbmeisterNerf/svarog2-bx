import mraa
import time
import numpy as np
import threading
import socket
import queue

EBOX_BOARD = True

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

if EBOX_BOARD:
    PERIPH_BINDINGS = {
        "HEAT_1": 0,
        "HEAT_2": 1,
        "HEAT_3": 2,
        "HEAT_4": 3,
        "BW_1":   4,
    }

    HEATER_SENSOR_PAIRS = {
        "HEAT_1": 0,
        "HEAT_2": 1,
        "HEAT_3": 2,
        "HEAT_4": 3,
    }

if not EBOX_BOARD:
    PERIPH_BINDINGS = {
        "BW_1":   0,
        "BW_2":   1,
        "BW_3":   2,
        "BW_4":   3,
        "HEAT_1": 4,
    }

    HEATER_SENSOR_PAIRS = {
        "HEAT_1": 4,
    }

assert set(PERIPH_BINDINGS.values()) == set(range(5))

peripheral_requests = {x : 0 for x in PERIPH_BINDINGS.keys()}
peripheral_requests_reset = False
peripheral_requests_highZ = False
peripheral_requests_lock = threading.Lock()

DATA_WAIT_TIMEOUT = 5

I2C_SDA = 3
I2C_SCL = 5
SPI_MOSI = 19
SPI_MISO = 21
SPI_SCLK = 23
PDU_SPI_CS = 24
THERMAL_SPI_CS = 26
UART_TX = 8
UART_RX = 10

EN_P1 = 15
EN_P2 = 11
EN_P3 = 7
EN_P4 = 16
EN_P5 = 12
EN_MOTCON = 13

FLT_P1 = 29
FLT_P2 = 31
FLT_P3 = 32
FLT_P4 = 33
FLT_P5 = 35
FLT_MOTCON = 36

PWR_GOOD_12 = 22
PWR_GOOD_5 = 37
PWR_GOOD_9 = 38

gpio_EN_P1  = mraa.Gpio(EN_P1)
gpio_EN_P2  = mraa.Gpio(EN_P2)
gpio_EN_P3  = mraa.Gpio(EN_P3)
gpio_EN_P4  = mraa.Gpio(EN_P4)
gpio_EN_P5  = mraa.Gpio(EN_P5)
gpio_EN_MOTCON = mraa.Gpio(EN_MOTCON)

gpio_EN_P1.dir(mraa.DIR_OUT)
gpio_EN_P2.dir(mraa.DIR_OUT)
gpio_EN_P3.dir(mraa.DIR_OUT)
gpio_EN_P4.dir(mraa.DIR_OUT)
gpio_EN_P5.dir(mraa.DIR_OUT)
gpio_EN_MOTCON.dir(mraa.DIR_OUT)

gpio_FLT_P1 = mraa.Gpio(FLT_P1)
gpio_FLT_P2 = mraa.Gpio(FLT_P2)
gpio_FLT_P3 = mraa.Gpio(FLT_P3)
gpio_FLT_P4 = mraa.Gpio(FLT_P4)
gpio_FLT_P5 = mraa.Gpio(FLT_P5)
gpio_FLT_MOTCON = mraa.Gpio(FLT_MOTCON)

gpio_FLT_P1.dir(mraa.DIR_IN)
gpio_FLT_P2.dir(mraa.DIR_IN)
gpio_FLT_P3.dir(mraa.DIR_IN)
gpio_FLT_P4.dir(mraa.DIR_IN)
gpio_FLT_P5.dir(mraa.DIR_IN)
gpio_FLT_MOTCON.dir(mraa.DIR_IN)

gpio_PWR_GOOD_12 = mraa.Gpio(PWR_GOOD_12)
gpio_PWR_GOOD_5  = mraa.Gpio(PWR_GOOD_5)
gpio_PWR_GOOD_9  = mraa.Gpio(PWR_GOOD_9)

gpio_PWR_GOOD_12.dir(mraa.DIR_IN)
gpio_PWR_GOOD_5.dir(mraa.DIR_IN)
gpio_PWR_GOOD_9.dir(mraa.DIR_IN)
