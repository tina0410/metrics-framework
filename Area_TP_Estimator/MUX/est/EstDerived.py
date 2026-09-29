import math

import numpy as np

from EstBasic import Est_ADD, Est_Delay, Est_FxMatch, Est_MUL, Est_SUB, _fx_is_constant, _fx_live_bits, _fx_pad_bits, _predict, _LIB_FF_AREA, _LIB_FF_AREA_EN, _LIB_FF_AREA_RST, _LIB_INV_AREA, _LIB_WIRE_AREA


def _bundle(Model, required, module):
    if isinstance(Model, dict) and all(key in Model for key in required):
        return Model
    raise TypeError("{} 的 Model 参数需要 Est/model/ 下对应的参数包 (缺少 {}), 请先跑 tools/fit_{}_area_model.py 标定。".format(module, "/".join(key for key in required if not (isinstance(Model, dict) and key in Model)), module.lower()))


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


def Est_SxMatch(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, SHIFT, N_CLK=0, IF_RST_N=False):
    d_in, f_in, s_in = int(DWT_IN), int(FRAC_IN), int(bool(SIGN_IN))
    d_out, f_out, s_out = int(DWT_OUT), int(FRAC_OUT), int(bool(SIGN_OUT))
    frac_match = f_out + int(SHIFT)
    if _fx_is_constant(d_in, f_in, s_in, d_out, frac_match, s_out):
        return _LIB_INV_AREA * d_out
    live = _fx_live_bits(d_in, f_in, s_in, d_out, frac_match, s_out)
    return Est_FxMatch(d_in, f_in, s_in, d_out, frac_match, s_out, 0, False) + Est_Delay(live, int(N_CLK), IF_RST_N)


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


def Est_CSub(ModelSub, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False):
    lane = Est_SUB(ModelSub, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, N_CLK, IF_RST_N)
    diff_frac = max(int(FRAC_IN_1), int(FRAC_IN_2))
    diff_width = max(int(DWT_IN_1) - int(FRAC_IN_1), int(DWT_IN_2) + 1 - int(FRAC_IN_2)) + 1 + diff_frac
    lsb_pad, _msb_pad = _fx_pad_bits(diff_width, diff_frac, 1, int(DWT_OUT), int(FRAC_OUT), int(SIGN_OUT))
    return 2.0 * lane + 2.0 * _LIB_INV_AREA * lsb_pad


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


def Est_Counter(ModelCounter, DWT, STEP, IF_RST_N, HAS_CLEAR, HAS_WRAP):
    params = _bundle(ModelCounter, ("model", "features"), "Est_Counter")
    dwt, step = int(DWT), int(STEP)
    rst, clr, wrap = int(bool(IF_RST_N)), int(bool(HAS_CLEAR)), int(bool(HAS_WRAP))
    trim = min(dwt, max(0, (step & -step).bit_length() - 1))
    wrapbit = wrap * clr
    if step % (1 << dwt) == 0:
        if rst or clr:
            return dwt * _LIB_INV_AREA + wrapbit * (_LIB_FF_AREA_RST if rst else _LIB_FF_AREA)
        return dwt * _LIB_FF_AREA + _LIB_INV_AREA * (1 if wrap else 0)
    count_bits = (dwt - trim) if rst else dwt
    ff_table = count_bits * (_LIB_FF_AREA_RST if rst else _LIB_FF_AREA_EN) + wrapbit * (_LIB_FF_AREA_RST if rst else _LIB_FF_AREA)
    available = {"one": 1.0, "inc": dwt - trim, "mux_rst": rst * dwt, "mux_norst": (1 - rst) * dwt, "dwt": dwt, "trim": trim, "clr": clr, "wrap": wrap}
    residual = max(0.0, _predict(params["model"], [available[name] for name in params["features"]]))
    return ff_table + residual


def _comp_aligned_range(DWT, FRAC, SIGN, FRAC_C):
    lo, hi = (-(1 << (int(DWT) - 1)), (1 << (int(DWT) - 1)) - 1) if int(SIGN) else (0, (1 << int(DWT)) - 1)
    return (lo >> (int(FRAC) - int(FRAC_C)), hi >> (int(FRAC) - int(FRAC_C))) if int(FRAC) >= int(FRAC_C) else (lo << (int(FRAC_C) - int(FRAC)), hi << (int(FRAC_C) - int(FRAC)))


def _comp_range_bits(lo, hi):
    return max(1, int(max(abs(int(lo)) - 1, int(hi))).bit_length() + 1) if int(lo) < 0 else max(1, int(hi).bit_length())


def _comp_value_bits(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, FRAC_C):
    lo1, hi1 = _comp_aligned_range(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, FRAC_C)
    lo2, hi2 = _comp_aligned_range(DWT_IN_2, FRAC_IN_2, SIGN_IN_2, FRAC_C)
    lo, hi = min(lo1, lo2), max(hi1, hi2)
    shift = int(FRAC_C) - int(FRAC_OUT)
    qlo, qhi = (lo >> shift, hi >> shift) if shift > 0 else ((lo << (-shift), hi << (-shift)) if shift < 0 else (lo, hi))
    modulus = 1 << (int(DWT_OUT) + (0 if int(SIGN_OUT) else 1))
    mask, half = modulus - 1, modulus >> 1
    if (qhi - qlo) >= mask:
        olo, ohi = (-half, half - 1) if int(SIGN_OUT) else (0, (1 << int(DWT_OUT)) - 1)
    else:
        wlo, whi = qlo & mask, qhi & mask
        wlo, whi = (wlo - modulus if wlo >= half else wlo), (whi - modulus if whi >= half else whi)
        olo, ohi = (wlo, whi) if wlo <= whi else (whi, wlo)
    pad = max(0, int(FRAC_OUT) - int(FRAC_C))
    live = (int(ohi).bit_length() - pad) if olo >= 0 else (int(DWT_OUT) - pad)
    return max(1, min(int(DWT_OUT), live))


def _comp_structure(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK, IF_RST_N, IF_GIDX, IF_LIDX, IF_EIDX, IF_GVAL, IF_LVAL):
    d1, f1, s1 = int(DWT_IN_1), int(FRAC_IN_1), int(bool(SIGN_IN_1))
    d2, f2, s2 = int(DWT_IN_2), int(FRAC_IN_2), int(bool(SIGN_IN_2))
    frac_c = max(f1, f2)
    cw = max(d1 + (1 - s1) - f1, d2 + (1 - s2) - f2) + frac_c
    a1 = _comp_range_bits(*_comp_aligned_range(d1, f1, s1, frac_c))
    a2 = _comp_range_bits(*_comp_aligned_range(d2, f2, s2, frac_c))
    live = _comp_value_bits(d1, f1, s1, d2, f2, s2, int(DWT_OUT), int(FRAC_OUT), int(SIGN_OUT), frac_c)
    drop = max(0, frac_c - int(FRAC_OUT))
    n_flag = int(bool(IF_GIDX)) + int(bool(IF_LIDX)) + int(bool(IF_EIDX))
    n_value = int(bool(IF_GVAL)) + int(bool(IF_LVAL))
    n_test = min(3, int(bool(IF_GIDX) or bool(IF_GVAL)) + int(bool(IF_LIDX) or bool(IF_LVAL)) + int(bool(IF_EIDX)))
    align_max, align_min = max(a1, a2), min(a1, a2)
    out_pad = max(0, int(DWT_OUT) - cw)
    sign_ext = int(bool(SIGN_IN_1)) * max(0, cw - a1) + int(bool(SIGN_IN_2)) * max(0, cw - a2)
    delay = n_flag * Est_Delay(1, N_CLK, IF_RST_N) + n_value * Est_Delay(live, N_CLK, IF_RST_N)
    return {"cw": cw, "frac": frac_c, "drop": drop, "align_1": a1, "align_2": a2, "live_out": live,
            "n_flag": n_flag, "n_value": n_value, "n_test": n_test, "delay": delay,
            "fx_value": _LIB_WIRE_AREA * n_value * live,
            "sign_in_1": s1, "sign_in_2": s2, "sign_out": int(bool(SIGN_OUT)), "in2_dwt": d2,
            "value_amin": n_value * align_min, "test_amin": n_test * align_min, "test_align_1": n_test * a1,
            "test_align_max": n_test * align_max, "test_d1": n_test * d1,
            "value_drop": n_value * drop, "value_do": n_value * int(DWT_OUT), "value_frac_1": n_value * f1,
            "out_pad": out_pad, "frac_1": f1, "sign_ext": sign_ext, "value_sign_ext": n_value * sign_ext}


def Est_Comp(ModelComp, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False, IF_GIDX=False, IF_LIDX=False, IF_EIDX=False, IF_GVAL=False, IF_LVAL=False):
    params = _bundle(ModelComp, ("logic_model", "features"), "Est_Comp")
    info = _comp_structure(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK, IF_RST_N, IF_GIDX, IF_LIDX, IF_EIDX, IF_GVAL, IF_LVAL)
    logic = max(0.0, _predict(params["logic_model"], [info[name] for name in params["features"]]))
    return info["delay"] + info["fx_value"] + logic


def _cmul_structure(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK, IF_RST_N, METHOD):
    d1, f1, s1 = int(DWT_IN_1), int(FRAC_IN_1), int(bool(SIGN_IN_1))
    d2, f2, s2 = int(DWT_IN_2), int(FRAC_IN_2), int(bool(SIGN_IN_2))
    do, fo, so = int(DWT_OUT), int(FRAC_OUT), int(bool(SIGN_OUT))
    three = 1 if str(METHOD) == "3mul" else 0
    ops = 3 if three else 2
    w1, w2 = d1 + (1 - s1), d2 + (1 - s2)
    work_d, work_f = w1 + w2 + 3, f1 + f2
    pre_1_d, pre_2_d = w1 + 1, w2 + 1
    mul_ops = [(d1, f1, s1, d2, f2, s2, work_d, work_f)] * (2 if three else 4)
    if three:
        mul_ops.append((pre_1_d, f1, 1, pre_2_d, f2, 1, work_d, work_f))
        pre_add_ops = [(d1, f1, s1, d1, f1, s1, pre_1_d, f1), (d2, f2, s2, d2, f2, s2, pre_2_d, f2)]
    else:
        pre_add_ops = []
    live = _fx_live_bits(work_d, work_f, 1, do, fo, so)
    return {"work_dwt": work_d, "work_frac": work_f, "pre_1_dwt": pre_1_d, "pre_2_dwt": pre_2_d,
            "n_mul": len(mul_ops), "n_pre_add": len(pre_add_ops), "ops": ops,
            "mul_ops": mul_ops, "pre_add_ops": pre_add_ops,
            "fx_count": 2, "fx_ops": (work_d, work_f, 1, do, fo, so, int(N_CLK), IF_RST_N),
            "one": 1.0, "lane_dwt": float(work_d), "lane_dwt_ops": float(work_d * (3 if three else 2)),
            "method4": float(1 - three), "sign_out": float(so), "frac_out": float(fo), "dwt_out": float(do),
            "live_out": float(live), "trim_bits": float(work_d - live),
            "live_ops": float(ops * live), "so_live": float(so * live)}


def Est_CMul(ModelCMul, ModelMul, ModelAdd, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False, METHOD="4mul"):
    params = _bundle(ModelCMul, ("lane_model", "features"), "Est_CMul")
    info = _cmul_structure(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK, IF_RST_N, METHOD)
    mul_area = sum(Est_MUL(ModelMul, *operand) for operand in info["mul_ops"])
    add_area = sum(Est_ADD(ModelAdd, *operand) for operand in info["pre_add_ops"])
    fx_area = info["fx_count"] * Est_FxMatch(*info["fx_ops"])
    lane = _predict(params["lane_model"], [info[name] for name in params["features"]])
    return mul_area + add_area + fx_area + lane


def _addertree_layers(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE, IF_RST_N):
    input_sign = int(bool(SIGN_IN)) if str(CONFIG_MODE).upper() == "A" else int(any(bool(value) for value in SIGN_IN))
    n_inputs = int(N_INPUTS)
    n_layers = int(math.ceil(math.log2(n_inputs)))
    if str(CONFIG_MODE).upper() == "A":
        layers = [(int(DWT_IN) + index, int(FRAC_IN), input_sign) for index in range(n_layers)] + [(int(DWT_OUT), int(FRAC_OUT), input_sign)]
        total = int(N_PIPELINES)
        base, extra = total // n_layers, total % n_layers
        pipelines = [base if index < n_layers - extra else base + 1 for index in range(n_layers)]
    else:
        layers = [(int(DWT_IN[index]), int(FRAC_IN[index]), int(bool(SIGN_IN[index]))) for index in range(n_layers)] + [(int(DWT_OUT), int(FRAC_OUT), input_sign)]
        pipelines = [int(value) for value in N_PIPELINES]
    resets = [bool(IF_RST_N) and pipelines[index] > 0 for index in range(n_layers)]
    return layers, pipelines, resets


def _addertree_window(DWT_OUT, FRAC_OUT, FRAC_LAYER, DWT_LAYER):
    return max(1, min(int(DWT_LAYER), int(DWT_OUT) + int(FRAC_LAYER) - int(FRAC_OUT)))


def _addertree_cut_width(src, dst, window):
    width = min(int(src[0]), int(window))
    if int(dst[0]) < int(src[0]):
        width = min(width, int(dst[0]))
    return max(int(src[1]) + 1, width)


def _addertree_ratio(DWT_OUT, FRAC_OUT, FRAC_LAYER, DWT_LAYER):
    return (float(DWT_OUT) + float(FRAC_LAYER) - float(FRAC_OUT)) / float(max(1, int(DWT_LAYER)))


def _addertree_blend(params, ratio):
    return min(1.0, max(0.0, 1.0 - float(ratio) / float(params["trim_span"])))


def _addertree_layer(params, ModelAdd, src, dst, pip, rst, DWT_OUT, FRAC_OUT):
    window = _addertree_window(DWT_OUT, FRAC_OUT, src[1], src[0])
    width = _addertree_cut_width(src, dst, window)
    blend = _addertree_blend(params, _addertree_ratio(DWT_OUT, FRAC_OUT, src[1], src[0]))
    full = Est_ADD(ModelAdd, src[0], src[1], src[2], src[0], src[1], src[2], dst[0], dst[1], pip, rst)
    cut = Est_ADD(ModelAdd, width, src[1], src[2], width, src[1], src[2], max(1, min(dst[0], width)), dst[1], pip, rst)
    rem_full = (Est_Delay(src[0], pip, rst) if pip > 0 else 0.0) + Est_FxMatch(src[0], src[1], src[2], dst[0], dst[1], dst[2], 0, False)
    rem_cut = (Est_Delay(width, pip, rst) if pip > 0 else 0.0) + Est_FxMatch(width, src[1], src[2], max(1, min(dst[0], width)), dst[1], dst[2], 0, False)
    return full, cut, blend, rem_full, rem_cut


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


def Est_AdderTree_Range(ModelAdderTree, ModelAdd, DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE="A", IF_RST_N=False):
    params = _bundle(ModelAdderTree, ("trim_span",), "Est_AdderTree")
    layers, pipelines, resets = _addertree_layers(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE, IF_RST_N)
    lower = 0.0
    upper = 0.0
    n_operators = int(N_INPUTS)
    for index in range(len(pipelines)):
        n_remainder = n_operators % 2
        n_adders = n_operators // 2
        n_operators = n_adders + n_remainder
        full, cut, blend, rem_full, rem_cut = _addertree_layer(params, ModelAdd, layers[index], layers[index + 1], pipelines[index], resets[index], DWT_OUT, FRAC_OUT)
        lower += n_adders * cut + (rem_cut if n_remainder == 1 else 0.0)
        upper += n_adders * full + (rem_full if n_remainder == 1 else 0.0)
    return lower, upper


def _comptree_structure(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE, IF_RST_N, IF_GIDX, IF_LIDX, IF_GVAL, IF_LVAL):
    n_inputs = int(N_INPUTS)
    n_layers = (n_inputs - 1).bit_length()
    if str(CONFIG_MODE).upper() == "A":
        types = [(int(DWT_IN) + 0, int(FRAC_IN), int(bool(SIGN_IN)))] * n_layers + [(int(DWT_OUT), int(FRAC_OUT), int(bool(SIGN_OUT)))]
        total = int(N_PIPELINES)
        base, extra = total // n_layers, total % n_layers
        depths = [base + int(index >= n_layers - extra) for index in range(n_layers)]
    else:
        types = [(int(DWT_IN[index]), int(FRAC_IN[index]), int(bool(SIGN_IN[index]))) for index in range(n_layers)] + [(int(DWT_OUT), int(FRAC_OUT), int(bool(SIGN_OUT)))]
        depths = [int(value) for value in N_PIPELINES]
    nodes, odds = [], []
    for side, need_value, need_index in (("g", bool(IF_GVAL), bool(IF_GIDX)), ("l", bool(IF_LVAL), bool(IF_LIDX))):
        if not (need_value or need_index):
            continue
        count = n_inputs
        for layer in range(n_layers):
            src, dst = types[layer], types[layer + 1]
            depth, rst = depths[layer], bool(IF_RST_N) and depths[layer] > 0
            live_value = bool(need_value) or layer < n_layers - 1
            gval, lval = side == "g" and live_value, side == "l" and live_value
            gidx, lidx = need_index and side == "g", need_index and side == "l"
            for _node in range(count // 2):
                nodes.append({"kind": "comppos" if (layer >= 1 and need_index) else "comp", "src": src, "dst": dst, "layer": layer,
                              "depth": depth, "rst": rst, "gval": gval, "lval": lval, "gidx": gidx, "lidx": lidx, "index_width": layer + 1})
            if count % 2:
                odds.append({"src": src, "dst": dst, "layer": layer, "depth": depth, "rst": rst, "need_value": live_value, "need_index": need_index, "index_width": layer + 1})
            count = (count + 1) // 2
    return {"types": types, "depths": depths, "n_layers": n_layers, "nodes": nodes, "odds": odds,
            "in_dwt": types[0][0], "in_frac": types[0][1], "in_sign": types[0][2], "out_dwt": types[-1][0], "out_frac": types[-1][1], "out_sign": types[-1][2],
            "n_layers_f": float(n_layers), "n_nodes_f": float(len(nodes)), "n_odds_f": float(len(odds)), "mode_a": 1.0 if str(CONFIG_MODE).upper() == "A" else 0.0,
            "if_gval": float(bool(IF_GVAL)), "if_lval": float(bool(IF_LVAL)), "if_gidx": float(bool(IF_GIDX)), "if_lidx": float(bool(IF_LIDX))}


def _comptree_assembly(info, ModelComp, return_parts=False):
    parts = {"comp": 0.0, "comppos": 0.0, "fx": 0.0, "delay": 0.0}
    for node in info["nodes"]:
        src, dst = node["src"], node["dst"]
        node_depth, node_rst = (node["depth"], node["rst"]) if node["kind"] == "comp" else (0, False)
        core = Est_Comp(ModelComp, src[0], src[1], src[2], src[0], src[1], src[2], dst[0], dst[1], dst[2], node_depth, node_rst, node["gidx"], node["lidx"], False, node["gval"], node["lval"])
        if node["kind"] == "comppos":
            inner = 0.0
            value_live = _comp_value_bits(src[0], src[1], src[2], src[0], src[1], src[2], dst[0], dst[1], dst[2], max(src[1], src[1]))
            if node["gidx"]: inner += Est_Delay(node["index_width"], node["depth"], node["rst"])
            if node["lidx"]: inner += Est_Delay(node["index_width"], node["depth"], node["rst"])
            if node["gval"]: inner += Est_Delay(value_live, node["depth"], node["rst"])
            if node["lval"]: inner += Est_Delay(value_live, node["depth"], node["rst"])
            parts["comppos"] += core + inner
        else:
            parts["comp"] += core
    for odd in info["odds"]:
        src, dst = odd["src"], odd["dst"]
        if odd["need_value"]:
            parts["fx"] += Est_FxMatch(src[0], src[1], src[2], dst[0], dst[1], dst[2], 0, False)
            parts["delay"] += Est_Delay(_fx_live_bits(src[0], src[1], src[2], dst[0], dst[1], dst[2]), odd["depth"], odd["rst"])
        if odd["need_index"]:
            parts["delay"] += Est_Delay(odd["index_width"], odd["depth"], odd["rst"])
    return parts if return_parts else sum(parts.values())


def Est_CompTree(ModelCompTree, ModelComp, DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE="A", IF_RST_N=False, IF_GIDX=False, IF_LIDX=False, IF_GVAL=False, IF_LVAL=False):
    params = _bundle(ModelCompTree, ("scale_model", "features"), "Est_CompTree")
    info = _comptree_structure(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_INPUTS, N_PIPELINES, CONFIG_MODE, IF_RST_N, IF_GIDX, IF_LIDX, IF_GVAL, IF_LVAL)
    assembly = _comptree_assembly(info, ModelComp)
    scale = _predict(params["scale_model"], [info[name] for name in params["features"]])
    return assembly * min(2.0, max(0.3, scale))
