from EstBasic import *
from EstDerived import *
from EstBasic import _predict
from EstDerived import _bundle, _comp_structure

def Est_Comp(ModelComp, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False, IF_GIDX=False, IF_LIDX=False, IF_EIDX=False, IF_GVAL=False, IF_LVAL=False):
    params = _bundle(ModelComp, ("logic_model", "features"), "Est_Comp")
    info = _comp_structure(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK, IF_RST_N, IF_GIDX, IF_LIDX, IF_EIDX, IF_GVAL, IF_LVAL)
    logic = max(0.0, _predict(params["logic_model"], [info[name] for name in params["features"]]))
    return info["delay"] + info["fx_value"] + logic
