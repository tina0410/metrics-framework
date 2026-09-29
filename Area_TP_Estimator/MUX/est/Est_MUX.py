from EstBasic import *
from EstDerived import *
from EstDerived import _bundle

def Est_MUX(ModelMUX, N_INPUTS, DWT):
    params = _bundle(ModelMUX, ("table", "fallback"), "Est_MUX")
    n, dwt = int(N_INPUTS), int(DWT)
    sel = max(1, (n - 1).bit_length())
    table = params["table"]
    if n in table:
        a, b = table[n]
    else:
        coef_a = params["fallback"]["a_coef"]
        coef_b = params["fallback"]["b_coef"]
        a = coef_a[0] * n + coef_a[1] * sel + coef_a[2]
        b = coef_b[0] * n + coef_b[1] * sel + coef_b[2]
    return max(0.0, a * dwt + b)
