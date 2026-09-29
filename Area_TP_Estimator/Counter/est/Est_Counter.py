from EstBasic import *
from EstDerived import *
from EstBasic import _LIB_FF_AREA, _LIB_FF_AREA_EN, _LIB_FF_AREA_RST, _LIB_INV_AREA, _predict
from EstDerived import _bundle

def Est_Counter(ModelCounter, DWT, STEP, IF_RST_N, HAS_CLEAR, HAS_WRAP):
    params = _bundle(ModelCounter, ("model", "features"), "Est_Counter")
    dwt, step = int(DWT), int(STEP)
    rst, clr, wrap = int(bool(IF_RST_N)), int(bool(HAS_CLEAR)), int(bool(HAS_WRAP))
    trim = min(dwt, max(0, (step & -step).bit_length() - 1))
    wrapbit = wrap * clr
    if step % (1 << dwt) == 0:
        if rst or clr:
            return dwt * _LIB_INV_AREA + wrapbit * (_LIB_FF_AREA_RST if rst else _LIB_FF_AREA)
        return dwt * _LIB_FF_AREA + _LIB_INV_AREA * (1 if wrap else 0)
    count_bits = (dwt - trim) if rst else dwt
    ff_table = count_bits * (_LIB_FF_AREA_RST if rst else _LIB_FF_AREA_EN) + wrapbit * (_LIB_FF_AREA_RST if rst else _LIB_FF_AREA)
    available = {"one": 1.0, "inc": dwt - trim, "mux_rst": rst * dwt, "mux_norst": (1 - rst) * dwt, "dwt": dwt, "trim": trim, "clr": clr, "wrap": wrap}
    residual = max(0.0, _predict(params["model"], [available[name] for name in params["features"]]))
    return ff_table + residual
