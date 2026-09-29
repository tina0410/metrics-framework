from EstBasic import *
from EstDerived import *
from EstBasic import _LIB_INV_AREA, _fx_pad_bits

def Est_CAdd(ModelAdd, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False):
    lane = Est_ADD(ModelAdd, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, N_CLK, IF_RST_N)
    sum_frac = max(int(FRAC_IN_1), int(FRAC_IN_2))
    sum_width = max(int(DWT_IN_1) - int(FRAC_IN_1), int(DWT_IN_2) - int(FRAC_IN_2)) + 1 + sum_frac
    sign_sum = int(bool(SIGN_IN_1 or SIGN_IN_2))
    lsb_pad, msb_pad = _fx_pad_bits(sum_width, sum_frac, sign_sum, int(DWT_OUT), int(FRAC_OUT), int(SIGN_OUT))
    cells = lsb_pad + (0 if sign_sum else msb_pad)
    if sign_sum == 0 and int(SIGN_OUT) == 1 and (msb_pad > 0 or lsb_pad > 0):
        cells += 1
    return 2.0 * lane + 2.0 * _LIB_INV_AREA * cells
