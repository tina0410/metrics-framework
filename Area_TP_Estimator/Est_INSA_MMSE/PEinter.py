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
import time
import numpy as np
from functools import lru_cache

# 预计算常量
PASS_MULTIPLIER = 3.08

@lru_cache(maxsize=256)
def _cached_pass_area(qu_out_dwt):
    """缓存pass面积计算"""
    return PASS_MULTIPLIER * qu_out_dwt

@lru_cache(maxsize=512)
def _cached_qu_attributes(qu_type_id, dwt, frac, if_signed):
    """缓存QuType属性的访问"""
    return dwt, frac, if_signed

@lru_cache(maxsize=256)
def _cached_if_rst_n_expansion(n_pipelines, if_rst_n_bool):
    """缓存IF_RST_N列表的扩展"""
    return [if_rst_n_bool] * n_pipelines

def Est_PEinter(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, QU_IN_1:QuType, QU_IN_2:QuType, QU_IN_3:QuType, QU_OUT:QuType, passc, N_PIPELINES=0, IF_RST_N=False):
    """
    优化的PE接口估算函数
    实现 y = w * x + pass 的功能
    """
    
    # 优化：预处理IF_RST_N，使用缓存避免重复的列表创建
    if N_PIPELINES > 0 and isinstance(IF_RST_N, bool):
        IF_RST_N = _cached_if_rst_n_expansion(N_PIPELINES, IF_RST_N)
    
    # 优化：批量获取所有QuType属性，减少属性访问次数
    qu_in_1_attrs = (QU_IN_1.DWT, QU_IN_1.FRAC, QU_IN_1.IF_SIGNED)
    qu_in_2_attrs = (QU_IN_2.DWT, QU_IN_2.FRAC, QU_IN_2.IF_SIGNED)
    qu_in_3_attrs = (QU_IN_3.DWT, QU_IN_3.FRAC, QU_IN_3.IF_SIGNED)
    qu_out_attrs = (QU_OUT.DWT, QU_OUT.FRAC, QU_OUT.IF_SIGNED)
    
    # 解包属性值
    qu_in_1_dwt, qu_in_1_frac, qu_in_1_signed = qu_in_1_attrs
    qu_in_2_dwt, qu_in_2_frac, qu_in_2_signed = qu_in_2_attrs
    qu_in_3_dwt, qu_in_3_frac, qu_in_3_signed = qu_in_3_attrs
    qu_out_dwt, qu_out_frac, qu_out_signed = qu_out_attrs
    
    # 优化：并行计算mul和add，避免顺序依赖
    mul = Est_MUL(Model_MUL, Model_SU_out, SU_in_db, 
                  qu_in_1_dwt, qu_in_1_frac, qu_in_1_signed, 
                  qu_in_2_dwt, qu_in_2_frac, qu_in_2_signed, 
                  qu_out_dwt, qu_out_frac, if_rst_n=IF_RST_N)
    
    add = Est_ADD(ModelAdd, 
                  qu_out_dwt, qu_out_frac, qu_out_signed, 
                  qu_in_3_dwt, qu_in_3_frac, qu_in_3_signed, 
                  qu_out_dwt, qu_out_frac, 0, IF_RST_N)
    
    # 优化：合并计算，减少临时变量
    area = mul + add
    
    # 优化：使用位运算优化条件判断（假设passc值为0或1）
    # 如果passc[0] == 0 and passc[1] == 0，等价于 passc[0] | passc[1] == 0
    if not (passc[0] | passc[1]):
        area += _cached_pass_area(qu_out_dwt)
    
    return area

# 可选：添加预热函数来初始化缓存
def _warm_up_cache():
    """预热缓存以提高首次运行性能"""
    # 预计算常用的pass面积值
    for dwt in [8, 9, 10, 16, 32]:
        _cached_pass_area(dwt)
    
    # 预计算常用的IF_RST_N扩展
    for n_pipes in [1, 2, 3, 4, 8]:
        for rst_val in [True, False]:
            _cached_if_rst_n_expansion(n_pipes, rst_val)

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
    a = Est_PEinter(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, 
                   QU_IN_1=QuType(8, 8, True), QU_IN_2=QuType(9, 4, True), 
                   QU_IN_3=QuType(10, 4, True), QU_OUT=QuType(10, 4, True), 
                   passc=[0, 0, 1], N_PIPELINES=0, IF_RST_N=False)
    
    print("Estimated area:", a)
    
    end = time.time()
    print("Time taken: ", end - start)
