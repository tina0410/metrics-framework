from EstBasic import *
from EstDerived import *
from EstBasic import _sub_feature_pool, _sub_reg_bits

def Est_SUB(ModelSub, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines=0, if_rst_n=False):
    if not (isinstance(ModelSub, dict) and "coef" in ModelSub and "features" in ModelSub):
        raise TypeError("Est_SUB 的 ModelSub 需要 Est/model/SUB_comb_area.pkl (dict: coef / features), 请先跑 tools/fit_sub_comb_model.py 标定。")
    pool = _sub_feature_pool(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT)
    y_pred = float(np.dot(np.asarray([pool[name] for name in ModelSub["features"]], dtype=float), np.asarray(ModelSub["coef"], dtype=float)))
    y_pred += Est_Delay(_sub_reg_bits(DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT), n_pipelines, if_rst_n)
    return y_pred
