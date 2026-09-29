from EstBasic import *
from EstDerived import *
from EstBasic import _LIB_INV_AREA, _fx_pad_bits

def Est_CSub(ModelSub, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False):
    lane = Est_SUB(ModelSub, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, N_CLK, IF_RST_N)
    diff_frac = max(int(FRAC_IN_1), int(FRAC_IN_2))
    diff_width = max(int(DWT_IN_1) - int(FRAC_IN_1), int(DWT_IN_2) + 1 - int(FRAC_IN_2)) + 1 + diff_frac
    lsb_pad, _msb_pad = _fx_pad_bits(diff_width, diff_frac, 1, int(DWT_OUT), int(FRAC_OUT), int(SIGN_OUT))
    return 2.0 * lane + 2.0 * _LIB_INV_AREA * lsb_pad
