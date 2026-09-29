from EstBasic import *
from EstDerived import *
from EstBasic import _predict
from EstDerived import _bundle, _comptree_assembly, _comptree_structure

def Est_CompTree(ModelCompTree, ModelComp, DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE="A", IF_RST_N=False, IF_GIDX=False, IF_LIDX=False, IF_GVAL=False, IF_LVAL=False):
    params = _bundle(ModelCompTree, ("scale_model", "features"), "Est_CompTree")
    info = _comptree_structure(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE, IF_RST_N, IF_GIDX, IF_LIDX, IF_GVAL, IF_LVAL)
    assembly = _comptree_assembly(info, ModelComp)
    scale = _predict(params["scale_model"], [info[name] for name in params["features"]])
    return assembly * min(2.0, max(0.3, scale))
