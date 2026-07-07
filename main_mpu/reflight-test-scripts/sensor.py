from declarations import *

I2C_BUS = 3

i2c = mraa.I2c(I2C_BUS)

LPS22HB_ADDR = 0x5C
MC6470_ACC_ADDR = 0x4C
MC6470_MAG_ADDR = 0x0C

LPS_PRESS_OUT_XL = 0x28
XOUT_EX_L = 0x0D

def scan():
    print("Scanning I2C bus...")
    for addr in range(0x08, 0x78):
        i2c.address(addr)
        try:
            i2c.readReg(0x00)
            print(f"  Found device at 0x{addr:02X}")
        except:
            pass

def read_pressure():
    i2c.address(LPS22HB_ADDR)
    data = i2c.readBytesReg(LPS_PRESS_OUT_XL, 3)
    raw = data[2] << 16 | data[1] << 8 | data[0]
    if raw & 0x800000:
        raw -= 1 << 24
    return raw / 4096.0

def read_accel():
    i2c.address(MC6470_ACC_ADDR)
    data = i2c.readBytesReg(XOUT_EX_L, 6)
    def to_signed(v):
        return v - (1 << 16) if v & 0x8000 else v
    x = to_signed(data[1] << 8 | data[0])
    y = to_signed(data[3] << 8 | data[2])
    z = to_signed(data[5] << 8 | data[4])
    return x / 512.0, y / 512.0, z / 512.0

if __name__ == "__main__":
    scan()
    try:
        press = read_pressure()
        print(f"Pressure: {press:.2f} hPa")
    except:
        print("No LPS22HB pressure sensor found")
    try:
        ax, ay, az = read_accel()
        print(f"Accel: X={ax:.2f}  Y={ay:.2f}  Z={az:.2f} g")
    except:
        print("No MC6470 accelerometer found")
