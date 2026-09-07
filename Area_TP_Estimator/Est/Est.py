import pandas as pd
import os
import joblib
from KeyParam import adder_config_v2, MUL_op, S2U_out
import math
import time
import warnings
import numpy as np
from PyTU import QuMode, OfMode, QuType
from sklearn.metrics import mean_absolute_error
from scipy.stats import pearsonr
from functools import lru_cache
from PyTU import QuMode, OfMode, QuType

def Est_MUL(Model_MUL, Model_SU_out, SU_in_db, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines):
    DWT_IN_1 = int(DWT_IN_1)
    FRAC_IN_1 = int(FRAC_IN_1)
    SIGN_IN_1 = int(SIGN_IN_1)
    DWT_IN_2 = int(DWT_IN_2)
    FRAC_IN_2 = int(FRAC_IN_2)
    SIGN_IN_2 = int(SIGN_IN_2)
    DWT_OUT = int(DWT_OUT)
    FRAC_OUT = int(FRAC_OUT)
    n_pipelines = int(n_pipelines)
    y_pred = 0

    MSB_out = DWT_OUT -  FRAC_OUT -1
    LSB_out = -FRAC_OUT
    MSB_mul = DWT_IN_1 + DWT_IN_2 - FRAC_IN_1 - FRAC_IN_2 - 1
    LSB_mul = -FRAC_IN_1 - FRAC_IN_2
    DWT_mul = min(MSB_out, MSB_mul) - LSB_mul + 1
    if DWT_mul < 0:
        DWT_mul = 0

    if SIGN_IN_1 == 1:
        SU_in_area = SU_in_db.loc[DWT_IN_1 - 1, 'Area']
    else:
        SU_in_area = 0
    if SIGN_IN_2 == 1:
        # print("DWT_IN_2:", DWT_IN_2)
        SU_in_area += SU_in_db.loc[DWT_IN_2 - 1, 'Area']
    else:
        SU_in_area += 0
    y_pred = SU_in_area
    # # print("SU_in_area: ", y_pred)

    X = [DWT_IN_1, DWT_IN_2, DWT_mul]
    X_new = []
    X_new.append(MUL_op(*X))
    X_new = pd.DataFrame(X_new)
    # Model_MUL = joblib.load('./model/pure_MUL_area.pkl')
    y_pred += Model_MUL.predict(X_new)
    # print("pure_MUL_area: ", Model_MUL.predict(X_new))

    # X = [DWT_mul, 0, DWT_OUT, FRAC_OUT - FRAC_IN_1 - FRAC_IN_2, SIGN_IN_1, SIGN_IN_2]
    # X_new = []
    # X_new.append(S2U_out(*X))
    # X_new = pd.DataFrame(X_new)
    # # Model_SU_out = joblib.load('./model/SU_out_FxP_area.pkl')
    # y_pred += Model_SU_out.predict(X_new)
    # print("SU_out_FxP_area: ", model.predict(X_new))
    # print("MUL_area: ", y_pred)

    return y_pred

def Est_ADD(model, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines=0, if_rst_n=False):
    LSB_OUT = -FRAC_OUT
    MSB_OUT = DWT_OUT - FRAC_OUT - 1
    MSB_IN1 = DWT_IN_1 - FRAC_IN_1 - 1
    MSB_IN2 = DWT_IN_2 - FRAC_IN_2 - 1
    max_MSB_in = max(MSB_IN1, MSB_IN2) + 1
    sign_out = SIGN_IN_1 or SIGN_IN_2
    LSB_OUT = -min(max(FRAC_IN_1, FRAC_IN_2), FRAC_OUT)
    if (not sign_out) and (MSB_OUT > max_MSB_in):
        MSB_OUT = max_MSB_in
    # X = [DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines]
    # X_config = adder_config_v2(*X)
    # X_array = np.array([X_config])
    # y_pred = model.predict(X_array)[0]
    # y_pred += 5.88 * n_pipelines * DWT_OUT
    # y_pred += 1.12 * DWT_OUT
    X = [DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, 0]
    X_config = adder_config_v2(*X)
    # 优化：直接使用numpy数组而不是DataFrame
    X_array = np.array([X_config])
    y_pred = model.predict(X_array)[0]

    # New PyTV
    DWT_FIX = MSB_OUT - LSB_OUT + 1
    y_pred += 1.12 * DWT_FIX * 2

    if isinstance(if_rst_n, bool):
        multiplier = 6.72 if if_rst_n else 5.88
        y_pred += multiplier * DWT_FIX * n_pipelines
    else:
        # 优化：向量化计算替代循环
        if n_pipelines > 0 and len(if_rst_n) >= n_pipelines:
            rst_flags = if_rst_n[:n_pipelines]
            y_pred += DWT_FIX * sum(6.72 if flag else 5.88 for flag in rst_flags)
    # y_pred += Est_Delay(DWT_OUT, n_pipelines, if_rst_n)
    # print(Est_Delay(DWT_OUT, n_pipelines, if_rst_n))
    return y_pred

def Est_SUB(model, Sub_db, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines=0, if_rst_n=False):
    LSB_OUT = -FRAC_OUT
    LSB_IN2 = -FRAC_IN_2
    MSB_OUT = DWT_OUT - FRAC_OUT - 1
    MSB_IN2 = DWT_IN_2 - FRAC_IN_2 - 1
    LSB_FIX = max(LSB_OUT, LSB_IN2)
    MSB_FIX = min(MSB_OUT, MSB_IN2)
    DWT_FIX = MSB_FIX - LSB_FIX + 1
    y_pred = Est_ADD(model, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2 + 1, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines, if_rst_n)
    # print(y_pred)
    if DWT_FIX < 20:
        if hasattr(Sub_db, 'values') and len(Sub_db) > DWT_FIX - 1:
            SU_in_area = Sub_db.iloc[DWT_FIX - 1]['Area'] if 'Area' in Sub_db.columns else Sub_db.loc[DWT_FIX - 1, 'Area']
        else:
            SU_in_area = Sub_db.loc[DWT_FIX - 1, 'Area']
    else:
        SU_in_area = 4.759999999999996 * (DWT_FIX - 1) - 0.2799999999999345
    y_pred += SU_in_area
    # print(y_pred)
    return y_pred

def Est_Delay(DWT, CLK, IS_RST_N):
    if CLK == 0:
        return 1.12 * DWT
    if isinstance(IS_RST_N, bool):
        multiplier = 6.72 if IS_RST_N else 5.88
        return multiplier * DWT * CLK
    else:
        y_pred = 0
        for rst_flag in IS_RST_N:
            multiplier = 6.72 if rst_flag else 5.88
            y_pred += multiplier * DWT
        return y_pred

def Est_COMP(model, Sub_db, QU_IN_1:QuType, QU_IN_2:QuType, QU_OUT:QuType, N_PIPELINES, IF_RST_N, IF_GIDX=False, IF_LIDX=False, IF_EIDX=False, IF_GVAL=False, IF_LVAL=False):
    y_pred = 0
    QU_IN_FIX = QuType()
    LSB_FIX = -max(QU_IN_1.FRAC, QU_IN_2.FRAC)
    MSB_FIX = max(QU_IN_1.DWT - QU_IN_1.FRAC, QU_IN_2.DWT - QU_IN_2.FRAC+1)
    QU_IN_FIX.DWT = MSB_FIX - LSB_FIX + 1
    QU_IN_FIX.FRAC = -LSB_FIX
    QU_IN_FIX.IF_SIGNED = QU_IN_1.IF_SIGNED or QU_IN_2.IF_SIGNED
    if QU_IN_FIX.IF_SIGNED:
        y_pred += Est_SUB(model, Sub_db, QU_IN_1.DWT, QU_IN_1.FRAC, QU_IN_1.IF_SIGNED,
                          QU_IN_2.DWT, QU_IN_2.FRAC, QU_IN_2.IF_SIGNED,
                          QU_IN_FIX.DWT, QU_IN_FIX.FRAC, N_PIPELINES, IF_RST_N)
        if IF_GIDX:
            y_pred += Est_Delay(1, N_PIPELINES, IF_RST_N)
        if IF_LIDX:
            y_pred += Est_Delay(1, N_PIPELINES, IF_RST_N)
        if IF_EIDX:
            y_pred += Est_Delay(1, N_PIPELINES, IF_RST_N)
        if IF_GVAL:
            y_pred += Est_Delay(QU_OUT.DWT, N_PIPELINES, IF_RST_N)
        if IF_LVAL:
            y_pred += Est_Delay(QU_OUT.DWT, N_PIPELINES, IF_RST_N)
    else:
        if IF_GIDX:
            y_pred += Est_Delay(1, N_PIPELINES, IF_RST_N)
        if IF_GVAL:
            y_pred += Est_Delay(QU_OUT.DWT, N_PIPELINES, IF_RST_N)
    if IF_GVAL or IF_LVAL:
        y_pred += Est_Delay(QU_OUT.DWT, 0, IF_RST_N)
        y_pred += Est_Delay(QU_OUT.DWT, 0, IF_RST_N)
    print(y_pred)
    return y_pred

# ---------- 主程序 ----------
if __name__ == "__main__":
    path = "."

    SU_in_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='SU_in', header=0)
    Sub_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='Sub', header=0)
    Model_ADD = joblib.load(path + '/model/ADD_area.pkl')
    Model_MUL = joblib.load(path + '/model/pure_MUL_area.pkl')
    Model_SU_out = joblib.load(path + '/model/SU_out_FxP_area.pkl')

    EXCEL_FILE = path + "/cases.xlsx"
    if not os.path.exists(EXCEL_FILE):
        print(f"错误：文件 {EXCEL_FILE} 不存在！")
        exit(1)

    xls = pd.ExcelFile(EXCEL_FILE)
    sheets = ['Comp', 'Delay', 'Sub', 'Add', 'newSub']

    for sheet in sheets:
        df = pd.read_excel(xls, sheet_name=sheet)
        print(f"\n========== 处理 Sheet: {sheet} ==========")
        for idx, row in df.iterrows():
            case = row['case']
            folder = row['folder']
            if sheet == 'Comp':
                qu_in1 = QuType(int(row['DWT1']), int(row['FRAC1']), bool(row['SIGNED1']))
                qu_in2 = QuType(int(row['DWT2']), int(row['FRAC2']), bool(row['SIGNED2']))
                qu_out = QuType(int(row['DWTOUT']), int(row['FRACOUT']), qu_in1.IF_SIGNED and qu_in2.IF_SIGNED)
                n_pipelines = int(row['N_PIPELINES'])
                if_rst_n = bool(row['IF_RST_N'])
                if_gidx = bool(row['IF_GIDX'])
                if_lidx = bool(row['IF_LIDX'])
                if_eidx = bool(row['IF_EIDX'])
                if_gval = bool(row['IF_GVAL'])
                if_lval = bool(row['IF_LVAL'])
                area = Est_COMP(Model_ADD, Sub_db, qu_in1, qu_in2, qu_out, n_pipelines, if_rst_n, if_gidx, if_lidx, if_eidx, if_gval, if_lval)
            elif sheet == 'Delay':
                dwt = int(row['DWT'])
                n_clk = int(row['N_CLK'])
                if_rst_n = bool(row['IF_RST_N'])
                # area = Est_Delay(dwt, n_clk, if_rst_n)
            elif sheet == 'newSub':
                area = Est_SUB(Model_ADD, Sub_db,
                               int(row['DWT1']), int(row['FRAC1']), bool(row['SIGNED1']),
                               int(row['DWT2']), int(row['FRAC2']), bool(row['SIGNED2']),
                               int(row['DWTOUT']), int(row['FRACOUT']),
                               int(row['N_PIPELINES']), bool(row['IF_RST_N']))
            # elif sheet == 'Add' or sheet == 'Add_frac0':
            #     area = Est_ADD(Model_ADD,
            #                    int(row['DWT1']), int(row['FRAC1']), bool(row['SIGNED1']),
            #                    int(row['DWT2']), int(row['FRAC2']), bool(row['SIGNED2']),
            #                    int(row['DWTOUT']), int(row['FRACOUT']),
            #                    int(row['N_PIPELINES']), bool(row['IF_RST_N']))
            else:
                continue
            # print(area)   # 仅打印评估面积
