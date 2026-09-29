from EstBasic import *
from EstDerived import *
from EstBasic import _LIB_INV_AREA, _LIB_WIRE_AREA, _fx_live_bits, _fx_pad_bits, _predict
from EstDerived import _bundle

def Est_Abs(ModelAbs, DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False):
    params = _bundle(ModelAbs, ("logic_model", "features"), "Est_Abs")
    d_in, f_in, s_in = int(DWT_IN), int(FRAC_IN), int(bool(SIGN_IN))
    d_out, f_out, s_out = int(DWT_OUT), int(FRAC_OUT), int(bool(SIGN_OUT))
    n_clk = int(N_CLK)

    live = _fx_live_bits(d_in, f_in, 0, d_out, f_out, s_out)
    lsb_pad, msb_pad = _fx_pad_bits(d_in, f_in, 0, d_out, f_out, s_out)
    cells = lsb_pad + msb_pad
    if s_out == 1 and (lsb_pad > 0 or msb_pad > 0):
        cells += 1

    disp_neg = max(0, f_in - f_out)
    u3 = min(d_in, live + disp_neg + 1)
    available = {"sin": s_in, "s_d_in": s_in * d_in, "s_live": s_in * live, "s_f_out": s_in * f_out, "s_u3": s_in * u3, "s_disp_neg": s_in * disp_neg}
    features = [available[name] for name in params["features"]]
    logic = max(0.0, _predict(params["logic_model"], features))

    return (logic + _LIB_INV_AREA * cells
            + _LIB_WIRE_AREA * live
            + Est_Delay(live, n_clk, IF_RST_N))
