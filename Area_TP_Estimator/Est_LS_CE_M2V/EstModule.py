import pandas as pd
# import os
import joblib
from KeyParam import adder_config_v2, MUL_op, S2U_out
import math
import time
import warnings
# import numpy as np
from PyTU import QuMode, OfMode, QuType
# from sklearn.metrics import mean_absolute_error
# from scipy.stats import pearsonr
# from functools import lru_cache
from PyTU import QuMode, OfMode, QuType

class ModelContext:
    def __init__(self, su_in_db=None, model_su_out=None, model_mul=None):
        self.su_in_db = su_in_db
        self.model_su_out = model_su_out
        self.model_mul = model_mul

context = ModelContext()

def init_context(su_in_db, model_su_out, model_mul=None):
    """初始化模型上下文"""
    context.su_in_db = su_in_db
    context.model_su_out = model_su_out
    context.model_mul = model_mul
    return context
    
def model_predict_wrapper(X_new, model_su_out):
    """将DataFrame转换为可哈希类型数据进行预测的包装函数"""
    X_df = pd.DataFrame([X_new])
    return float(model_su_out.predict(X_df)[0])

# 2. 针对SU_in_db的查询包装函数
def get_su_area(dwt, sign, su_in_db):
    """获取SU面积的包装函数,转换为更简单的查询"""
    if sign == 1:
        return float(su_in_db.loc[dwt - 1, 'Area'])
    return 0.0

# DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines
def Est_SUB(model, Sub_db, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines):
    X = [DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2 + 1, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, 0]
    X_new = []
    X_new.append(adder_config_v2(*X))
    # model =  joblib.load('./model/ADD_area.pkl')
    y_pred = model.predict(X_new)
    if DWT_IN_2 < 20:
        SU_in_area = Sub_db.loc[DWT_IN_2 - 1, 'Area']
    else:
        SU_in_area = 4.759999999999996 * (DWT_IN_2 - 1) - 0.2799999999999345
    y_pred += SU_in_area
    if n_pipelines == 0:
        y_pred += 1.12 * DWT_OUT
    else:
        y_pred += 5.88 * DWT_OUT * n_pipelines
    # print("ADD_area: ", y_pred)
    return y_pred

# DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines
def Est_ADD(model, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines):
    X = [DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, 0]
    X_new = []
    X_new.append(adder_config_v2(*X))
    # model =  joblib.load('./model/ADD_area.pkl')
    y_pred = model.predict(X_new)
    # New PyTV
    if n_pipelines == 0:
        y_pred += 1.12 * DWT_OUT
    else:
        y_pred += 5.88 * DWT_OUT * n_pipelines
    # print("ADD_area: ", y_pred)
    return y_pred

# SU_in_db, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines
def Est_MUL(Model_MUL, Model_SU_out, SU_in_db, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines):
    MSB_out = DWT_OUT -  FRAC_OUT -1
    LSB_out = -FRAC_OUT
    # print("DWT_IN_1:", DWT_IN_1)
    # print("DWT_IN_2:", DWT_IN_2)
    # print("FRAC_IN_1:", FRAC_IN_1)
    # print("FRAC_IN_2:", FRAC_IN_2)
    MSB_mul = DWT_IN_1 + DWT_IN_2 - FRAC_IN_1 - FRAC_IN_2 - 1
    LSB_mul = -FRAC_IN_1 - FRAC_IN_2
    DWT_mul = min(MSB_out, MSB_mul) - LSB_mul + 1
    # DWT_mul = DWT_IN_1
    if DWT_mul < 0:
        DWT_mul = 0

    if SIGN_IN_1 == 1:
        if DWT_IN_1 < 90:
            SU_in_area = SU_in_db.loc[DWT_IN_1 - 1, 'Area']
        else:
            SU_in_area = 7.025313962352943 * (DWT_IN_1 - 1) - 7.608355686274602
    else:
        SU_in_area = 0
    if SIGN_IN_2 == 1:
        if DWT_IN_1 < 90:
            SU_in_area += SU_in_db.loc[DWT_IN_1 - 1, 'Area']
        else:
            SU_in_area += 7.025313962352943 * (DWT_IN_2 - 1) - 7.608355686274602
    else:
        SU_in_area += 0
    y_pred = SU_in_area
    # print("SU_in_area: ", y_pred)
    
    if LSB_out - LSB_mul <= 1 and DWT_OUT <= 2:
        DWT_mul = min(MSB_out, MSB_mul) - LSB_mul + 1
    else:
        DWT_mul = DWT_IN_1 + DWT_IN_2
    # DWT_mul = DWT_IN_1 + DWT_IN_2
    X = [DWT_IN_1, DWT_IN_2, DWT_mul]
    X_new = []
    X_new.append(MUL_op(*X))
    X_new = pd.DataFrame(X_new)
    # Model_MUL = joblib.load('./model/pure_MUL_area.pkl')
    y_pred += Model_MUL.predict(X_new)
    # print("pure_MUL_area: ", Model_MUL.predict(X_new))
    
    DWT_mul = min(MSB_out, MSB_mul) - LSB_mul + 1
    X = [DWT_mul, 0, DWT_OUT, FRAC_OUT - FRAC_IN_1 - FRAC_IN_2, SIGN_IN_1, SIGN_IN_2]
    X_new = []
    X_new.append(S2U_out(*X))
    X_new = pd.DataFrame(X_new)
    # Model_SU_out = joblib.load('./model/SU_out_FxP_area.pkl')
    y_pred += Model_SU_out.predict(X_new)
    # print("SU_out_FxP_area: ", Model_SU_out.predict(X_new))
    # print("MUL_area: ", y_pred)
    y_pred += 5.88 * DWT_OUT * n_pipelines

    return y_pred
    
# Adder Tree
def Est_AT(model, N_INPUTS, QU_AT, QU_OUT, n_pipelines):
    #  QU_AT = [QU_IN_1, QU_OUT_L0, QU_OUT_L1, ...], same for FRAC_AT, SIGN_AT
    #  n_pipelines = [n_pipelines_L0, n_pipelines_L1, ...]
    QU_AT.append(QU_OUT)
    layers =  math.ceil(math.log2(N_INPUTS))
    points = N_INPUTS
    y_pred = 0
    cnt = []
    # the number of adders in each layer
    for l in range(layers):
        tmp = points // 2
        cnt.append(tmp)
        points = points - tmp
    # add area
    for l in range(layers):
        # add_area = (Est_ADD(model, QU_AT[l][0], QU_AT[l][1], QU_AT[l][2], QU_AT[l][0], QU_AT[l][1], QU_AT[l][2], QU_AT[l][0] + 1, QU_AT[l][1], n_pipelines[l])+QU_AT[l][0]*1.1*4) * cnt[l]
        add_area = (Est_ADD(model, QU_AT[l][0], QU_AT[l][1], QU_AT[l][2], QU_AT[l][0], QU_AT[l][1], QU_AT[l][2], QU_AT[l+1][0], QU_AT[l+1][1], 0)) * cnt[l]
        # print(Est_ADD(model, QU_AT[l][0], QU_AT[l][1], QU_AT[l][2], QU_AT[l][0], QU_AT[l][1], QU_AT[l][2], QU_AT[l][0]+1, QU_AT[l][1], 0))
        add_area += QU_AT[l+1][0] * n_pipelines[l] * 5.88  # Adding some constant overhead
        # print("Adder Tree layer", l, "area:", add_area)
        y_pred += add_area
    # y_pred += 1.26 * QU_OUT[0]
    return y_pred

def Est_M2V(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, M:int, V:int, QU_M:QuType, QU_V:QuType, QU_M_V:QuType, QU_OUT:QuType, N_PIPELINES):
    y_pred = 0
    y_pred_at = 0
    n_layers = math.ceil(math.log2(V))
    QU_AT = []
    
    for i in range(n_layers):
        QU_AT.append([QU_M_V.DWT + i, QU_M_V.FRAC, QU_M_V.IF_SIGNED]) 
    QU_OUT = [QU_OUT.DWT, QU_OUT.FRAC, QU_OUT.IF_SIGNED]
          
    base_pipelines = N_PIPELINES[1] // n_layers
    extra_pipelines = N_PIPELINES[1] % n_layers
    N_PIPELINES_AT = [base_pipelines if i < n_layers - extra_pipelines else base_pipelines + 1 for i in range(n_layers)]
    
    if V == 1:
        y_pred_mul = (M * V) * Est_MUL(Model_MUL, Model_SU_out, SU_in_db, QU_M.DWT, QU_M.FRAC, QU_M.IF_SIGNED, QU_V.DWT, QU_V.FRAC, QU_V.IF_SIGNED, QU_OUT.DWT, QU_OUT.FRAC, N_PIPELINES[0])
    else:
        y_pred_mul = (M * V) * Est_MUL(Model_MUL, Model_SU_out, SU_in_db, QU_M.DWT, QU_M.FRAC, QU_M.IF_SIGNED, QU_V.DWT, QU_V.FRAC, QU_V.IF_SIGNED, QU_M_V.DWT, QU_M_V.FRAC, N_PIPELINES[0])
        # print("y_pred_mul:", Est_MUL(Model_MUL, Model_SU_out, SU_in_db, QU_M.DWT, QU_M.FRAC, QU_M.IF_SIGNED, QU_V.DWT, QU_V.FRAC, QU_V.IF_SIGNED, QU_M_V.DWT, QU_M_V.FRAC, N_PIPELINES[0]))
        y_pred_at = M * Est_AT(ModelAdd, V, QU_AT, QU_OUT, N_PIPELINES_AT)
        # print("y_pred_at:", y_pred_at)
        
    y_pred = y_pred_mul + y_pred_at
    
    # y_pred = float(y_pred)

    return y_pred

if __name__ == '__main__':
    # os.chdir(os.path.dirname(__file__))
    warnings.filterwarnings("ignore")
    path = "."
    SU_in_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='SU_in', header = 0)
    Sub_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='Sub', header = 0)
    Model_ADD = joblib.load(path +'/model/ADD_area.pkl')
    Model_MUL = joblib.load(path +'/model/pure_MUL_area.pkl')
    Model_SU_out = joblib.load(path +'/model/SU_out_FxP_area.pkl')
    su_in_db_id = "ctx_su_in_db"
    model_su_out_id = "ctx_model_su_out"
    
    start = time.time()

    # print(Est_AT(Model_ADD, 3, [[10,2,1],[9,2,1]], [8,2,1], [0, 1]))
    # ModelAdd, Model_MUL, Model_SU_out, SU_in_db, M:int, V:int, QU_M:QuType, QU_V:QuType, QU_M_V:QuType, QU_OUT:QuType, N_PIPELINES
    print(Est_M2V(Model_ADD, Model_MUL, Model_SU_out, SU_in_db, M = 16, V = 10, 
                  QU_M = QuType(DWT=8, FRAC=2, IF_SIGNED=True), 
                  QU_V = QuType(DWT=8, FRAC=2, IF_SIGNED=True), 
                  QU_M_V = QuType(DWT=8, FRAC=0, IF_SIGNED=True), 
                  QU_OUT = QuType(DWT=8, FRAC=0, IF_SIGNED=True),
                  N_PIPELINES=[1, 1]))
    # print(Est_ADD(Model_ADD, 10,4,1,9,3,1,9,2,0))
    
    end = time.time()
    print("Time taken: ", end - start)
