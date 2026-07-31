from declarations import *

def read_all():
    pg = {
        "PG_5":  gpio_PG_5.read(),
        "PG_9":  gpio_PG_9.read(),
        "PG_12": gpio_PG_12.read(),
    }
    flt = {
        "FLT_P2": gpio_FLT_P2.read(),
        "FLT_P3": gpio_FLT_P3.read(),
        "FLT_P4": gpio_FLT_P4.read(),
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
