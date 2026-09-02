import sys
import os 
import re
# from tests.parameters import Parameters

from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

from PyTU import QuMode, OfMode, QuType
# from EstModule import Est_ADD, Est_SUB, Est_MUL, Est_Delay, Est_AT, Est_PEinter
# from AddSubTree import Est_AddSubTree
# from PEinterone import Est_PEinterone
# from DataflowPEone import Est_DataflowPEone
# from DataflowPE import Est_DataflowPE
from lNSA import Est_lNSA
import math 
# import joblib
# import warnings
import pandas as pd
import os
import joblib
# from KeyParam import adder_config_v2, MUL_op, S2U_out
# import math
import warnings
import numpy as np
import re
import time
import PErela
import Getloop
import GetIS
import copy
import math 
from PyTU import QuMode, OfMode, QuType
from functools import lru_cache
import json

# 预计算常用的numpy数组，避免重复创建
_T_MATRICES = {
    'matrix_3x3_1': np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=np.int8),
    'matrix_3x3_2': np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]], dtype=np.int8),
    'matrix_3x1': np.array([[0], [0], [1]], dtype=np.int8)
}

@lru_cache(maxsize=128)
def _cached_ceil_log2(n):
    """缓存的ceil(log2)计算"""
    if n <= 1:
        return 0
    return math.ceil(math.log2(n))

@lru_cache(maxsize=256)
def _cached_range_extraction(code_str):
    """缓存的range值提取"""
    range_values = []
    for line in code_str.splitlines():
        line = line.strip()
        if 'range(' in line:
            start = line.index('range(') + len('range(')
            end = line.index(')', start)
            value = int(line[start:end])
            range_values.append(value)
    return tuple(range_values)

def _create_qu_dict_optimized(QU_IN_H, QU_IN_y, QU_IN_a, QU_IN_D, QU_OUT_ymf, QU_OUT_x1, QU_OUT_b2, QU_OUT_d2, QU_OUT_Dx1, QU_OUT_x2, QU_OUT_b3, QU_OUT_d3, QU_OUT_Dx2, QU_OUT_x3, QU_OUT_b4, QU_OUT_d4, QU_OUT_Dx3, QU_OUT_x4):
    """优化的QU字典创建"""
    QU = {}
    
    # 批量赋值相同类型的QU
    h_keys = ['HT1', 'H1', 'HT2', 'H2', 'HT3', 'H3', 'HT4']
    for key in h_keys:
        QU[key] = QU_IN_H
    
    d_keys = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7']
    for key in d_keys:
        QU[key] = QU_IN_D
    
    # 其他键值对
    QU.update({
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
    })
    
    return QU

def _generate_code_optimized(Tx, Rx):
    """优化的代码生成，减少字符串操作"""
    # 预计算字符串模板
    templates = [
        f"for i in range({Tx}):\n    for j in range(1):\n        for k in range({Rx}):\n            ymf[i, j] += HT1[i,k] * y[k, j]",
        f"for i in range({Tx}):\n    x1[i] = D1[i]*ymf[i]",
        f"for i in range({Rx}):\n    for j in range(1):\n        for k in range({Tx}):\n            b2[i, j] += H1[i,k] * x1[k, j]",
        f"for i in range({Tx}):\n    for j in range(1):\n        for k in range({Rx}):\n            d2[i, j] += HT2[i,k] * b2[k, j]",
        f"for i in range({Tx}):\n    Dx1[i] = D2[i]*x1[i]",
        f"for i in range({Tx}):\n    x2[i] = x1[i] + x1[i] - a*Dx1[i] + D3[i]*d2[i]",
        f"for i in range({Rx}):\n    for j in range(1):\n        for k in range({Tx}):\n            b3[i, j] += H2[i,k] * x2[k, j]",
        f"for i in range({Tx}):\n    for j in range(1):\n        for k in range({Rx}):\n            d3[i, j] += HT3[i,k] * b3[k, j]",
        f"for i in range({Tx}):\n    Dx2[i] = D4[i]*x2[i]",
        f"for i in range({Tx}):\n    x3[i] = x1[i] + x2[i] - a*Dx2[i] + D5[i]*d3[i]",
        f"for i in range({Rx}):\n    for j in range(1):\n        for k in range({Tx}):\n            b4[i, j] += H3[i,k] * x3[k, j]",
        f"for i in range({Tx}):\n    for j in range(1):\n        for k in range({Rx}):\n            d4[i, j] += HT4[i,k] * b4[k, j]",
        f"for i in range({Tx}):\n    Dx3[i] = D6[i]*x3[i]",
        f"for i in range({Tx}):\n    x4[i] = x1[i] + x3[i] - a*Dx3[i] + D7[i]*d4[i]"
    ]
    
    return templates

def _generate_T_matrices_optimized(iterations):
    """优化的T矩阵生成"""
    T = []
    tmax = 2 + iterations * 4
    
    # 预定义的模式
    pattern_3x3_1 = _T_MATRICES['matrix_3x3_1']
    pattern_3x3_2 = _T_MATRICES['matrix_3x3_2']
    pattern_3x1 = _T_MATRICES['matrix_3x1']
    
    # 按模式批量生成
    T.extend([pattern_3x3_1, pattern_3x1])  # 前两个
    
    # 重复模式
    for _ in range(iterations):
        T.extend([pattern_3x3_2, pattern_3x3_1, pattern_3x1, pattern_3x1])
    
    return T[:tmax]

def EstlNSA_MMSE(ModelAdd, Model_MUL, ModelSU_out, SU_in_db, Sub_db, Tx, Rx, AdderTree_PIPELINES, QU_IN_H:QuType, QU_IN_y:QuType, QU_IN_a:QuType, QU_IN_D:QuType, QU_OUT_ymf:QuType, QU_OUT_x1:QuType, QU_OUT_b2:QuType, QU_OUT_d2:QuType, QU_OUT_Dx1:QuType,QU_OUT_x2:QuType,QU_OUT_b3:QuType,QU_OUT_d3:QuType,QU_OUT_Dx2:QuType,QU_OUT_x3:QuType,QU_OUT_b4:QuType,QU_OUT_d4:QuType,QU_OUT_Dx3:QuType,QU_OUT_x4:QuType,iterations, IF_RST_N=False):
    # 优化：使用预优化的QU字典创建
    QU = _create_qu_dict_optimized(QU_IN_H, QU_IN_y, QU_IN_a, QU_IN_D, QU_OUT_ymf, QU_OUT_x1, QU_OUT_b2, QU_OUT_d2, QU_OUT_Dx1, QU_OUT_x2, QU_OUT_b3, QU_OUT_d3, QU_OUT_Dx2, QU_OUT_x3, QU_OUT_b4, QU_OUT_d4, QU_OUT_Dx3, QU_OUT_x4)
    
    N_FRAMES = 1

    # 优化：使用预优化的代码和矩阵生成
    code = _generate_code_optimized(Tx, Rx)
    T = _generate_T_matrices_optimized(iterations)
    
    tmax = 2 + iterations * 4
    transpose = []

    # 预分配所有列表，避免动态增长
    Eqn = [None] * tmax
    Nn = [None] * tmax
    Mn = [None] * tmax
    Pn = [None] * tmax
    In_An = [None] * tmax
    start_time_an = [None] * tmax
    end_time_an = [None] * tmax
    In_Bn = [None] * tmax
    start_time_bn = [None] * tmax
    end_time_bn = [None] * tmax
    Out_Cn = [None] * tmax
    In_Cn = [None] * tmax
    end_time_Cn = [None] * tmax
    start_time_Cn = [None] * tmax
    unique_pe_addressesn = [None] * tmax
    passan = [None] * tmax
    passbn = [None] * tmax
    passcn = [None] * tmax
    dependency_matricesn = [None] * tmax
    code_linen = [None] * tmax

    for tn in range(tmax):
        if T[tn].shape == (3, 3):
            # 优化：缓存正则表达式结果
            eqarrays = re.findall(r'(\w+)\s*\[', code[tn])
            Eq = list(dict.fromkeys(eqarrays))
            
            # 优化：使用缓存的range提取
            range_values = _cached_range_extraction(code[tn])
            N, M, P = (list(range_values) + [None, None, None])[:3]

            dependency_matrices = Getloop.get_dependency_matrices(code[tn])
            global_loop_vars = dependency_matrices[next(iter(dependency_matrices))][1]
            
            solution = np.eye(3)
            i = 0
            for var_name, (matrix, loop_vars) in dependency_matrices.items():
                solution[i] = GetIS.find_unit_solution(matrix)
                i += 1

            pass_pass = np.matmul(T[tn], solution.T).astype(np.int8)

            # 优化：预计算迭代向量
            iteration_vectors = [(i, j, k) for i in range(N) for j in range(M) for k in range(P)]
            
            unique_pe_addresses, cnt = PErela.generate_pe_addresses_and_times(T[tn], iteration_vectors)
            unique_pe_addresses = sorted(unique_pe_addresses)

            passa = pass_pass[:, 1]
            passb = pass_pass[:, 2]
            passc = pass_pass[:, 0]
            
            # 优化：简化输出迭代向量生成
            OUTiteration_vectors = [(i, j, P-1) for i in range(N) for j in range(M)]
            
            # 优化：简化条件判断
            if not (passa[0] or passa[1]):  # passa[0] == 0 and passa[1] == 0
                In_A = unique_pe_addresses
                start_time_a = {pe_address: times['start_time'] for pe_address, times in cnt.items()}
                end_time_a = start_time_a
            else:
                In_A, time_a = PErela.get_edge_points_with_times(unique_pe_addresses, passa[:2], cnt)
                start_time_a = {pe_address: times['start_time'] for pe_address, times in time_a.items()}
                end_time_a = {pe_address: times['end_time'] for pe_address, times in time_a.items()}
                
            if not (passb[0] or passb[1]):  # passb[0] == 0 and passb[1] == 0
                In_B = unique_pe_addresses
                start_time_b = {pe_address: times['start_time'] for pe_address, times in cnt.items()}
                end_time_b = start_time_b
            else:
                In_B, time_b = PErela.get_edge_points_with_times(unique_pe_addresses, passb[:2], cnt)
                start_time_b = {pe_address: times['start_time'] for pe_address, times in time_b.items()}
                end_time_b = {pe_address: times['end_time'] for pe_address, times in time_b.items()}
                
            if not (passc[0] or passc[1]):  # passc[0] == 0 and passc[1] == 0
                Out_C = unique_pe_addresses
                end_time_C = {pe_address: times['end_time'] for pe_address, times in cnt.items()}
                In_C = unique_pe_addresses
                start_time_C = {key: np.int64(value + 1) for key, value in end_time_C.items()}
            else:
                OutCu, OutCT = PErela.generate_pe_addresses_and_times(T[tn], OUTiteration_vectors)
                OutCT = sorted(OutCT.items(), key=lambda x: (x[0][0], x[0][1]))   
                Out_C = sorted(OutCu)   
                time_c = {
                    (i, j): {'start_time': times['start_time'], 'end_time': times['end_time']}
                    for (i, j), times in OutCT
                }  
                start_time_C = {pe_address: times['start_time'] for pe_address, times in time_c.items()}
                end_time_C = {pe_address: times['end_time'] for pe_address, times in time_c.items()}
                In_C, in_time_c = PErela.get_edge_points_with_times(unique_pe_addresses, passc[:2], cnt)
                
                if passc[2] == 0:
                    end_time_C = {key: np.int64(value + AdderTree_PIPELINES) for key, value in end_time_C.items()}
                    start_time_C = {key: np.int64(value + AdderTree_PIPELINES) for key, value in start_time_C.items()}

            # 批量赋值
            Eqn[tn] = Eq
            Nn[tn] = N
            Mn[tn] = M
            Pn[tn] = P
            In_An[tn] = In_A
            start_time_an[tn] = start_time_a
            end_time_an[tn] = end_time_a
            In_Bn[tn] = In_B
            start_time_bn[tn] = start_time_b
            end_time_bn[tn] = end_time_b
            Out_Cn[tn] = Out_C
            In_Cn[tn] = In_C
            end_time_Cn[tn] = end_time_C
            start_time_Cn[tn] = start_time_C
            unique_pe_addressesn[tn] = unique_pe_addresses
            passan[tn] = passa
            passbn[tn] = passb
            passcn[tn] = passc
            dependency_matricesn[tn] = dependency_matrices
            code_linen[tn] = 0
            
        else:
            if T[tn].shape == (3, 1):
                # 优化：预定义常用值
                pe_address = (np.int64(0), np.int64(0))
                In_A = [pe_address]
                In_B = In_A
                In_C = In_A
                Out_C = In_A
                unique_pe_addresses = In_A
                
                start_time_a = {pe_address: np.int64(0)}
                end_time_a = {pe_address: np.int64(N-1)}
                start_time_b = start_time_a
                end_time_b = end_time_a
                
                Eq = Getloop.extract_variables_in_order(code[tn])
                start_time_C = copy.deepcopy(start_time_a)
                
                lines = code[tn].strip().split('\n')
                code_line = lines[1].strip()

                # 优化：使用缓存的log2计算
                add_sub_count = code_line.count('+') + code_line.count('-')
                log_offset = _cached_ceil_log2(add_sub_count + 1) + 1
                
                start_time_C = {key: np.int64(value + log_offset) for key, value in start_time_C.items()}
                end_time_C = {key: np.int64(value + N - 1) for key, value in start_time_C.items()}

                # 批量赋值
                code_linen[tn] = code_line
                Eqn[tn] = Eq
                Nn[tn] = N
                Mn[tn] = 1
                Pn[tn] = 1
                In_An[tn] = In_A
                start_time_an[tn] = start_time_a
                end_time_an[tn] = end_time_a
                In_Bn[tn] = In_B
                start_time_bn[tn] = start_time_b
                end_time_bn[tn] = end_time_b
                Out_Cn[tn] = Out_C
                In_Cn[tn] = In_C
                end_time_Cn[tn] = end_time_C
                start_time_Cn[tn] = start_time_C
                unique_pe_addressesn[tn] = unique_pe_addresses
                passan[tn] = 0
                passbn[tn] = 0
                passcn[tn] = 0
                dependency_matricesn[tn] = 0
            else:
                lines = code[tn].strip().split('\n')
                code_line = lines[2].strip()
                
                range_values = _cached_range_extraction(code[tn])
                N, M = (list(range_values) + [None, None])[:2]
                
                Eq = Getloop.extract_variables_in_order(code[tn])
                iteration_vector = PErela.extract_iterations(code[tn])
                unique_pe_addresses, cnt = PErela.generate_pe_addresses_and_times(T[tn], iteration_vector)
                unique_pe_addresses = sorted(unique_pe_addresses)

                In_A = unique_pe_addresses
                start_time_a = {pe_address: times['start_time'] for pe_address, times in cnt.items()}
                end_time_C = {pe_address: times['end_time'] for pe_address, times in cnt.items()}
                
                add_sub_count = code_line.count('+') + code_line.count('-')
                log_offset = _cached_ceil_log2(add_sub_count + 1) + 1
                
                end_time_C = {key: np.int64(value + log_offset) for key, value in end_time_C.items()}
                start_time_C = {key: np.int64(value + log_offset) for key, value in start_time_C.items()}
                
                end_time_a = start_time_a
                start_time_b = start_time_a
                end_time_b = start_time_a
                
                In_B = In_A
                In_C = In_A
                Out_C = In_A

                # 批量赋值
                code_linen[tn] = code_line
                Eqn[tn] = Eq
                Nn[tn] = N
                Mn[tn] = M
                Pn[tn] = 1
                In_An[tn] = In_A
                start_time_an[tn] = start_time_a
                end_time_an[tn] = end_time_a
                In_Bn[tn] = In_B
                start_time_bn[tn] = start_time_b
                end_time_bn[tn] = end_time_b
                Out_Cn[tn] = Out_C
                In_Cn[tn] = In_C
                end_time_Cn[tn] = end_time_C
                start_time_Cn[tn] = start_time_C
                unique_pe_addressesn[tn] = unique_pe_addresses
                passan[tn] = 0
                passbn[tn] = 0
                passcn[tn] = 0
                dependency_matricesn[tn] = 0

    # from datetime import datetime
    start_time = time.time()
    area = Est_lNSA(ModelAdd, Model_MUL, ModelSU_out, SU_in_db, Sub_db, 
                   QU=QU, 
                   passa=passan, 
                   passb=passbn, 
                   passc=passcn, 
                   edgea=In_An,  
                   start_time_a=start_time_an,  
                   start_time_b=start_time_bn, 
                   edgeb=In_Bn, 
                   In_C=In_Cn, 
                   edgec=Out_Cn, 
                   start_time_C=start_time_Cn, 
                   unique_pe_addresses=unique_pe_addressesn, 
                   I=Nn,  
                   J=Mn, 
                   K=Pn, 
                   Eq=Eqn, 
                   transpose=transpose, 
                   code_line=code_linen,
                   AdderTree_PIPELINES=AdderTree_PIPELINES, 
                   IF_RST_N=IF_RST_N)
    end_time = time.time()
    excution_time = end_time - start_time
    print(f"Time taken: {excution_time} seconds")
    area = float(area)
    
    return area, excution_time

def CalcTP(period:float, QAM:int, N_T:int):
        # period in ns
        # QAM number
        # Return TP in Gbps
        N_STG = N_T * 2
        return (1 / period) * math.log2(QAM) * N_T / N_STG

def EstlNSA_GUI(ModelAdd, ModelMUL, ModelSU_out, SU_in_db, Sub_db, ConfigFileName="./config.json"):
    # Load Configuration
    TP = 0
    try:
        with open(ConfigFileName, 'r') as f:
            config = json.load(f)
        
        # Load basic parameters from config
        Tx = config.get("Number of Transmit Antennas", 16)
        Rx = config.get("Number of Receiving Antennas", 256)

        ITERATIONS = config.get("Iterations", 2)
        IF_RST_N = config.get("Interface Reset Active Low", True)
        ADDERTREE_PIPELINES = config.get("Adder Tree Pipelines", 1)
        
        # 优化：批量创建QuType对象，减少重复的字典查找
        qu_configs = {
            'h': config.get("Quantization format of H", {"bitwidth": 9, "fractional width": 8, "signed": True}),
            'y': config.get("Quantization format of y", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'a': config.get("Quantization format of a", {"bitwidth": 4, "fractional width": 4, "signed": True}),
            'd': config.get("Quantization format of D", {"bitwidth": 5, "fractional width": 4, "signed": True}),
            'ymf': config.get("Quantization format of ymf", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'x1': config.get("Quantization format of x1", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'b2': config.get("Quantization format of b2", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'd2': config.get("Quantization format of d2", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'Dx1': config.get("Quantization format of Dx1", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'x2': config.get("Quantization format of x2", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'b3': config.get("Quantization format of b3", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'd3': config.get("Quantization format of d3", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'Dx2': config.get("Quantization format of Dx2", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'x3': config.get("Quantization format of x3", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'b4': config.get("Quantization format of b4", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'd4': config.get("Quantization format of d4", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'Dx3': config.get("Quantization format of Dx3", {"bitwidth": 9, "fractional width": 4, "signed": True}),
            'x4': config.get("Quantization format of x4", {"bitwidth": 9, "fractional width": 4, "signed": True})
        }
        
        # 批量创建QuType对象
        qu_types = {}
        for key, cfg in qu_configs.items():
            qu_types[key] = QuType(cfg["bitwidth"], cfg["fractional width"], cfg["signed"])
        
        # Load mode configurations
        qu_mode_mapping = {
            "TRN.TCPL": QuMode.TRN.TCPL,
            "TRN.SMGN": QuMode.TRN.SMGN,
            "RND.POS_INF": QuMode.RND.POS_INF,
            "RND.NEG_INF": QuMode.RND.NEG_INF,
            "RND.ZERO": QuMode.RND.ZERO,
            "RND.INF": QuMode.RND.INF,
            "RND.CONV": QuMode.RND.CONV
        }
        
        of_mode_mapping = {
            "WRP.TCPL": OfMode.WRP.TCPL,
            "SAT.TCPL": OfMode.SAT.TCPL,
            "SAT.SMGN": OfMode.SAT.SMGN,
            "SAT.ZERO": OfMode.SAT.ZERO
        }
        
        qu_mode_str = config.get("Quantization Mode", "TRN.TCPL")
        QU_MODE = qu_mode_mapping.get(qu_mode_str, QuMode.TRN.TCPL)
        
        of_mode_str = config.get("Overflow Mode", "WRP.TCPL")
        OF_MODE = of_mode_mapping.get(of_mode_str, OfMode.WRP.TCPL)
        
        PIPELINE_STAGES = config.get("Pipeline Stages", {"Multiplication": 1, "Adder Tree": 1})
        
    except FileNotFoundError:
        print(f"Warning: Config file {ConfigFileName} not found. Using default parameters.")
        # 使用默认参数
        Tx = 16
        Rx = 256
        ITERATIONS = 2
        IF_RST_N = True
        ADDERTREE_PIPELINES = 1
        
        # 默认QuType对象
        qu_types = {
            'h': QuType(9, 8, True),
            'y': QuType(9, 4, True),
            'a': QuType(4, 4, True),
            'd': QuType(5, 4, True)
        }
        
        # 为其他类型使用默认值
        default_qu = QuType(9, 4, True)
        for key in ['ymf', 'x1', 'b2', 'd2', 'Dx1', 'x2', 'b3', 'd3', 'Dx2', 'x3', 'b4', 'd4', 'Dx3', 'x4']:
            qu_types[key] = default_qu
        
        QU_MODE = QuMode.TRN.TCPL
        OF_MODE = OfMode.WRP.TCPL

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file {ConfigFileName}: {e}")
        return None
    
    except Exception as e:
        print(f"Error loading config: {e}")
        return None
    
    area, excution_time = EstlNSA_MMSE(ModelAdd, ModelMUL, ModelSU_out, SU_in_db, Sub_db,
        Tx=Tx,
        Rx=Rx,
        AdderTree_PIPELINES=ADDERTREE_PIPELINES,
        QU_IN_H=qu_types['h'],
        QU_IN_y=qu_types['y'],
        QU_IN_a=qu_types['a'],
        QU_IN_D=qu_types['d'],
        QU_OUT_ymf=qu_types['ymf'],
        QU_OUT_x1=qu_types['x1'],
        QU_OUT_b2=qu_types['b2'],
        QU_OUT_d2=qu_types['d2'],
        QU_OUT_Dx1=qu_types['Dx1'],
        QU_OUT_x2=qu_types['x2'],
        QU_OUT_b3=qu_types['b3'],
        QU_OUT_d3=qu_types['d3'],
        QU_OUT_Dx2=qu_types['Dx2'],
        QU_OUT_x3=qu_types['x3'],
        QU_OUT_b4=qu_types['b4'],
        QU_OUT_d4=qu_types['d4'],
        QU_OUT_Dx3=qu_types['Dx3'],
        QU_OUT_x4=qu_types['x4'],
        iterations=ITERATIONS,
        IF_RST_N=IF_RST_N
    )
    TP = CalcTP(period=50, QAM=64, N_T=Tx)
    return float(area), excution_time, TP

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    path = "."
    SU_in_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='SU_in', header = 0)
    Sub_db = pd.read_excel(path + '/model/SU_in.xlsx', sheet_name='Sub', header = 0)
    ModelAdd = joblib.load(path +'/model/ADD_area.pkl')
    ModelMUL = joblib.load(path +'/model/pure_MUL_area.pkl')
    ModelSU_out = joblib.load(path +'/model/SU_out_FxP_area.pkl')
    su_in_db_id = "ctx_su_in_db"
    model_su_out_id = "ctx_model_su_out"
    
    area, excution_time, TP = EstlNSA_GUI(ModelAdd, ModelMUL, ModelSU_out, SU_in_db, Sub_db, ConfigFileName="./config.json")
    print(f"Area: {area:.2f} um^2, TP = {TP:.5f} Gbps")
    print("Execution Time:", excution_time)