import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

from PyTU import QuMode, OfMode, QuType
from EstModule import Est_ADD, Est_SUB, Est_MUL
import math 
import joblib
import warnings
import pandas as pd
import os
import joblib
from KeyParam import adder_config_v2, MUL_op, S2U_out
import math
import time
import warnings
import numpy as np
from functools import lru_cache

# 预计算常量
CONST_6_72 = 6.72
CONST_5_88 = 5.88

@lru_cache(maxsize=128)
def _cached_ceil_log2(n):
    """缓存的 ceil(log2(n)) 计算"""
    if n <= 1:
        return 0
    return math.ceil(math.log2(n))

@lru_cache(maxsize=256)
def _cached_pipeline_distribution(n_pipelines, n_layers):
    """缓存的管道分布计算"""
    base_pipelines = n_pipelines // n_layers
    extra_pipelines = n_pipelines % n_layers
    return tuple([base_pipelines if i < n_layers - extra_pipelines else base_pipelines + 1 
                  for i in range(n_layers)])

@lru_cache(maxsize=512)
def _cached_qu_layers_key(n_layers, qu_in_params, qu_out_params, config_mode):
    """生成QU_LAYERS的缓存键"""
    return (n_layers, qu_in_params, qu_out_params, config_mode)

def _create_qu_layers_optimized(n_layers, QU_IN, QU_OUT, CONFIG_MODE):
    """优化的QU_LAYERS创建"""
    qu_layers = [QuType() for _ in range(n_layers + 1)]
    
    if CONFIG_MODE == "A":
        # Mode A配置
        qu_layers[0].IF_SIGNED = QU_IN.IF_SIGNED
        for i in range(n_layers):
            qu_layers[i].DWT = QU_IN.DWT
            qu_layers[i].FRAC = QU_IN.FRAC
        qu_layers[n_layers].DWT = QU_OUT.DWT
        qu_layers[n_layers].FRAC = QU_OUT.FRAC
    else:  # CONFIG_MODE == "B"
        qu_layers[0].IF_SIGNED = any(item.IF_SIGNED for item in QU_IN)
        for i in range(n_layers):
            qu_layers[i].DWT = QU_IN[i].DWT
            qu_layers[i].FRAC = QU_IN[i].FRAC
        qu_layers[n_layers].DWT = QU_OUT.DWT
        qu_layers[n_layers].FRAC = QU_OUT.FRAC
    
    return qu_layers

def _preprocess_if_rst_n(IF_RST_N, N_PIPELINES, CONFIG_MODE):
    """预处理IF_RST_N参数"""
    if isinstance(IF_RST_N, bool):
        if CONFIG_MODE == "A":
            return [IF_RST_N] * N_PIPELINES
        else:  # CONFIG_MODE == "B"
            return [IF_RST_N] * sum(N_PIPELINES)
    return IF_RST_N

def _calculate_delay_optimized(QU_OUT_DWT, N_PIPELINES_layer, IF_RST_N_slice):
    """优化的延迟计算"""
    if N_PIPELINES_layer == 0:
        return 0
    
    if isinstance(IF_RST_N_slice, bool):
        multiplier = CONST_6_72 if IF_RST_N_slice else CONST_5_88
        return multiplier * QU_OUT_DWT * N_PIPELINES_layer
    else:
        # 向量化计算
        total_delay = 0
        for rst_flag in IF_RST_N_slice:
            multiplier = CONST_6_72 if rst_flag else CONST_5_88
            total_delay += multiplier * QU_OUT_DWT * N_PIPELINES_layer
        return total_delay

# Explain Add_Tree module here
def Est_AddSubTree(ModelADD, Sub_db, QU_IN:QuType, QU_OUT:QuType, sign_flags, N_PIPELINES = 10, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N = False, N_INPUTS=4, CONFIG_MODE = "A"):
    area = 0
    
    # 优化：缓存ceil(log2)计算
    n_layers = _cached_ceil_log2(N_INPUTS)
    
    # 优化：预处理IF_RST_N
    IF_RST_N = _preprocess_if_rst_n(IF_RST_N, N_PIPELINES, CONFIG_MODE)
    
    # 优化：预处理N_PIPELINES for CONFIG_MODE A
    if CONFIG_MODE == "A":
        N_PIPELINES = list(_cached_pipeline_distribution(N_PIPELINES, n_layers))
    
    # 优化：创建QU_LAYERS
    QU_LAYERS = _create_qu_layers_optimized(n_layers, QU_IN, QU_OUT, CONFIG_MODE)
    
    # 预计算常用值
    QU_OUT_DWT = QU_OUT.DWT
    base_if_signed = QU_LAYERS[0].IF_SIGNED
    
    # 预计算N_PIPELINES的累积和以避免重复计算
    if CONFIG_MODE == "B":
        pipeline_cumsum = [0]
        for i, n_pipe in enumerate(N_PIPELINES):
            pipeline_cumsum.append(pipeline_cumsum[-1] + n_pipe)
    
    n_operators = N_INPUTS
    
    for layer in range(n_layers):
        n_remainder = n_operators % 2
        n_adders = n_operators // 2
        n_operators = n_adders + n_remainder
        
        # 优化：预计算固定的QU类型参数
        qu_in_dwt = QU_LAYERS[layer].DWT
        qu_in_frac = QU_LAYERS[layer].FRAC
        qu_out_dwt = QU_LAYERS[layer+1].DWT
        qu_out_frac = QU_LAYERS[layer+1].FRAC
        
        # 优化：预计算管道参数
        n_pipelines_layer = N_PIPELINES[layer]
        
        if CONFIG_MODE == "A":
            if_rst_n_slice = IF_RST_N
        else:  # CONFIG_MODE == "B"
            if_rst_n_slice = IF_RST_N[pipeline_cumsum[layer]:pipeline_cumsum[layer+1]]
        
        # 预计算sign_flag索引的基数
        sign_base_index = 2**(layer+1)
        sign_offset = 2**layer
        
        # 批量处理加法器
        for adder in range(n_adders):
            sign_index = adder * sign_base_index + sign_offset
            
            if sign_flags[sign_index] == 0:
                area += Est_ADD(ModelADD, qu_in_dwt, qu_in_frac, base_if_signed, 
                               qu_in_dwt, qu_in_frac, base_if_signed, 
                               qu_out_dwt, qu_out_frac, n_pipelines_layer, 
                               if_rst_n=if_rst_n_slice)
            else:
                area += Est_SUB(ModelADD, Sub_db, qu_in_dwt, qu_in_frac, base_if_signed,
                               qu_in_dwt, qu_in_frac, base_if_signed,
                               qu_out_dwt, qu_out_frac, n_pipelines_layer,
                               if_rst_n=if_rst_n_slice)
        
        # 优化：处理余数情况
        if n_remainder == 1:
            area += _calculate_delay_optimized(QU_OUT_DWT, n_pipelines_layer, if_rst_n_slice)
    
    return area

if __name__ == "__main__":
#   os.chdir(os.path.dirname(__file__))
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
    
    print(Est_AddSubTree(Model_ADD, Sub_db, QU_IN = [QuType(10,2,True),QuType(8,2,True)], QU_OUT = QuType(6,2,True), N_PIPELINES = [2,3], CONFIG_MODE = "B", sign_flags = [0,0,1,0], N_INPUTS=4, IF_RST_N = False))
    
    end = time.time()
    print("Time taken: ", end - start)