from EstBasic import *
from EstDerived import *
from EstBasic import _LIB_INV_AREA, _fx_is_constant, _fx_live_bits

def Est_SxMatch(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, SHIFT, N_CLK=0, IF_RST_N=False):
    d_in, f_in, s_in = int(DWT_IN), int(FRAC_IN), int(bool(SIGN_IN))
    d_out, f_out, s_out = int(DWT_OUT), int(FRAC_OUT), int(bool(SIGN_OUT))
    frac_match = f_out + int(SHIFT)
    if _fx_is_constant(d_in, f_in, s_in, d_out, frac_match, s_out):
        return _LIB_INV_AREA * d_out
    live = _fx_live_bits(d_in, f_in, s_in, d_out, frac_match, s_out)
    return Est_FxMatch(d_in, f_in, s_in, d_out, frac_match, s_out, 0, False) + Est_Delay(live, int(N_CLK), IF_RST_N)
