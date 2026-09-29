from EstBasic import *
from EstDerived import *
from EstDerived import _addertree_layer, _addertree_layers, _bundle

def Est_AdderTree(ModelAdderTree, ModelAdd, DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE="A", IF_RST_N=False):
    params = _bundle(ModelAdderTree, ("trim_span",), "Est_AdderTree")
    layers, pipelines, resets = _addertree_layers(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE, IF_RST_N)
    total = 0.0
    n_operators = int(N_INPUTS)
    for index in range(len(pipelines)):
        n_remainder = n_operators % 2
        n_adders = n_operators // 2
        n_operators = n_adders + n_remainder
        full, cut, blend, rem_full, rem_cut = _addertree_layer(params, ModelAdd, layers[index], layers[index + 1], pipelines[index], resets[index], DWT_OUT, FRAC_OUT)
        total += n_adders * (full + blend * (cut - full))
        if n_remainder == 1:
            total += rem_full + blend * (rem_cut - rem_full)
    return total
