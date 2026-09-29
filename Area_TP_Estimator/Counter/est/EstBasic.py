import pandas as pd
import numpy as np
from KeyParam import adder_config_v2, MUL_op

_LIB_WIRE_AREA = 1.12
_LIB_FF_AREA = 5.88
_LIB_FF_AREA_RST = 6.72
_LIB_FF_AREA_EN = 7.84
_LIB_INV_AREA = 0.84


def _bitlen(value):
    bits = 0
    while value > 0:
        bits += 1
        value >>= 1
    return bits


def _adder_config(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT):
    config = adder_config_v2(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, 0)
    return np.asarray(config, dtype=float)[:7]


def _comb_area(Model, *features):
    vector = np.concatenate([np.asarray(feature, dtype=float).reshape(-1) for feature in features])
    try:
        return float(np.asarray(Model.predict(vector.reshape(1, -1))).reshape(-1)[0])
    except ValueError as exc:
        raise ValueError("模型特征数不匹配: 本函数给出 {} 个结构门计数, 请确认传入的 pkl 与它配套。原始错误: {}".format(vector.size, exc))


def _predict(Model, features):
    vector = np.asarray(features, dtype=float).reshape(1, -1)
    try:
        return float(np.asarray(Model.predict(vector)).reshape(-1)[0])
    except ValueError as exc:
        raise ValueError("模型特征数不匹配: 本函数给出 {} 个特征, 请确认传入的 pkl 与它配套。原始错误: {}".format(vector.size, exc))


def _mul_params(ModelMul):
    required = ("abs_model", "array_model", "reg_model", "flat_max_product", "trim_max_span", "trim_d2_max", "trim_dwt_max")
    if isinstance(ModelMul, dict) and all(key in ModelMul for key in required):
        return ModelMul
    raise TypeError("Est_MUL 的 ModelMul 参数需要 Est/model/MUL_area_model.pkl (dict: abs_model / array_model / reg_model + flat_max_product / trim_max_span / trim_d2_max / trim_dwt_max); 旧版 pure_MUL_area.pkl 只在完整阵列上标定, 已不适用于本实现, 请用 tools/fit_mul_area_model.py 重新标定。")


def _add_reg_bits(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT):
    LSB_OUT = -min(max(FRAC_IN_1, FRAC_IN_2), FRAC_OUT)
    MSB_OUT = DWT_OUT - FRAC_OUT - 1
    max_MSB_in = max(DWT_IN_1 - FRAC_IN_1 - 1, DWT_IN_2 - FRAC_IN_2 - 1) + 1
    if (not (SIGN_IN_1 or SIGN_IN_2)) and MSB_OUT > max_MSB_in:
        MSB_OUT = max_MSB_in
    return MSB_OUT - LSB_OUT + 1


def _operand_value_range(DWT, FRAC, SIGN, LSB_FIX):
    shift = -int(LSB_FIX) - int(FRAC)
    if int(SIGN):
        low, high = -(1 << (int(DWT) - 1)), (1 << (int(DWT) - 1)) - 1
    else:
        low, high = 0, (1 << int(DWT)) - 1
    if shift >= 0:
        return low << shift, high << shift
    return low >> (-shift), high >> (-shift)


def _sub_reg_bits(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT):
    LSB_FIX = -max(FRAC_IN_1, FRAC_IN_2)
    lo_1, hi_1 = _operand_value_range(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, LSB_FIX)
    lo_2, hi_2 = _operand_value_range(DWT_IN_2, FRAC_IN_2, SIGN_IN_2, LSB_FIX)
    lo, hi = lo_1 - hi_2, hi_1 - lo_2
    shift = FRAC_OUT + LSB_FIX
    if shift >= 0:
        lo, hi = lo << shift, hi << shift
    else:
        lo, hi = lo >> (-shift), hi >> (-shift)
    sign_out = int(SIGN_IN_1) or int(SIGN_IN_2)
    DWT_out_eq = DWT_OUT + (0 if sign_out else 1)
    modulus = 1 << DWT_out_eq
    mask = modulus - 1

    def _wrap(value):
        value &= mask
        return value - modulus if value >= (1 << (DWT_out_eq - 1)) else value

    if (hi - lo) >= mask:
        low, high = (-(1 << (DWT_out_eq - 1)), (1 << (DWT_out_eq - 1)) - 1) if sign_out \
            else (0, (1 << DWT_OUT) - 1)
    else:
        a, b = _wrap(lo), _wrap(hi)
        low, high = (a, b) if a <= b else (b, a)
    top_bit = DWT_OUT - 1
    if low < 0:
        highest = top_bit
    else:
        highest = min(top_bit, max(low, high).bit_length() - 1)
    if high > low or (low < 0 <= high):
        lowest = max(0, shift)
    else:
        lowest = top_bit + 1
    return max(0, min(DWT_OUT, highest - lowest + 1))


def _fx_live_bits(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT):
    SIGN_IN = int(SIGN_IN)
    SIGN_OUT = int(SIGN_OUT)
    DWT_in_eq = DWT_IN + (0 if SIGN_IN else 1)
    DWT_out_eq = DWT_OUT + (0 if SIGN_OUT else 1)
    MSB_in = DWT_in_eq - FRAC_IN - 1
    LSB_in = -FRAC_IN
    LSB_out = -FRAC_OUT
    shift = LSB_out - LSB_in

    if SIGN_IN:
        lo = -(1 << (MSB_in - LSB_in))
        hi = (1 << (MSB_in - LSB_in)) - 1
    else:
        lo, hi = 0, (1 << DWT_IN) - 1

    if shift > 0:
        qlo, qhi = lo >> shift, hi >> shift
    elif shift < 0:
        qlo, qhi = lo << (-shift), hi << (-shift)
    else:
        qlo, qhi = lo, hi

    m = 1 << DWT_out_eq
    mask = m - 1
    if (qhi - qlo) >= mask:
        if SIGN_OUT:
            olo, ohi = -(1 << (DWT_out_eq - 1)), (1 << (DWT_out_eq - 1)) - 1
        else:
            olo, ohi = 0, (1 << DWT_OUT) - 1
    else:
        a = qlo & mask
        if a >= (1 << (DWT_out_eq - 1)):
            a -= m
        b = qhi & mask
        if b >= (1 << (DWT_out_eq - 1)):
            b -= m
        olo, ohi = (a, b) if a <= b else (b, a)

    pad = max(0, FRAC_OUT - FRAC_IN)
    if olo >= 0:
        w_eff = _bitlen(ohi) - pad
    else:
        w_eff = DWT_OUT - pad
    return max(1, min(DWT_OUT, w_eff))


def _fx_pad_bits(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT):
    MSB_in = DWT_IN + (0 if int(SIGN_IN) else 1) - FRAC_IN - 1
    MSB_out = DWT_OUT + (0 if int(SIGN_OUT) else 1) - FRAC_OUT - 1
    return max(0, FRAC_OUT - FRAC_IN), max(0, MSB_out - MSB_in)


def _fx_is_constant(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT):
    LSB_in, LSB_out = -int(FRAC_IN), -int(FRAC_OUT)
    DWT_out_eq = int(DWT_OUT) + (0 if int(SIGN_OUT) else 1)
    if int(SIGN_IN):
        # The raw two's-complement range depends on storage width; FRAC only
        # locates the binary point and must not reduce the shift count.
        lo = -(1 << (int(DWT_IN) - 1))
        hi = (1 << (int(DWT_IN) - 1)) - 1
    else:
        lo, hi = 0, (1 << int(DWT_IN)) - 1
    shift = LSB_out - LSB_in
    if shift > 0:
        qlo, qhi = lo >> shift, hi >> shift
    elif shift < 0:
        qlo, qhi = lo << (-shift), hi << (-shift)
    else:
        qlo, qhi = lo, hi
    if qlo == qhi:
        return True
    return (LSB_in - LSB_out) >= DWT_out_eq


def _mul_structure(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines, flat_max_product, trim_max_span, trim_d2_max, trim_dwt_max):
    DWT_IN_1, FRAC_IN_1, SIGN_IN_1 = int(DWT_IN_1), int(FRAC_IN_1), int(SIGN_IN_1)
    DWT_IN_2, FRAC_IN_2, SIGN_IN_2 = int(DWT_IN_2), int(FRAC_IN_2), int(SIGN_IN_2)
    DWT_OUT, FRAC_OUT, n_pipelines = int(DWT_OUT), int(FRAC_OUT), int(n_pipelines)

    LSB_mul = -FRAC_IN_1 - FRAC_IN_2
    MSB_mul = DWT_IN_1 + DWT_IN_2 - FRAC_IN_1 - FRAC_IN_2 - 1
    MSB_out = DWT_OUT - FRAC_OUT - 1
    DWT_mul = max(0, MSB_mul - LSB_mul + 1)
    sign_out = int(bool(SIGN_IN_1 or SIGN_IN_2))
    span = min(MSB_out, MSB_mul) - LSB_mul + 1

    flat = int(DWT_IN_1 * DWT_IN_2 <= int(flat_max_product))
    trim = 0
    if flat:
        w_arr = w_reg = 0
    else:
        trim = int((sign_out == 0) or (span <= int(trim_max_span)
                                       and (DWT_IN_2 <= int(trim_d2_max)
                                            or DWT_mul <= int(trim_dwt_max))))
        if trim:
            w_arr = w_reg = max(0, span)
        else:
            w_arr = w_reg = DWT_mul

    pipe_product = int(sign_out == 1 and n_pipelines >= 2)
    stages = n_pipelines - 1 if pipe_product else n_pipelines
    top_bits = (w_reg + 1) if pipe_product else 0
    pad = max(0, FRAC_OUT - FRAC_IN_1 - FRAC_IN_2)
    hi_zero = 0 if sign_out else min(2, max(0, DWT_OUT - 1 - (MSB_mul + FRAC_OUT)))
    return {"DWT_mul": DWT_mul, "LSB_mul": LSB_mul, "MSB_mul": MSB_mul, "MSB_out": MSB_out, "sign_out": sign_out, "span": span, "flat": flat, "trim": trim, "w_arr": w_arr, "w_reg": w_reg, "stages": stages, "top_bits": top_bits, "pad": pad, "hi_zero": hi_zero}


def _mul_abs_features(struct, SIGN_IN_1, SIGN_IN_2, DWT_IN_1, DWT_IN_2, n_pipelines):
    SIGN_IN_1, SIGN_IN_2 = int(bool(SIGN_IN_1)), int(bool(SIGN_IN_2))
    DWT_IN_1, DWT_IN_2, n_pipelines = int(DWT_IN_1), int(DWT_IN_2), int(n_pipelines)
    features = [0.0] * 7
    if struct["flat"]:
        features[4] = float(DWT_IN_1 * DWT_IN_2)
        features[5] = float((SIGN_IN_1 + SIGN_IN_2) * DWT_IN_1 * DWT_IN_2)
        features[6] = float(n_pipelines)
    else:
        features[0] = float(SIGN_IN_1)
        features[1] = float(SIGN_IN_2)
        features[2] = float(SIGN_IN_1 * DWT_IN_1)
        features[3] = float(SIGN_IN_2 * DWT_IN_2)
    features.append(float(int(bool(SIGN_IN_1 or SIGN_IN_2)) * struct["span"]))
    return features


def _mul_reg_features(struct, DWT_OUT):
    DWT_OUT = int(DWT_OUT)
    stages = struct["stages"]
    return [float(struct["top_bits"]), float(stages * DWT_OUT), float(stages * struct["pad"]), float(stages * struct["hi_zero"])]


def Est_Delay(DWT, CLK, IS_RST_N):
    if CLK == 0:
        return _LIB_WIRE_AREA * DWT
    if isinstance(IS_RST_N, bool):
        multiplier = _LIB_FF_AREA_RST if IS_RST_N else _LIB_FF_AREA
        return multiplier * DWT * CLK
    y_pred = 0
    for rst_flag in IS_RST_N:
        multiplier = _LIB_FF_AREA_RST if rst_flag else _LIB_FF_AREA
        y_pred += multiplier * DWT
    return y_pred


def Est_MUL(ModelMul, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines=0, if_rst_n=False):
    params = _mul_params(ModelMul)
    DWT_IN_1, FRAC_IN_1, SIGN_IN_1 = int(DWT_IN_1), int(FRAC_IN_1), int(SIGN_IN_1)
    DWT_IN_2, FRAC_IN_2, SIGN_IN_2 = int(DWT_IN_2), int(FRAC_IN_2), int(SIGN_IN_2)
    DWT_OUT, FRAC_OUT, n_pipelines = int(DWT_OUT), int(FRAC_OUT), int(n_pipelines)
    struct = _mul_structure(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines, params["flat_max_product"], params["trim_max_span"], params["trim_d2_max"], params["trim_dwt_max"])
    sign_out = struct["sign_out"]

    abs_features = _mul_abs_features(struct, SIGN_IN_1, SIGN_IN_2, DWT_IN_1, DWT_IN_2, n_pipelines)
    y_pred = max(0.0, _predict(params["abs_model"], abs_features))

    mul_feature = np.asarray(MUL_op(DWT_IN_1, DWT_IN_2, struct["w_arr"]), dtype=float)
    y_pred += max(0.0, _predict(params["array_model"], mul_feature))

    y_pred += Est_FxMatch(struct["DWT_mul"], -struct["LSB_mul"], sign_out, DWT_OUT, FRAC_OUT, sign_out, 0)

    units = _LIB_FF_AREA_RST if (isinstance(if_rst_n, bool) and if_rst_n) else _LIB_FF_AREA
    if not isinstance(if_rst_n, bool):
        flags = list(if_rst_n)[:n_pipelines] if len(if_rst_n) >= n_pipelines else []
        if flags:
            ratio = sum(_LIB_FF_AREA_RST if flag else _LIB_FF_AREA for flag in flags) / len(flags)
            units = ratio
        else:
            units = 0.0
    y_pred += max(0.0, _predict(params["reg_model"], _mul_reg_features(struct, DWT_OUT))) * units
    return y_pred


def Est_ADD(ModelAdd, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines=0, if_rst_n=False):
    y_pred = _comb_area(ModelAdd, _adder_config(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT))
    y_pred += Est_Delay(_add_reg_bits(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT), n_pipelines, if_rst_n)
    return y_pred


def _sub_feature_pool(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT):
    negated = _adder_config(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2 + 1, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT)
    raw = _adder_config(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT)
    pool = {"dmax": float(max(DWT_IN_1, DWT_IN_2)), "dmin": float(min(DWT_IN_1, DWT_IN_2)), "dsum": float(DWT_IN_1 + DWT_IN_2),
            "fsum": float(FRAC_IN_1 + FRAC_IN_2), "F1": float(FRAC_IN_1), "F2": float(FRAC_IN_2),
            "s12": float(int(bool(SIGN_IN_1)) + int(bool(SIGN_IN_2)))}
    for index in range(7):
        pool["cn{}".format(index)] = float(negated[index])
        pool["cr{}".format(index)] = float(raw[index])
    return pool


def _sub_feature_names():
    return ["cn{}".format(index) for index in range(7)] + ["cr{}".format(index) for index in range(7)] + ["dmax", "dmin", "dsum", "fsum", "F1", "F2", "s12"]


def Est_SUB(ModelSub, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines=0, if_rst_n=False):
    if not (isinstance(ModelSub, dict) and "coef" in ModelSub and "features" in ModelSub):
        raise TypeError("Est_SUB 的 ModelSub 需要 Est/model/SUB_comb_area.pkl (dict: coef / features), 请先跑 tools/fit_sub_comb_model.py 标定。")
    pool = _sub_feature_pool(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT)
    y_pred = float(np.dot(np.asarray([pool[name] for name in ModelSub["features"]], dtype=float), np.asarray(ModelSub["coef"], dtype=float)))
    y_pred += Est_Delay(_sub_reg_bits(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT), n_pipelines, if_rst_n)
    return y_pred


def Est_FxMatch(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT, N_CLK=0, IF_RST_N=False):
    DWT_IN = int(DWT_IN)
    FRAC_IN = int(FRAC_IN)
    SIGN_IN = int(SIGN_IN)
    DWT_OUT = int(DWT_OUT)
    FRAC_OUT = int(FRAC_OUT)
    SIGN_OUT = int(SIGN_OUT)
    N_CLK = int(N_CLK)

    if _fx_is_constant(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT):
        return _LIB_INV_AREA * DWT_OUT

    w_eff = _fx_live_bits(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT)
    if N_CLK > 0:
        if isinstance(IF_RST_N, bool):
            y_pred = (_LIB_FF_AREA_RST if IF_RST_N else _LIB_FF_AREA) * w_eff * N_CLK
        else:
            y_pred = w_eff * sum(_LIB_FF_AREA_RST if flag else _LIB_FF_AREA
                                 for flag in IF_RST_N[:N_CLK])
    else:
        y_pred = _LIB_WIRE_AREA * w_eff

    lsb_pad, msb_pad = _fx_pad_bits(DWT_IN, FRAC_IN, SIGN_IN, DWT_OUT, FRAC_OUT, SIGN_OUT)
    cells = lsb_pad + (0 if SIGN_IN else msb_pad)
    if SIGN_IN == 0 and SIGN_OUT == 1 and (msb_pad > 0 or (N_CLK == 0 and lsb_pad > 0)):
        cells += 1
    y_pred += _LIB_INV_AREA * cells
    return y_pred
