import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

from PyTU import QuMode, OfMode, QuType
from DataflowPEone import Est_DataflowPEone
from DataflowPE import Est_DataflowPE
import pandas as pd
from KeyParam import adder_config_v2, MUL_op, S2U_out
import numpy as np
import re

from collections import OrderedDict
from enum import Enum
import math 
import numpy as np
from typing import List, Set
import Getloop
import GetIS
import copy
from functools import lru_cache

# 缓存字典，避免重复计算
_cached_min_values = {}
_cached_first_occurrences = {}

@lru_cache(maxsize=256)
def _cached_find_first_occurrence(eq_tuple, target):
    """缓存的首次出现查找"""
    for i, sublist in enumerate(eq_tuple):
        for j, item in enumerate(sublist):
            if item == target:
                return (i, j)
    return None

def find_first_occurrence(lst, target):
    # 转换为可哈希的tuple以便缓存
    eq_tuple = tuple(tuple(sublist) if isinstance(sublist, list) else sublist for sublist in lst)
    return _cached_find_first_occurrence(eq_tuple, target)

def _get_min_start_time_c_cached(start_time_C, tnn):
    """缓存start_time_C的最小值计算"""
    # Temporary object ids can be reused after a sample is released, causing a
    # later sample to read another configuration's minimum.  Key the cache by
    # immutable content instead.
    cache_key = (
        tnn,
        tuple(sorted((tuple(key), int(value)) for key, value in start_time_C[tnn].items())),
    )
    if cache_key not in _cached_min_values:
        _cached_min_values[cache_key] = min(start_time_C[tnn].values())
    return _cached_min_values[cache_key]

def _batch_update_start_times(start_dict, min_value, keys=None):
    """批量更新start时间，避免重复遍历"""
    if keys is None:
        keys = start_dict.keys()
    
    for key in keys:
        start_dict[key] = np.int64(start_dict[key] + min_value)

def _create_start_array_optimized(eq_tn_len, start_time_a_tn):
    """优化的start数组创建"""
    start = []
    for si in range(eq_tn_len):
        start.append(copy.deepcopy(start_time_a_tn))
    return start

@lru_cache(maxsize=128)
def extract_constants_from_list(code_list_tuple: tuple) -> tuple:
    """
    从元组中提取所有方程中的常数（不带[i]的变量），去重后返回元组。
    使用缓存优化重复调用。
    """
    constants = []
    seen = set()  # 用于去重
    
    for item in code_list_tuple:
        if not isinstance(item, str):
            continue  # 跳过非字符串元素
            
        # 提取等号右边的表达式
        expr_part = item.split('=', 1)[1].strip() if '=' in item else item
        
        # 匹配独立变量（不带[i]的变量）
        vars_in_expr = re.findall(r'\b([a-zA-Z_]\w*)\b(?!\s*\[)', expr_part)
        
        # 添加到结果列表（去重）
        for var in vars_in_expr:
            if var != 'i' and var not in seen:
                seen.add(var)
                constants.append(var)
    
    return tuple(constants)

def Est_lNSA(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, QU:QuType, passa, passb, passc, edgea,  start_time_a,  start_time_b, edgeb, In_C, edgec, start_time_C, unique_pe_addresses, I , J, K, Eq, transpose, code_line, AdderTree_PIPELINES, IF_RST_N=False):
    area = 0
    starttimea = copy.deepcopy(start_time_a)
    starttimeb = copy.deepcopy(start_time_b)
    
    # 预计算所有需要的值，避免重复计算
    outputs = {eq[0] for eq in Eq}  # {'C', 'E'}
    input_info = OrderedDict() 

    for eq_idx, eq in enumerate(Eq):
        for var_idx, var in enumerate(eq[1:], start=1):  # 跳过输出变量（索引0）
            if var not in input_info and var not in outputs:
                input_info[var] = (eq_idx, var_idx)

    input_elements = list(input_info.keys())  # 保持顺序的输入变量 ['A', 'B', 'D']
    input_elements_set = set(input_elements)  # 转换为set以提高查找效率
    
    # 预计算所有输出和索引
    all_outputs = []
    all_indices = []
    for i, eq in enumerate(Eq):
        all_outputs.append(eq[0])  
        all_indices.append((i, 0))  # 记录位置 (方程索引, 0)
    
    used_vars = set()
    for eq in Eq:
        used_vars.update(eq[1:])  # 收集所有输入变量
    
    final_outputs = []
    final_indices = []
    for var, idx in zip(all_outputs, all_indices):
        if var not in used_vars:
            final_outputs.append(var)
            final_indices.append(idx)
    
    intermediate_outputs = []
    intermediate_indices = []
    for var, idx in zip(all_outputs, all_indices):
        if var in used_vars:  # 被其他方程使用过的输出变量
            intermediate_outputs.append(var)
            intermediate_indices.append(idx)

    # 预计算start_time_C的最小值，避免重复计算
    min_start_time_c = []
    for tn in range(len(Eq)):
        min_start_time_c.append(_get_min_start_time_c_cached(start_time_C, tn))

    for tn in range(len(Eq)):         
############################################input A#######################################################
        if code_line[tn] == 0:                              
            # 优化：批量处理starttimea[tn]的更新
            if Eq[tn][1] in input_elements_set:
                for key in starttimea[tn]:
                    starttimea[tn][key] = np.int64(0)
            else:
                for key in starttimea[tn]:
                    starttimea[tn][key] = np.int64(0)  
                
                i, j = find_first_occurrence(Eq, Eq[tn][1])
                # 优化：批量累加而不是逐个更新
                cumulative_time = 0
                for tnn in range(i+1, tn):
                    cumulative_time += min_start_time_c[tnn]
                
                if cumulative_time > 0:
                    _batch_update_start_times(starttimea[tn], cumulative_time)
                    
            # 优化：类似地处理starttimeb[tn]
            if Eq[tn][2] in input_elements_set:
                cumulative_time_b = sum(min_start_time_c[tnn] for tnn in range(tn))
                if cumulative_time_b > 0:
                    _batch_update_start_times(starttimeb[tn], cumulative_time_b)
            else:
                for key in starttimeb[tn]:
                    starttimeb[tn][key] = np.int64(0)  
                
                i, j = find_first_occurrence(Eq, Eq[tn][2])
                cumulative_time_b = sum(min_start_time_c[tnn] for tnn in range(i+1, tn))
                
                if cumulative_time_b > 0:
                    _batch_update_start_times(starttimeb[tn], cumulative_time_b)
                        
            # 调用Est_DataflowPE
            dfpe = Est_DataflowPE(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, 
                                 QU_IN_A=QU[Eq[tn][1]], QU_IN_B=QU[Eq[tn][2]], QU_OUT=QU[Eq[tn][0]], 
                                 unique_pe_addresses=unique_pe_addresses[tn], passa=passa[tn], 
                                 passb=passb[tn], passc=passc[tn], edgea=edgea[tn], 
                                 starta=starttimea[tn], edgeb=edgeb[tn], startb=starttimeb[tn], 
                                 edgec=edgec[tn], In_C=In_C[tn], K=K[tn],
                                 AdderTree_PIPELINES=AdderTree_PIPELINES, IF_RST_N=IF_RST_N)
            
            area += dfpe
        else:          
            # 优化：使用更高效的start数组创建
            start = _create_start_array_optimized(len(Eq[tn]), start_time_a[tn])
            
            # 优化：批量处理start数组的更新
            for si in range(1, len(Eq[tn])):
                if Eq[tn][si] in input_elements_set:
                    for key in starttimea[tn]:
                        start[si][key] = np.int64(0) 
                else:
                    for key in starttimea[tn]:
                        start[si][key] = np.int64(0)  
                    
                    i, j = find_first_occurrence(Eq, Eq[tn][si])
                    # 优化：批量累加
                    cumulative_time = sum(min_start_time_c[tnn] for tnn in range(i+1, tn))
                    
                    if cumulative_time > 0:
                        _batch_update_start_times(start[si], cumulative_time)
            
            dfpeone = Est_DataflowPEone(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, 
                                       QU=QU, unique_pe_addresses=unique_pe_addresses[tn], 
                                       edgea=edgea[tn], starta=start, edgec=edgec[tn], 
                                       Eq=Eq[tn], code_line=code_line[tn], IF_RST_N=IF_RST_N)
            
            area += dfpeone
    
    return area





