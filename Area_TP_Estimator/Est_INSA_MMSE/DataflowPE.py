import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

from PyTU import QuMode, OfMode, QuType
from EstModule import Est_ADD, Est_SUB, Est_MUL, Est_Delay, Est_AT
from AddSubTree import Est_AddSubTree
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
import re
from PEinter import Est_PEinter
from functools import lru_cache

# 预计算常量
_cached_log2_values = {}
_cached_qu_layers = {}

@lru_cache(maxsize=256)
def _cached_ceil_log2(n):
    """缓存的 ceil(log2(n)) 计算"""
    if n <= 1:
        return 0
    return math.ceil(math.log2(n))

@lru_cache(maxsize=512)
def _get_qu_layers_cache_key(n_layers, dwt, frac, if_signed):
    """生成QU_LAYERS的缓存键"""
    return (n_layers, dwt, frac, if_signed)

def _create_qu_layers_optimized(n_layers, qu_out):
    """优化的QU_LAYERS创建"""
    cache_key = _get_qu_layers_cache_key(n_layers, qu_out.DWT, qu_out.FRAC, qu_out.IF_SIGNED)
    if cache_key in _cached_qu_layers:
        return _cached_qu_layers[cache_key]
    
    qu_layers = [QuType() for _ in range(n_layers)]
    qu_layers[0].DWT = qu_out.DWT
    qu_layers[0].FRAC = qu_out.FRAC
    qu_layers[0].IF_SIGNED = qu_out.IF_SIGNED
    
    for i in range(1, n_layers):
        qu_layers[i].DWT = qu_out.DWT + 1
        qu_layers[i].FRAC = qu_out.FRAC
        qu_layers[i].IF_SIGNED = qu_out.IF_SIGNED
    
    _cached_qu_layers[cache_key] = qu_layers
    return qu_layers

def Est_DataflowPE(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, QU_IN_A:QuType, QU_IN_B:QuType, QU_OUT:QuType, unique_pe_addresses, passa, passb, passc, edgea, starta, edgeb, startb, edgec, In_C, K, AdderTree_PIPELINES, IF_RST_N=False):
    area = 0
    
    # 预计算常用值
    pia, pja, da = passa[0], passa[1], passa[2]
    pib, pjb, db = passb[0], passb[1], passb[2]
    pic, pjc, dc = passc[0], passc[1], passc[2]
    
    # 优化：预计算unique_pe_addresses的长度和常用值
    num_unique_pes = len(unique_pe_addresses)
    
    # 优化：预处理IF_RST_N
    if isinstance(IF_RST_N, bool):
        IF_RST_N = [IF_RST_N] * num_unique_pes * 4
    
    # 优化：预计算常用的Est_Delay参数
    dwt_a = QU_IN_A.DWT
    dwt_b = QU_IN_B.DWT
    dwt_out = QU_OUT.DWT
    
    # 1. 批量处理Input A的边缘PEs
    if edgea:
        for pe_address in edgea:
            i, j = pe_address
            daa = starta[i, j]
            area += Est_Delay(DWT=dwt_a, N_CLK=daa, if_rst_n=IF_RST_N[0])

    # 2. 批量处理Input B的边缘PEs
    if edgeb:
        for pe_address in edgeb:
            i, j = pe_address
            dbb = startb[i, j]
            area += Est_Delay(DWT=dwt_b, N_CLK=dbb, if_rst_n=IF_RST_N[1])

    # 3. 优化Output edge PEs处理
    if dc == 0:  # passc[2] == 0
        if edgec:
            # 预计算QU_LAYERS以避免重复创建
            n_layers = _cached_ceil_log2(K)
            qu_layers = _create_qu_layers_optimized(n_layers, QU_OUT)
            
            # 预计算Est_AT结果，因为对所有edge PEs都是相同的
            # Match the RTL generator, which drives the adder tree with
            # IF_RST_N[1].  Uniform boolean reset settings are unaffected, but
            # per-stage reset lists now produce the same area on both sides.
            at_area = Est_AT(ModelAdd, K, qu_layers, QU_OUT, AdderTree_PIPELINES, if_rst_n=IF_RST_N[1])
            area += at_area * len(edgec)

    # 4. 优化PE实例化
    pic_zero = pic == 0
    pjc_zero = pjc == 0
    dc_zero = dc == 0
    
    if pic_zero and pjc_zero:
        # 预计算PE面积，因为对所有PE都是相同的
        pe_area = Est_PEinter(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, 
                             QU_IN_1=QU_IN_A, QU_IN_2=QU_IN_B, QU_IN_3=QU_OUT, 
                             QU_OUT=QU_OUT, passc=passc, N_PIPELINES=0, IF_RST_N=False)
        area += pe_area * num_unique_pes
        
    elif dc_zero:
        # 预计算MUL面积
        mul_area = Est_MUL(Model_MUL, Model_SU_out, SU_in_db, 
                          dwt_a, QU_IN_A.FRAC, QU_IN_A.IF_SIGNED, 
                          dwt_b, QU_IN_B.FRAC, QU_IN_B.IF_SIGNED, 
                          dwt_out, QU_OUT.FRAC, n_pipelines=0, if_rst_n=False)
        area += mul_area * num_unique_pes
        
    else:
        # 优化：预计算面积值，减少重复计算
        mul_area = Est_MUL(Model_MUL, Model_SU_out, SU_in_db, 
                          dwt_a, QU_IN_A.FRAC, QU_IN_A.IF_SIGNED, 
                          dwt_b, QU_IN_B.FRAC, QU_IN_B.IF_SIGNED, 
                          dwt_out, QU_OUT.FRAC, N_PIPELINES=0, IF_RST_N=False)
        
        pe_area = Est_PEinter(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, 
                             QU_IN_1=QU_IN_A, QU_IN_2=QU_IN_B, QU_IN_3=QU_OUT, 
                             QU_OUT=QU_OUT, passc=passc, N_PIPELINES=0, IF_RST_N=False)
        
        # 优化：将In_C转换为set以提高查找效率
        in_c_set = set(In_C) if In_C else set()
        
        # 批量处理PEs
        mul_count = 0
        pe_count = 0
        
        for pe in unique_pe_addresses:
            if pe in in_c_set:
                mul_count += 1
            else:
                pe_count += 1
        
        area += mul_area * mul_count + pe_area * pe_count

    # 5. 优化延迟计算 - 批量处理相同的延迟
    # 预计算延迟值
    delay_a = Est_Delay(DWT=dwt_a, N_CLK=da, if_rst_n=IF_RST_N[0])
    delay_b = Est_Delay(DWT=dwt_b, N_CLK=db, if_rst_n=IF_RST_N[0])
    delay_c = Est_Delay(DWT=dwt_out, N_CLK=dc, if_rst_n=IF_RST_N[0])
    
    # 批量添加延迟（每个PE都有相同的延迟）
    total_delay = (delay_a + delay_b + delay_c) * num_unique_pes
    area += total_delay
    
    return area

# 可选：添加预热函数来初始化缓存
def _warm_up_cache():
    """预热缓存以提高首次运行性能"""
    # 预计算常用的log2值
    for i in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
        _cached_ceil_log2(i)

# 在模块加载时预热缓存
_warm_up_cache()

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    path = "."
    SU_in_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='SU_in', header = 0)
    Sub_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='Sub', header = 0)
    ModelAdd = joblib.load(path +'/model/ADD_area.pkl')
    Model_MUL = joblib.load(path +'/model/pure_MUL_area.pkl')
    Model_SU_out = joblib.load(path +'/model/SU_out_FxP_area.pkl')
    
    start = time.time()   
    a = Est_DataflowPE(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, QU_IN_A = QuType(9, 8, True), QU_IN_B = QuType(9, 4, True), QU_OUT = QuType(9, 4, True), unique_pe_addresses = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (0, 12), (0, 13), (0, 14), (0, 15), (0, 16), (0, 17), (0, 18), (0, 19), (0, 20), (0, 21), (0, 22), (0, 23), (0, 24), (0, 25), (0, 26), (0, 27), (0, 28), (0, 29), (0, 30), (0, 31), (0, 32), (0, 33), (0, 34), (0, 35), (0, 36), (0, 37), (0, 38), (0, 39), (0, 40), (0, 41), (0, 42), (0, 43), (0, 44), (0, 45), (0, 46), (0, 47), (0, 48), (0, 49), (0, 50), (0, 51), (0, 52), (0, 53), (0, 54), (0, 55), (0, 56), (0, 57), (0, 58), (0, 59), (0, 60), (0, 61), (0, 62), (0, 63)], passa = [1,0,0], passb = [0,1,0], passc = [0,0,1], edgea = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (0, 12), (0, 13), (0, 14), (0, 15), (0, 16), (0, 17), (0, 18), (0, 19), (0, 20), (0, 21), (0, 22), (0, 23), (0, 24), (0, 25), (0, 26), (0, 27), (0, 28), (0, 29), (0, 30), (0, 31), (0, 32), (0, 33), (0, 34), (0, 35), (0, 36), (0, 37), (0, 38), (0, 39), (0, 40), (0, 41), (0, 42), (0, 43), (0, 44), (0, 45), (0, 46), (0, 47), (0, 48), (0, 49), (0, 50), (0, 51), (0, 52), (0, 53), (0, 54), (0, 55), (0, 56), (0, 57), (0, 58), (0, 59), (0, 60), (0, 61), (0, 62), (0, 63)], starta = {(0, 0): 0, (0, 1): 0, (0, 2): 0, (0, 3): 0, (0, 4): 0, (0, 5): 0, (0, 6): 0, (0, 7): 0, (0, 8): 0, (0, 9): 0, (0, 10): 0, (0, 11): 0, (0, 12): 0, (0, 13): 0, (0, 14): 0, (0, 15): 0, (0, 16): 0, (0, 17): 0, (0, 18): 0, (0, 19): 0, (0, 20): 0, (0, 21): 0, (0, 22): 0, (0, 23): 0, (0, 24): 0, (0, 25): 0, (0, 26): 0, (0, 27): 0, (0, 28): 0, (0, 29): 0, (0, 30): 0, (0, 31): 0, (0, 32): 0, (0, 33): 0, (0, 34): 0, (0, 35): 0, (0, 36): 0, (0, 37): 0, (0, 38): 0, (0, 39): 0, (0, 40): 0, (0, 41): 0, (0, 42): 0, (0, 43): 0, (0, 44): 0, (0, 45): 0, (0, 46): 0, (0, 47): 0, (0, 48): 0, (0, 49): 0, (0, 50): 0, (0, 51): 0, (0, 52): 0, (0, 53): 0, (0, 54): 0, (0, 55): 0, (0, 56): 0, (0, 57): 0, (0, 58): 0, (0, 59): 0, (0, 60): 0, (0, 61): 0, (0, 62): 0, (0, 63): 0}, edgeb = [(0, 0)], startb = {(0, 0): 0}, edgec = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (0, 12), (0, 13), (0, 14), (0, 15), (0, 16), (0, 17), (0, 18), (0, 19), (0, 20), (0, 21), (0, 22), (0, 23), (0, 24), (0, 25), (0, 26), (0, 27), (0, 28), (0, 29), (0, 30), (0, 31), (0, 32), (0, 33), (0, 34), (0, 35), (0, 36), (0, 37), (0, 38), (0, 39), (0, 40), (0, 41), (0, 42), (0, 43), (0, 44), (0, 45), (0, 46), (0, 47), (0, 48), (0, 49), (0, 50), (0, 51), (0, 52), (0, 53), (0, 54), (0, 55), (0, 56), (0, 57), (0, 58), (0, 59), (0, 60), (0, 61), (0, 62), (0, 63)], In_C = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (0, 12), (0, 13), (0, 14), (0, 15), (0, 16), (0, 17), (0, 18), (0, 19), (0, 20), (0, 21), (0, 22), (0, 23), (0, 24), (0, 25), (0, 26), (0, 27), (0, 28), (0, 29), (0, 30), (0, 31), (0, 32), (0, 33), (0, 34), (0, 35), (0, 36), (0, 37), (0, 38), (0, 39), (0, 40), (0, 41), (0, 42), (0, 43), (0, 44), (0, 45), (0, 46), (0, 47), (0, 48), (0, 49), (0, 50), (0, 51), (0, 52), (0, 53), (0, 54), (0, 55), (0, 56), (0, 57), (0, 58), (0, 59), (0, 60), (0, 61), (0, 62), (0, 63)], K = 4, AdderTree_PIPELINES = 1, IF_RST_N = False)
    print("Estimated area:", a)
    
    end = time.time()
    print("Time taken: ", end - start)
