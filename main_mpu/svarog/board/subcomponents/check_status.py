import declarations as d

def read_all():
    pg = {
        "PG_5":  d.gpio_PG_5.read(),
        "PG_9":  d.gpio_PG_9.read(),
        "PG_12": d.gpio_PG_12.read(),
    }
    flt = {
        "FLT_P2": d.gpio_FLT_P2.read(),
        "FLT_P3": d.gpio_FLT_P3.read(),
    }
    return pg, flt

def read_en():
    return {name: gpio.read() for name, gpio in d.PERIPH_BINDINGS.items()}
