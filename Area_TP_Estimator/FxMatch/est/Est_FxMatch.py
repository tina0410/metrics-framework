from EstBasic import *
from EstDerived import *
from EstBasic import _LIB_FF_AREA, _LIB_FF_AREA_RST, _LIB_INV_AREA, _LIB_WIRE_AREA, _fx_is_constant, _fx_live_bits, _fx_pad_bits

def Est_FxMatch(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False):
    DWT_IN = int(DWT_IN)
    FRAC_IN = int(FRAC_IN)
    SIGN_IN = int(SIGN_IN)
    DWT_OUT = int(DWT_OUT)
    FRAC_OUT = int(FRAC_OUT)
    SIGN_OUT = int(SIGN_OUT)
    N_CLK = int(N_CLK)

    if _fx_is_constant(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT):
        return _LIB_INV_AREA * DWT_OUT

    w_eff = _fx_live_bits(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT)
    if N_CLK > 0:
        if isinstance(IF_RST_N, bool):
            y_pred = (_LIB_FF_AREA_RST if IF_RST_N else _LIB_FF_AREA) * w_eff * N_CLK
        else:
            y_pred = w_eff * sum(_LIB_FF_AREA_RST if flag else _LIB_FF_AREA
                                 for flag in IF_RST_N[:N_CLK])
    else:
        y_pred = _LIB_WIRE_AREA * w_eff

    lsb_pad, msb_pad = _fx_pad_bits(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT)
    cells = lsb_pad + (0 if SIGN_IN else msb_pad)
    if SIGN_IN == 0 and SIGN_OUT == 1 and (msb_pad > 0 or (N_CLK == 0 and lsb_pad > 0)):
        cells += 1
    y_pred += _LIB_INV_AREA * cells
    return y_pred
