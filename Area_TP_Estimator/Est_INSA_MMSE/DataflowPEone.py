import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

from PyTU import QuMode, OfMode, QuType
from EstModule import Est_ADD, Est_SUB, Est_MUL, Est_Delay
from PEinterone import Est_PEinterone
from PEinter import Est_PEinter
import math 
import joblib
import warnings
import pandas as pd
import os
import joblib
import math
import time
import warnings
import numpy as np
import re
from functools import lru_cache

# 预计算常量，避免重复计算
_QU_TEMPLATE_CACHE = {}

def _create_qu_dict_optimized(QU_IN_H, QU_IN_y, QU_IN_a, QU_IN_D, QU_OUT_ymf, QU_OUT_x1, QU_OUT_b2, QU_OUT_d2, QU_OUT_Dx1, QU_OUT_x2, QU_OUT_b3, QU_OUT_d3, QU_OUT_Dx2, QU_OUT_x3, QU_OUT_b4, QU_OUT_d4, QU_OUT_Dx3, QU_OUT_x4):
    """优化的QU字典创建，减少重复赋值"""
    QU = {}
    
    # 批量赋值相同类型的QU
    h_keys = ['HT1', 'H1', 'HT2', 'H2', 'HT3', 'H3', 'HT4']
    for key in h_keys:
        QU[key] = QU_IN_H
    
    d_keys = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7']
    for key in d_keys:
        QU[key] = QU_IN_D
    
    # 单独赋值的键值对
    single_assignments = {
        'y': QU_IN_y,
        'a': QU_IN_a,
        'ymf': QU_OUT_ymf,
        'x1': QU_OUT_x1,
        'b2': QU_OUT_b2,
        'd2': QU_OUT_d2,
        'Dx1': QU_OUT_Dx1,
        'x2': QU_OUT_x2,
        'b3': QU_OUT_b3,
        'd3': QU_OUT_d3,
        'Dx2': QU_OUT_Dx2,
        'x3': QU_OUT_x3,
        'b4': QU_OUT_b4,
        'd4': QU_OUT_d4,
        'Dx3': QU_OUT_Dx3,
        'x4': QU_OUT_x4
    }
    QU.update(single_assignments)
    
    return QU

def ModulelNSA_MMSE(Tx, Rx, AdderTree_PIPELINES, QU_IN_H:QuType, QU_IN_y:QuType, QU_IN_a:QuType, QU_IN_D:QuType, QU_OUT_ymf:QuType, QU_OUT_x1:QuType, QU_OUT_b2:QuType, QU_OUT_d2:QuType, QU_OUT_Dx1:QuType,QU_OUT_x2:QuType,QU_OUT_b3:QuType,QU_OUT_d3:QuType,QU_OUT_Dx2:QuType,QU_OUT_x3:QuType,QU_OUT_b4:QuType,QU_OUT_d4:QuType,QU_OUT_Dx3:QuType,QU_OUT_x4:QuType,iterations,QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=False):
    # 使用优化的字典创建函数
    return _create_qu_dict_optimized(
        QU_IN_H, QU_IN_y, QU_IN_a, QU_IN_D, QU_OUT_ymf, QU_OUT_x1, QU_OUT_b2, 
        QU_OUT_d2, QU_OUT_Dx1, QU_OUT_x2, QU_OUT_b3, QU_OUT_d3, QU_OUT_Dx2, 
        QU_OUT_x3, QU_OUT_b4, QU_OUT_d4, QU_OUT_Dx3, QU_OUT_x4
    )

def Est_DataflowPEone(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, QU:QuType, unique_pe_addresses, edgea, starta, edgec, Eq, code_line, IF_RST_N=False):
    area = 0
    
    # 优化：预处理IF_RST_N，避免重复的类型检查
    if isinstance(IF_RST_N, bool):
        IF_RST_N_val = IF_RST_N
        IF_RST_N = [IF_RST_N] * len(unique_pe_addresses) * 4
    else:
        IF_RST_N_val = IF_RST_N[0]
    
    # 优化：预计算Eq的长度，避免重复计算
    eq_len = len(Eq)
    eq_range = range(1, eq_len)
    
    # 优化：预计算QU字典的查找，避免重复字典访问
    qu_dwt_cache = {}
    for eq_id in eq_range:
        eq_key = Eq[eq_id]
        if eq_key not in qu_dwt_cache:
            qu_dwt_cache[eq_key] = QU[eq_key].DWT
    
    # 1. 批量处理edge PEs的延迟计算
    if edgea:
        # 预计算延迟值，避免重复调用Est_Delay
        delay_cache = {}
        for eq_id in eq_range:
            eq_key = Eq[eq_id]
            dwt = qu_dwt_cache[eq_key]
            if dwt not in delay_cache:
                # 假设daa为0时的基础延迟
                delay_cache[dwt] = {}
        
        total_delay = 0
        for pe_address in edgea:
            i, j = pe_address
            for eq_id in eq_range:
                eq_key = Eq[eq_id]
                dwt = qu_dwt_cache[eq_key]
                daa = starta[eq_id][i, j]
                
                # 优化：缓存相同参数的延迟计算
                cache_key = (dwt, daa)
                if cache_key not in delay_cache:
                    delay_cache[cache_key] = Est_Delay(DWT=dwt, N_CLK=daa, if_rst_n=IF_RST_N_val)
                
                total_delay += delay_cache[cache_key]
        
        area += total_delay
    
    # 2. 优化PE实例化 - 预计算相同的PE面积
    if unique_pe_addresses:
        # 预计算PE面积，因为所有PE使用相同的参数
        pe_area = Est_PEinterone(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, 
                                QU=QU, N_PIPELINES=3, code_line=code_line, 
                                Eq=Eq, IF_RST_N=IF_RST_N_val)
        
        # 批量计算所有PE的面积
        area += pe_area * len(unique_pe_addresses)
    
    return area

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    path = "."
    SU_in_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='SU_in', header = 0)
    Sub_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='Sub', header = 0)
    ModelAdd = joblib.load(path +'/model/ADD_area.pkl')
    Model_MUL = joblib.load(path +'/model/pure_MUL_area.pkl')
    Model_SU_out = joblib.load(path +'/model/SU_out_FxP_area.pkl')
    su_in_db_id = "ctx_su_in_db"
    model_su_out_id = "ctx_model_su_out"
    
    start = time.time()
    
    QU = ModulelNSA_MMSE(Tx=4, Rx=32, AdderTree_PIPELINES=1,QU_IN_H= QuType(9,8,True), QU_IN_y= QuType(9,4,True), QU_IN_a= QuType(4,4,True), QU_IN_D= QuType(5,4,True), QU_OUT_ymf= QuType(9,4,True), QU_OUT_x1= QuType(9,4,True), QU_OUT_b2= QuType(9,4,True), QU_OUT_d2= QuType(9,4,True), QU_OUT_Dx1= QuType(9,4,True),QU_OUT_x2= QuType(9,4,True),QU_OUT_b3= QuType(9,4,True),QU_OUT_d3= QuType(9,4,True),QU_OUT_Dx2= QuType(9,4,True),QU_OUT_x3= QuType(9,4,True),QU_OUT_b4= QuType(9,4,True),QU_OUT_d4= QuType(9,4,True),QU_OUT_Dx3= QuType(9,4,True),QU_OUT_x4= QuType(9,4,True),iterations=2,QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=True) 
    
    a = Est_DataflowPEone(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, QU=QU, unique_pe_addresses=[(0, 0)], edgea=[(0, 0)], starta=[{(0, 0): 0}, {(0, 0): 13}, {(0, 0): 5}, {(0, 0): 0}, {(0, 0): 0}, {(0, 0): 0}, {(0, 0): 1}], edgec=[(0, 0)], Eq=['x3', 'x1', 'x2', 'a', 'Dx2', 'D5', 'd3'], code_line="x3[i] = x1[i] + x2[i] - a*Dx2[i] + D5[i]*d3[i]", IF_RST_N=False)
    print("Estimated area:", a)
    
    end = time.time()
    print("Time taken: ", end - start)



