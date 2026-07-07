from declarations import *

def read_all():
    pg = {
        "PWR_GOOD_12": gpio_PWR_GOOD_12.read(),
        "PWR_GOOD_5":  gpio_PWR_GOOD_5.read(),
        "PWR_GOOD_9":  gpio_PWR_GOOD_9.read(),
    }
    flt = {
        "FLT_P1": gpio_FLT_P1.read(),
        "FLT_P2": gpio_FLT_P2.read(),
        "FLT_P3": gpio_FLT_P3.read(),
        "FLT_P4": gpio_FLT_P4.read(),
        "FLT_P5": gpio_FLT_P5.read(),
        "FLT_MOTCON": gpio_FLT_MOTCON.read(),
    }
    return pg, flt

if __name__ == "__main__":
    pg, flt = read_all()
    print("=== Power Good ===")
    for k, v in pg.items():
        print(f"  {k}: {'OK' if v else 'FAIL'}")
    print("=== Faults ===")
    for k, v in flt.items():
        print(f"  {k}: {'FAULT' if v else 'OK'}")
