from EstBasic import *
from EstDerived import *
from EstBasic import _LIB_INV_AREA, _LIB_WIRE_AREA, _fx_live_bits, _fx_pad_bits, _predict
from EstDerived import _bundle

def Est_Neg(ModelNeg, DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False):
    params = _bundle(ModelNeg, ("logic_model", "features"), "Est_Neg")
    d_in, f_in = int(DWT_IN), int(FRAC_IN)
    d_out, f_out, s_out = int(DWT_OUT), int(FRAC_OUT), int(bool(SIGN_OUT))
    n_clk = int(N_CLK)

    width = d_in + 1
    live = _fx_live_bits(width, f_in, 1, d_out, f_out, s_out)
    lsb_pad, _msb_pad = _fx_pad_bits(width, f_in, 1, d_out, f_out, s_out)
    disp_neg = max(0, f_in - f_out)
    available = {"one": 1.0, "live": live, "w": width, "d_in": d_in, "d_out": d_out, "disp_neg": disp_neg, "u3": min(width, live + disp_neg + 1)}
    features = [available[name] for name in params["features"]]
    logic = max(0.0, _predict(params["logic_model"], features))

    return (logic + _LIB_INV_AREA * lsb_pad
            + _LIB_WIRE_AREA * live
            + Est_Delay(live, n_clk, IF_RST_N))
