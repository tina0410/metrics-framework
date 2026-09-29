from EstBasic import *
from EstDerived import *
from EstBasic import _predict
from EstDerived import _bundle, _cmul_structure

def Est_CMul(ModelCMul, ModelMul, ModelAdd, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False, METHOD="4mul"):
    params = _bundle(ModelCMul, ("lane_model", "features"), "Est_CMul")
    info = _cmul_structure(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK, IF_RST_N, METHOD)
    mul_area = sum(Est_MUL(ModelMul, *operand) for operand in info["mul_ops"])
    add_area = sum(Est_ADD(ModelAdd, *operand) for operand in info["pre_add_ops"])
    fx_area = info["fx_count"] * Est_FxMatch(*info["fx_ops"])
    lane = _predict(params["lane_model"], [info[name] for name in params["features"]])
    return mul_area + add_area + fx_area + lane
