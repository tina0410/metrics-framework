from EstBasic import *
from EstDerived import *
from EstBasic import _LIB_FF_AREA, _LIB_FF_AREA_RST, _LIB_WIRE_AREA

def Est_Delay(DWT, CLK, IS_RST_N):
    if CLK == 0:
        return _LIB_WIRE_AREA * DWT
    if isinstance(IS_RST_N, bool):
        multiplier = _LIB_FF_AREA_RST if IS_RST_N else _LIB_FF_AREA
        return multiplier * DWT * CLK
    y_pred = 0
    for rst_flag in IS_RST_N:
        multiplier = _LIB_FF_AREA_RST if rst_flag else _LIB_FF_AREA
        y_pred += multiplier * DWT
    return y_pred
