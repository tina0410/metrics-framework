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

# 常量预计算
CONST_6_72 = 6.72
CONST_5_88 = 5.88
CONST_1_12 = 1.12
CONST_COEFF_1 = 7.025313962352943
CONST_COEFF_2 = -7.608355686274602
CONST_COEFF_3 = 4.759999999999996
CONST_COEFF_4 = -0.2799999999999345

@lru_cache(maxsize=128)
def _cached_log2_ceil(n):
    """缓存的 ceil(log2(n)) 计算"""
    return math.ceil(math.log2(n))

@lru_cache(maxsize=256)
def _cached_pipeline_distribution(n_pipelines, layers):
    """缓存的管道分布计算"""
    base_pipelines = n_pipelines // layers
    extra_pipelines = n_pipelines % layers
    pipeline_dist = [base_pipelines] * layers
    
    if extra_pipelines >= 2:
        pipeline_dist[0] += 1
        pipeline_dist[-1] += 1
        extra_pipelines -= 2
    elif extra_pipelines == 1:
        pipeline_dist[0] += 1
        extra_pipelines -= 1

    if extra_pipelines > 0 and layers > 2:
        step = (layers - 2) / (extra_pipelines * 2)
        for i in range(1, extra_pipelines + 1):
            pos = 1 + int(i * step)
            if pos >= layers - 1:
                pos = layers - 2
            pipeline_dist[pos] += 1
    
    return tuple(pipeline_dist)

@lru_cache(maxsize=512)
def _cached_su_area_formula(dwt, is_dwt_in_1=True):
    """缓存的SU面积公式计算"""
    if is_dwt_in_1:
        return CONST_COEFF_1 * (dwt - 1) + CONST_COEFF_2
    else:
        return CONST_COEFF_3 * (dwt - 1) + CONST_COEFF_4

class ModelContext:
    def __init__(self, su_in_db=None, model_su_out=None, model_mul=None):
        self.su_in_db = su_in_db
        self.model_su_out = model_su_out
        self.model_mul = model_mul
        # 预计算并缓存数组形式的数据以提高查询速度
        self.su_in_area_array = None
        self.sub_area_array = None
        if su_in_db is not None:
            self._precompute_arrays(su_in_db)
    
    def _precompute_arrays(self, su_in_db):
        """预计算数组以提高查询速度"""
        try:
            if 'Area' in su_in_db.columns:
                self.su_in_area_array = su_in_db['Area'].values
            # 如果有 Sub sheet，也预计算
            if hasattr(su_in_db, 'sheet_names') or 'Sub' in str(su_in_db):
                # 这里需要根据实际情况调整
                pass
        except:
            pass

context = ModelContext()

def init_context(su_in_db, model_su_out, model_mul=None):
    """初始化模型上下文"""
    context.su_in_db = su_in_db
    context.model_su_out = model_su_out
    context.model_mul = model_mul
    if su_in_db is not None:
        context._precompute_arrays(su_in_db)
    return context

@lru_cache(maxsize=1024)
def model_predict_wrapper_cached(X_tuple, model_id):
    """缓存的模型预测包装函数"""
    X_array = np.array([X_tuple])
    if model_id == 'su_out':
        return float(context.model_su_out.predict(X_array)[0])
    elif model_id == 'mul':
        return float(context.model_mul.predict(X_array)[0])
    return 0.0

def model_predict_wrapper(X_new, model_su_out):
    """将DataFrame转换为可哈希类型数据进行预测的包装函数"""
    # 优化：直接使用numpy数组而不是DataFrame
    X_array = np.array([X_new])
    return float(model_su_out.predict(X_array)[0])

@lru_cache(maxsize=512)
def get_su_area_cached(dwt, sign):
    """缓存的SU面积获取函数"""
    if sign != 1:
        return 0.0
    if context.su_in_area_array is not None and dwt <= len(context.su_in_area_array):
        return float(context.su_in_area_array[dwt - 1])
    elif context.su_in_db is not None:
        return float(context.su_in_db.loc[dwt - 1, 'Area'])
    return 0.0

# 2. 针对SU_in_db的查询包装函数
def get_su_area(dwt, sign, su_in_db):
    """获取SU面积的包装函数,转换为更简单的查询"""
    if sign == 1:
        return float(su_in_db.loc[dwt - 1, 'Area'])
    return 0.0

@lru_cache(maxsize=256)
def Est_Delay(DWT, N_CLK, if_rst_n=False):
    """优化的延迟估算函数，添加缓存"""
    if N_CLK == 0:
        return 1.12 * DWT
    
    if isinstance(if_rst_n, bool):
        multiplier = 6.72 if if_rst_n else 5.88
        return multiplier * DWT * N_CLK
    else:
        # 如果if_rst_n是列表，计算每个时钟的延迟
        y_pred = 0
        for rst_flag in if_rst_n:
            multiplier = 6.72 if rst_flag else 5.88
            y_pred += multiplier * DWT
        return y_pred

# DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines
def Est_ADD(model, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines= 0, if_rst_n=False):
    X = [DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, 0]
    X_config = adder_config_v2(*X)
    # 优化：直接使用numpy数组而不是DataFrame
    X_array = np.array([X_config])
    y_pred = model.predict(X_array)[0]
    
    # New PyTV
    y_pred += 1.12 * DWT_OUT * 2

    if isinstance(if_rst_n, bool):
        multiplier = 6.72 if if_rst_n else 5.88
        y_pred += multiplier * DWT_OUT * n_pipelines
    else:
        # 优化：向量化计算替代循环
        if n_pipelines > 0 and len(if_rst_n) >= n_pipelines:
            rst_flags = if_rst_n[:n_pipelines]
            y_pred += DWT_OUT * sum(6.72 if flag else 5.88 for flag in rst_flags)
            
    # print("ADD_area: ", y_pred)
    return y_pred
    
# DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines
def Est_SUB(model, Sub_db, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines= 0, if_rst_n=False):
    y_pred = Est_ADD(model, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines, if_rst_n)
    
    # 优化：预计算或使用更高效的查询方式
    if DWT_IN_2 < 20:
        # 优化：避免pandas的.loc操作，直接使用数组索引
        if hasattr(Sub_db, 'values') and len(Sub_db) > DWT_IN_2 - 1:
            SU_in_area = Sub_db.iloc[DWT_IN_2 - 1]['Area'] if 'Area' in Sub_db.columns else Sub_db.loc[DWT_IN_2 - 1, 'Area']
        else:
            SU_in_area = Sub_db.loc[DWT_IN_2 - 1, 'Area']
    else:
        # 预计算的线性公式，避免重复计算
        SU_in_area = 4.759999999999996 * (DWT_IN_2 - 1) - 0.2799999999999345
    y_pred += SU_in_area
    return y_pred

# SU_in_db, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines
def Est_MUL(Model_MUL, Model_SU_out, SU_in_db, DWT_IN_1, FRAC_IN_1, SIGN_IN_1, DWT_IN_2, FRAC_IN_2, SIGN_IN_2, DWT_OUT, FRAC_OUT, n_pipelines = 0, if_rst_n = False):
    # 预计算常用值
    MSB_out = DWT_OUT - FRAC_OUT - 1
    LSB_out = -FRAC_OUT
    MSB_mul = DWT_IN_1 + DWT_IN_2 - FRAC_IN_1 - FRAC_IN_2 - 1
    LSB_mul = -FRAC_IN_1 - FRAC_IN_2
    DWT_mul = max(0, min(MSB_out, MSB_mul) - LSB_mul + 1)  # 使用max避免负值

    # 优化SU_in_area计算，减少重复的数据库查询
    SU_in_area = 0
    if SIGN_IN_1 == 1:
        if DWT_IN_1 < 90:
            # 优化：如果有预计算数组，使用数组索引
            if hasattr(context, 'su_in_area_array') and context.su_in_area_array is not None and DWT_IN_1 <= len(context.su_in_area_array):
                SU_in_area = context.su_in_area_array[DWT_IN_1 - 1]
            else:
                SU_in_area = SU_in_db.loc[DWT_IN_1 - 1, 'Area']
        else:
            SU_in_area = 7.025313962352943 * (DWT_IN_1 - 1) - 7.608355686274602
    
    if SIGN_IN_2 == 1:
        if DWT_IN_2 < 90:
            # 注意：这里原代码中使用的是DWT_IN_1，应该是DWT_IN_2
            if hasattr(context, 'su_in_area_array') and context.su_in_area_array is not None and DWT_IN_2 <= len(context.su_in_area_array):
                SU_in_area += context.su_in_area_array[DWT_IN_2 - 1]
            else:
                SU_in_area += SU_in_db.loc[DWT_IN_2 - 1, 'Area']
        else:
            SU_in_area += 7.025313962352943 * (DWT_IN_2 - 1) - 7.608355686274602

    y_pred = SU_in_area
    
    # 优化DWT_mul计算逻辑
    if LSB_out - LSB_mul <= 1 and DWT_OUT <= 2:
        DWT_mul = min(MSB_out, MSB_mul) - LSB_mul + 1
    else:
        DWT_mul = DWT_IN_1 + DWT_IN_2
    
    # 优化模型预测，减少DataFrame创建
    X_mul = MUL_op(DWT_IN_1, DWT_IN_2, DWT_mul)
    X_mul_array = np.array([X_mul])
    y_pred += Model_MUL.predict(X_mul_array)[0]
    # print(Model_MUL.predict(X_mul_array)[0])
    
    # 第二个模型预测
    DWT_mul = min(MSB_out, MSB_mul) - LSB_mul + 1
    X_su = S2U_out(DWT_mul, 0, DWT_OUT, FRAC_OUT - FRAC_IN_1 - FRAC_IN_2, SIGN_IN_1, SIGN_IN_2)
    X_su_array = np.array([X_su])
    y_pred += Model_SU_out.predict(X_su_array)[0]
    
    # 优化管道延迟计算
    if isinstance(if_rst_n, bool):
        multiplier = 6.72 if if_rst_n else 5.88
        y_pred += multiplier * DWT_OUT * n_pipelines
    else:
        if n_pipelines > 0 and len(if_rst_n) >= n_pipelines:
            rst_flags = if_rst_n[:n_pipelines]
            y_pred += DWT_OUT * sum(6.72 if flag else 5.88 for flag in rst_flags)

    return y_pred
    
# Adder Tree - 优化版本
def Est_AT(model, N_INPUTS, QU_AT, QU_OUT, n_pipelines=0, if_rst_n=False):
    """优化的加法树估算函数"""
    #  QU_AT = [QU_IN_1, QU_OUT_L0, QU_OUT_L1, ...], same for FRAC_AT, SIGN_AT
    #  n_pipelines = [n_pipelines_L0, n_pipelines_L1, ...]
    # Do not append to the caller-owned list.  DataflowPE caches the layer list,
    # so mutating it here used to leak state into later estimator calls.
    QU_AT = [*QU_AT, QU_OUT]
    layers = math.ceil(math.log2(N_INPUTS))
    
    # 优化：预计算管道分布
    if isinstance(n_pipelines, int):
        base_pipelines = n_pipelines // layers
        extra_pipelines = n_pipelines % layers
        pipeline_dist = [base_pipelines] * layers
        
        # 分配额外的管道
        if extra_pipelines >= 2:
            pipeline_dist[0] += 1  # 首层 +1
            pipeline_dist[-1] += 1  # 尾层 +1
            extra_pipelines -= 2
        elif extra_pipelines == 1:
            pipeline_dist[0] += 1  # 如果只有 1 个，优先给首层
            extra_pipelines -= 1

        # 剩余的 extra_pipelines 均匀分配到中间层
        if extra_pipelines > 0 and layers > 2:
            step = (layers - 2) / (extra_pipelines * 2)  # 中间层步长（去掉首尾）
            for i in range(1, extra_pipelines + 1):
                pos = 1 + int(i * step)  # 从第 2 层（i=1）开始
                if pos >= layers - 1:  # 避免越界（不能覆盖尾层）
                    pos = layers - 2   # 放在倒数第二层
                pipeline_dist[pos] += 1
    else:
        pipeline_dist = n_pipelines
    
    # 标准化 if_rst_n 
    if not isinstance(if_rst_n, bool):
        if_rst_n = if_rst_n[0] if len(if_rst_n) > 0 else False
    
    # 预计算每层的加法器数量
    points = N_INPUTS
    cnt = []
    for l in range(layers):
        tmp = points // 2
        cnt.append(tmp)
        points = points - tmp
    
    # 计算总面积
    y_pred = 0
    for l in range(layers):
        if cnt[l] > 0:  # 只有当层中有加法器时才计算
            # 优化：减少函数调用
            add_area = Est_ADD(model, 
                             QU_AT[l].DWT, QU_AT[l].FRAC, QU_AT[l].IF_SIGNED, 
                             QU_AT[l].DWT, QU_AT[l].FRAC, QU_AT[l].IF_SIGNED, 
                             QU_AT[l+1].DWT, QU_AT[l+1].FRAC, 
                             0, if_rst_n) * cnt[l]
            
            # 添加管道开销
            add_area += QU_AT[l+1].DWT * pipeline_dist[l] * 5.88
            y_pred += add_area
    
    return y_pred

def Est_M2V(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, M:int, V:int, QU_M:QuType, QU_V:QuType, QU_M_V:QuType, QU_OUT:QuType, N_PIPELINES = 0):
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

    return y_pred

def Est_AddSubTree(ModelADD, Sub_db, QU_IN:QuType, QU_OUT:QuType, sign_flags, N_PIPELINES = 10, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N = False, N_INPUTS=4, CONFIG_MODE = "A"):
    """优化的加减法树估算函数"""
    area = 0
    n_layers = math.ceil(math.log2(N_INPUTS))

    QU_LAYERS: list[QuType] = [QuType() for _ in range(n_layers+1)]  
    
    if CONFIG_MODE == "A":
        if isinstance(IF_RST_N, bool):
            IF_RST_N = [IF_RST_N] * N_PIPELINES
        
        # 优化：预计算管道分布
        base_pipelines = N_PIPELINES // n_layers
        extra_pipelines = N_PIPELINES % n_layers
        N_PIPELINES = [base_pipelines if i < n_layers - extra_pipelines else base_pipelines + 1 for i in range(n_layers)]
        
        # 设置量化层属性
        QU_LAYERS[0].IF_SIGNED = QU_IN.IF_SIGNED
        for i in range(n_layers):
            QU_LAYERS[i].DWT = QU_IN.DWT
            QU_LAYERS[i].FRAC = QU_IN.FRAC
        QU_LAYERS[n_layers].DWT = QU_OUT.DWT
        QU_LAYERS[n_layers].FRAC = QU_OUT.FRAC
        
    elif CONFIG_MODE == "B":
        QU_LAYERS[0].IF_SIGNED = any(getattr(item, 'IF_SIGNED', False) for item in (QU_IN if isinstance(QU_IN, list) else [QU_IN]))
        for i in range(n_layers):
            if isinstance(QU_IN, list) and i < len(QU_IN):
                QU_LAYERS[i].DWT = QU_IN[i].DWT
                QU_LAYERS[i].FRAC = QU_IN[i].FRAC
        QU_LAYERS[n_layers].DWT = QU_OUT.DWT
        QU_LAYERS[n_layers].FRAC = QU_OUT.FRAC
        if isinstance(IF_RST_N, bool):
            IF_RST_N = [IF_RST_N] * sum(N_PIPELINES)

    n_operators = N_INPUTS

    for layer in range(n_layers):
        n_remainder = n_operators % 2
        n_adders = n_operators // 2
        n_operators = n_adders + n_remainder
        
        # 预计算固定的量化类型
        QU_IN_FIX = QuType()
        QU_OUT_FIX = QuType()
        QU_IN_FIX.DWT = QU_LAYERS[layer].DWT
        QU_IN_FIX.FRAC = QU_LAYERS[layer].FRAC
        QU_IN_FIX.IF_SIGNED = QU_LAYERS[0].IF_SIGNED
        QU_OUT_FIX.DWT = QU_LAYERS[layer+1].DWT
        QU_OUT_FIX.FRAC = QU_LAYERS[layer+1].FRAC
        QU_OUT_FIX.IF_SIGNED = QU_LAYERS[0].IF_SIGNED
        
        # 优化：批量处理加法器
        for adder in range(n_adders):
            sign_idx = adder * 2**(layer+1) + 2**layer
            if sign_idx < len(sign_flags):
                rst_slice = slice(sum(N_PIPELINES[:layer]), sum(N_PIPELINES[:layer+1]))
                
                if sign_flags[sign_idx] == 0:
                    area += Est_ADD(ModelADD, QU_IN_FIX.DWT, QU_IN_FIX.FRAC, QU_IN_FIX.IF_SIGNED, 
                                  QU_IN_FIX.DWT, QU_IN_FIX.FRAC, QU_IN_FIX.IF_SIGNED, 
                                  QU_OUT_FIX.DWT, QU_OUT_FIX.FRAC, N_PIPELINES[layer], 
                                  if_rst_n=IF_RST_N[rst_slice])
                else:
                    area += Est_SUB(ModelADD, Sub_db, QU_IN_FIX.DWT, QU_IN_FIX.FRAC, QU_IN_FIX.IF_SIGNED, 
                                  QU_IN_FIX.DWT, QU_IN_FIX.FRAC, QU_IN_FIX.IF_SIGNED, 
                                  QU_OUT_FIX.DWT, QU_OUT_FIX.FRAC, N_PIPELINES[layer], 
                                  if_rst_n=IF_RST_N[rst_slice])
        
        # 处理余数节点的管道延迟
        if n_remainder == 1 and N_PIPELINES[layer] > 0:
            rst_slice = slice(sum(N_PIPELINES[:layer]), sum(N_PIPELINES[:layer+1]))
            rst_flags = IF_RST_N[rst_slice]
            
            if isinstance(rst_flags, bool) or (len(rst_flags) == 1 and isinstance(rst_flags[0], bool)):
                multiplier = 6.72 if (rst_flags if isinstance(rst_flags, bool) else rst_flags[0]) else 5.88
                area += multiplier * QU_OUT.DWT * N_PIPELINES[layer]
            else:
                area += QU_OUT.DWT * N_PIPELINES[layer] * sum(6.72 if flag else 5.88 for flag in rst_flags)
    
    return area


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

    add = Est_ADD(Model_ADD, 14, 0, 0, 4, 0, 0, 4, 0, 0)
    print("add: ", add)
    sub = Est_SUB(Model_ADD, Sub_db, 4, 0, 0, 14, 0, 0, 9, 0, 0)
    print("sub: ", sub)
    
    # print( Est_MUL(Model_MUL, Model_SU_out, SU_in_db, 3, 0, 0, 3, 0, 0, 3, 0, n_pipelines = 1, if_rst_n = False))
    
    end = time.time()
    print("Time taken: ", end - start)
