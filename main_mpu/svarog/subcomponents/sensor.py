import declarations as d

def scan():
    i2c = d.mraa.I2c(d.I2C_BUS)
    print("Scanning I2C bus...")
    for addr in range(0x08, 0x78):
        i2c.address(addr)
        try:
            i2c.readReg(0x00)
            print(f"  Found device at 0x{addr:02X}")
        except:
            pass

def read_pressure():
    i2c = d.mraa.I2c(d.I2C_BUS)
    i2c.address(d.LPS22HB_ADDR)
    data = i2c.readBytesReg(d.LPS_PRESS_OUT_XL, 3)
    raw = data[2] << 16 | data[1] << 8 | data[0]
    if raw & 0x800000:
        raw -= 1 << 24
    return raw / 4096.0

def read_accel():
    i2c = d.mraa.I2c(d.I2C_BUS)
    i2c.address(d.MC6470_ACC_ADDR)
    data = i2c.readBytesReg(d.XOUT_EX_L, 6)
    def to_signed(v):
        return v - (1 << 16) if v & 0x8000 else v
    x = to_signed(data[1] << 8 | data[0])
    y = to_signed(data[3] << 8 | data[2])
    z = to_signed(data[5] << 8 | data[4])
    return x / 512.0, y / 512.0, z / 512.0
