from EstBasic import *
from EstDerived import *
from EstBasic import _LIB_INV_AREA
from EstDerived import _bundle

def Est_CNorm(ModelCNorm, ModelAbs, ModelAdd, DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False):
    params = _bundle(ModelCNorm, ("trim_lo", "trim_hi"), "Est_CNorm")
    d_in, f_in, s_in = int(DWT_IN), int(FRAC_IN), int(bool(SIGN_IN))
    d_out, f_out = int(DWT_OUT), int(FRAC_OUT)
    u2 = min(d_in, d_out - f_out + f_in)
    width = max(f_in + 1, min(d_in, u2))
    blend = min(1.0, max(0.0, (params["trim_hi"] - u2 / float(d_in)) / (params["trim_hi"] - params["trim_lo"])))
    full = Est_Abs(ModelAbs, d_in, f_in, s_in, d_in, f_in, 0, 0, False)
    cut = Est_Abs(ModelAbs, width, f_in, s_in, width, f_in, 0, 0, False) if width != d_in else full
    lane = full - blend * (full - cut)
    add = Est_ADD(ModelAdd, d_in, f_in, 0, d_in, f_in, 0, d_out, f_out, N_CLK, IF_RST_N)
    pad_lsb = max(0, f_out - f_in)
    pad_msb = max(0, d_out - f_out - (d_in - f_in + 1))
    return 2.0 * lane + add + _LIB_INV_AREA * (pad_lsb + pad_msb)
