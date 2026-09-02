# Description: lNSA
# Author: Yifang Dai
# Date: 2025.2.22
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader  
import sys
import os 
import re
# from tests.parameters import Parameters

from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

import random
import pytest

from pathlib import Path
import subprocess
from Delay import ModuleDelay
from Delayreg import ModuleDelayreg
from FxMatch import ModuleFxMatch
from DataflowPE import ModuleDataflowPE
from DataflowPEone import ModuleDataflowPEone
from lNSA import ModulelNSA
import PyTU
import PyTB

import numpy as np
import PErela
import Getloop
import GetIS
import copy
import math 
from PyTU import QuMode, OfMode, QuType
import time


def ModulelNSA_MMSE(Tx, Rx, AdderTree_PIPELINES, QU_IN_H:QuType, QU_IN_y:QuType, QU_IN_a:QuType, QU_IN_D:QuType, QU_OUT_ymf:QuType, QU_OUT_x1:QuType, QU_OUT_b2:QuType, QU_OUT_d2:QuType, QU_OUT_Dx1:QuType,QU_OUT_x2:QuType,QU_OUT_b3:QuType,QU_OUT_d3:QuType,QU_OUT_Dx2:QuType,QU_OUT_x3:QuType,QU_OUT_b4:QuType,QU_OUT_d4:QuType,QU_OUT_Dx3:QuType,QU_OUT_x4:QuType,iterations,QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=False):
    QU_IN_1 = QU_IN_H
    QU_IN_2 = QU_IN_H
    QU = {}

    QU['HT1'] = QU_IN_H
    QU['H1'] = QU_IN_H
    QU['HT2'] = QU_IN_H
    QU['H2'] = QU_IN_H
    QU['HT3'] = QU_IN_H
    QU['H3'] = QU_IN_H
    QU['HT4'] = QU_IN_H
    QU['y'] =  QU_IN_y
    QU['a'] =  QU_IN_a
    QU['D1'] =  QU_IN_D
    QU['D2'] = QU_IN_D
    QU['D3'] = QU_IN_D
    QU['D4'] = QU_IN_D
    QU['D5'] = QU_IN_D
    QU['D6'] = QU_IN_D
    QU['D7'] = QU_IN_D
    # IF_ENABLE = Parameters.IF_ENABLE
    QU_OUT = QU_OUT_ymf
    QU['ymf'] =  QU_OUT_ymf
    QU['x1'] =   QU_OUT_x1
    QU['b2'] =   QU_OUT_b2
    QU['d2'] =   QU_OUT_d2
    QU['Dx1'] =  QU_OUT_Dx1
    QU['x2'] =   QU_OUT_x2
    QU['b3'] =   QU_OUT_b3
    QU['d3'] =   QU_OUT_d3
    QU['Dx2'] =  QU_OUT_Dx2
    QU['x3'] =   QU_OUT_x3
    QU['b4'] =   QU_OUT_b4
    QU['d4'] =   QU_OUT_d4
    QU['Dx3'] =  QU_OUT_Dx3
    QU['x4'] =   QU_OUT_x4

    N_FRAMES =  1


    # ------------------------------------------------------------------------------ #
    # Set working directory
    # os.system("rm -rf ./RTL/*")
    

    # folder_path = f'./RTL'

    

    # # Generate RTL code & Testbench
    
    
    # moduleloader.set_language_mode('VERILOG')
    # moduleloader.set_root_dir(folder_path)
    # moduleloader.disEnableWarning()
    # moduleloader.set_naming_mode("SEQUENTIAL")

    verilog_run_flag = True
    error_record = []

    print(f"Genrating RTL Code...")
    code = []
    T=[]
    transpose=[]
    code.append(f"""
for i in range({Tx}):
    for j in range(1):
        for k in range({Rx}):
            ymf[i, j] += HT1[i,k] * y[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    x1[i] = D1[i]*ymf[i]
    """)
#------------for i=2:k do--------------#
    code.append(f"""
for i in range({Rx}):
    for j in range(1):
        for k in range({Tx}):
            b2[i, j] += H1[i,k] * x1[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    for j in range(1):
        for k in range({Rx}):
            d2[i, j] += HT2[i,k] * b2[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    Dx1[i] = D2[i]*x1[i]
    """)
    
    code.append(f"""
for i in range({Tx}):
    x2[i] = x1[i] + x1[i] - a*Dx1[i] + D3[i]*d2[i]
    """)
#----------i=3--------------#    
    code.append(f"""
for i in range({Rx}):
    for j in range(1):
        for k in range({Tx}):
            b3[i, j] += H2[i,k] * x2[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    for j in range(1):
        for k in range({Rx}):
            d3[i, j] += HT3[i,k] * b3[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    Dx2[i] = D4[i]*x2[i]
    """)
    
    code.append(f"""
for i in range({Tx}):
    x3[i] = x1[i] + x2[i] - a*Dx2[i] + D5[i]*d3[i]
    """)
#----------i=4--------------#    
    code.append(f"""
for i in range({Rx}):
    for j in range(1):
        for k in range({Tx}):
            b4[i, j] += H3[i,k] * x3[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    for j in range(1):
        for k in range({Rx}):
            d4[i, j] += HT4[i,k] * b4[k, j]
    """)
    
    code.append(f"""
for i in range({Tx}):
    Dx3[i] = D6[i]*x3[i]
    """)
    
    code.append(f"""
for i in range({Tx}):
    x4[i] = x1[i] + x3[i] - a*Dx3[i] + D7[i]*d4[i]
    """)
        
    T.append(np.array([
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [1, 0, 0],
        [0, 0, 1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [1, 0, 0],
        [0, 0, 1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [1, 0, 0],
        [0, 0, 1]
    ]))
    T.append(np.array([
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    T.append(np.array([
        [0],
        [0],
        [1]
    ]))
    tmax=2+iterations*4
###################################################################################################
    Eqn=[]
    Nn=[]
    Mn=[]
    Pn=[]
    In_An=[]
    start_time_an=[]
    end_time_an=[]
    In_Bn=[]
    start_time_bn=[]
    end_time_bn=[]
    Out_Cn=[]
    In_Cn=[]
    end_time_Cn=[]
    start_time_Cn=[]
    unique_pe_addressesn=[]
    passan=[]
    passbn=[]
    passcn=[]
    dependency_matricesn=[]
    code_linen=[]
    for tn in range(tmax):
        if T[tn].shape == (3,3):
            eqarrays = re.findall(r'(\w+)\s*\[', code[tn])
            Eq=list(dict.fromkeys(eqarrays)) 
            # print("AT", AT)
            # print("BT", BT)
            range_values = []  
            for line in code[tn].splitlines():
                line = line.strip()  
                if 'range(' in line:  
                    start = line.index('range(') + len('range(')
                    end = line.index(')', start)
                    value = int(line[start:end])  
                    range_values.append(value)  
            N, M, P = (range_values + [None, None, None])[:3]

            dependency_matrices = Getloop.get_dependency_matrices(code[tn])
            global_loop_vars = dependency_matrices[next(iter(dependency_matrices))][1]
            
            
            solution = np.eye(3)
            i = 0
            for var_name, (matrix, loop_vars) in dependency_matrices.items():
                solution[i] = GetIS.find_unit_solution(matrix)
                i += 1
            
            

            pass_pass = np.matmul(T[tn], solution.T)

            pass_pass = np.array(pass_pass, dtype=np.int8)
            


            iteration_vectors = []

            for i in range(N):
                for j in range(M):
                    for k in range(P):
                        iteration_vectors.append((i, j, k))
            # Generate unique PE addresses
            unique_pe_addresses, time = PErela.generate_pe_addresses_and_times(T[tn], iteration_vectors)
            unique_pe_addresses = sorted(unique_pe_addresses)
            

            passa = pass_pass[:, 1]
            passb = pass_pass[:, 2]
            passc = pass_pass[:, 0]
            
            OUTiteration_vectors = []
            for i in range(N):
                for j in range(M):
                    for k in range(P-1,P):
                        OUTiteration_vectors.append((i, j, k))
            if passa[0] == 0 and passa[1] == 0:
                In_A = unique_pe_addresses
                start_time_a = {pe_address: times['start_time'] for pe_address, times in time.items()}
                end_time_a = start_time_a
            else:
                In_A, time_a = PErela.get_edge_points_with_times(unique_pe_addresses, passa[:2], time)
                
                start_time_a = {pe_address: times['start_time'] for pe_address, times in time_a.items()}
                end_time_a = {pe_address: times['end_time'] for pe_address, times in time_a.items()}
            if passb[0] == 0 and passb[1] == 0:
                In_B = unique_pe_addresses
                start_time_b = {pe_address: times['start_time'] for pe_address, times in time.items()}
                end_time_b = start_time_b
            else:
                In_B, time_b = PErela.get_edge_points_with_times(unique_pe_addresses, passb[:2], time)
                start_time_b = {pe_address: times['start_time'] for pe_address, times in time_b.items()}
                end_time_b = {pe_address: times['end_time'] for pe_address, times in time_b.items()}
            if passc[0] == 0 and passc[1] == 0:
                Out_C = unique_pe_addresses
                end_time_C = {pe_address: times['end_time'] for pe_address, times in time.items()}
                In_C = unique_pe_addresses
                start_time_C = end_time_C 
    
                for key in start_time_C:
                    start_time_C[key] = np.int64(start_time_C[key]+ 1)     
            else:
                OutCu, OutCT= PErela.generate_pe_addresses_and_times(T[tn], OUTiteration_vectors)
                OutCT = sorted(OutCT.items(), key=lambda x: (x[0][0], x[0][1]))   
                Out_C = sorted(OutCu)   
                time_c = {
                    (i, j): {'start_time': times['start_time'], 'end_time': times['end_time']}
                    for (i, j), times in OutCT
                }  
                start_time_C = {pe_address: times['start_time'] for pe_address, times in time_c.items()}
                end_time_C = {pe_address: times['end_time'] for pe_address, times in time_c.items()}
                In_C, in_time_c = PErela.get_edge_points_with_times(unique_pe_addresses, passc[:2], time)
                if passc[2]==0:
                    for key in end_time_C:
                        end_time_C[key] = np.int64(end_time_C[key]+ AdderTree_PIPELINES)       
                    for key in start_time_C:
                        start_time_C[key] = np.int64(start_time_C[key]+ AdderTree_PIPELINES)              

            Eqn.append(Eq)
            Nn.append(N)
            Mn.append(M)
            Pn.append(P)
            In_An.append(In_A)
            start_time_an.append(start_time_a)
            end_time_an.append(end_time_a)
            In_Bn.append(In_B)
            start_time_bn.append(start_time_b)
            end_time_bn.append(end_time_b)
            Out_Cn.append(Out_C)
            In_Cn.append(In_C)
            end_time_Cn.append(end_time_C)
            start_time_Cn.append(start_time_C)
            unique_pe_addressesn.append(unique_pe_addresses)
            passan.append(passa)
            passbn.append(passb)
            passcn.append(passc)
            dependency_matricesn.append(dependency_matrices)
            code_linen.append(0)
        else:
            if T[tn].shape == (3,1):
                In_A = [(np.int64(0), np.int64(0))]
                In_B=In_A
                In_C=In_A
                Out_C=In_A
                unique_pe_addresses=In_A
                # start_time_a = {
                #     tuple(map(np.int64, item['PE_address'].flatten())): np.int64(item['time'][0])
                #     for item in pe_addresses
                # }
                start_time_a = {(np.int64(0), np.int64(0)): np.int64(0)}
                end_time_a=copy.deepcopy(start_time_a)
                for key in end_time_a:
                    end_time_a[key] = np.int64(end_time_a[key]+ N-1)
                start_time_b=start_time_a
                end_time_b=end_time_a
            
                Eq= Getloop.extract_variables_in_order(code[tn])
                start_time_C=copy.deepcopy(start_time_a)
                
                lines = code[tn].strip().split('\n')
                code_line = lines[1].strip()

                add_sub_count = code_line.count('+') + code_line.count('-')
                
                for key in start_time_C:
                    start_time_C[key] = np.int64(start_time_C[key]+ math.ceil(math.log2(add_sub_count+1))+1)
                end_time_C=copy.deepcopy(start_time_C)
                for key in end_time_C:
                    end_time_C[key] = np.int64(end_time_C[key]+ N-1)

                
                code_linen.append(code_line)
                Eqn.append(Eq)
                Nn.append(N)
                Mn.append(1)
                Pn.append(1)
                In_An.append(In_A)
                start_time_an.append(start_time_a)
                end_time_an.append(end_time_a)
                In_Bn.append(In_B)
                start_time_bn.append(start_time_b)
                end_time_bn.append(end_time_b)
                Out_Cn.append(Out_C)
                In_Cn.append(In_C)
                end_time_Cn.append(end_time_C)
                start_time_Cn.append(start_time_C)
                unique_pe_addressesn.append(unique_pe_addresses)
                passan.append(0)
                passbn.append(0)
                passcn.append(0)
                dependency_matricesn.append(0)
            else:
                lines = code[tn].strip().split('\n')
                code_line = lines[2].strip()
                range_values = []  
                for line in code[tn].splitlines():
                    line = line.strip()  
                    if 'range(' in line:  
                        start = line.index('range(') + len('range(')
                        end = line.index(')', start)
                        value = int(line[start:end])  
                        range_values.append(value)  
                N, M = (range_values + [None, None])[:2]
                Eq= Getloop.extract_variables_in_order(code[tn])
                iteration_vector=PErela.extract_iterations(code[tn])
                unique_pe_addresses, time = PErela.generate_pe_addresses_and_times(T[tn], iteration_vector)
                unique_pe_addresses = sorted(unique_pe_addresses)

                In_A = unique_pe_addresses
                start_time_a = {pe_address: times['start_time'] for pe_address, times in time.items()}
                end_time_C = {pe_address: times['end_time'] for pe_address, times in time.items()}  
                add_sub_count = code_line.count('+') + code_line.count('-')
                start_time_C=copy.deepcopy(start_time_a)
                for key in end_time_C:
                    end_time_C[key] = np.int64(end_time_C[key]+ math.ceil(math.log2(add_sub_count+1))+1) 
                for key in start_time_C:
                    start_time_C[key] = np.int64(start_time_C[key]+ math.ceil(math.log2(add_sub_count+1))+1)     
                end_time_a=start_time_a
                start_time_b=start_time_a
                end_time_b=start_time_a
                
                In_B=In_A
                In_C=In_A
                Out_C=In_A

                code_linen.append(code_line)
                Eqn.append(Eq)
                Nn.append(N)
                Mn.append(M)
                Pn.append(1)
                In_An.append(In_A)
                start_time_an.append(start_time_a)
                end_time_an.append(end_time_a)
                In_Bn.append(In_B)
                start_time_bn.append(start_time_b)
                end_time_bn.append(end_time_b)
                Out_Cn.append(Out_C)
                In_Cn.append(In_C)
                end_time_Cn.append(end_time_C)
                start_time_Cn.append(start_time_C)
                unique_pe_addressesn.append(unique_pe_addresses)
                passan.append(0)
                passbn.append(0)
                passcn.append(0)
                dependency_matricesn.append(0)
    # -----------------------------User Settings------------------------------------ #

    #print("end_time_an:", end_time_an[1]) 
    ModulelNSA(QU=QU, passa=passan, passb=passbn, passc=passcn, edgea=In_An,  start_time_a=start_time_an,  start_time_b=start_time_bn, edgeb=In_Bn, In_C=In_Cn, edgec=Out_Cn, start_time_C=start_time_Cn, unique_pe_addresses=unique_pe_addressesn, I=Nn,  J=Mn, K=Pn, Eq=Eqn, transpose=transpose, code_line=code_linen,AdderTree_PIPELINES=AdderTree_PIPELINES, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=IF_RST_N)
    print('done')
    #moduleloader.reset()

def GenlNSA(ConfigFileName="./config_mimo.json", GenRoot="./RTL"):
    # Load Configuration
    import json
    
    try:
        with open(ConfigFileName, 'r') as f:
            config = json.load(f)
        
        # Load basic parameters from config
        Tx = config.get("Number of Transmit Antennas", 16)
        Rx = config.get("Number of Receiving Antennas", 256)

        ITERATIONS = config.get("Iterations", 2)
        IF_RST_N = config.get("Interface Reset Active Low", True)
        ADDERTREE_PIPELINES = config.get("Adder Tree Pipelines", 1)
        
        # Load input quantization types
        qu_h_config = config.get("Quantization format of H", {"bitwidth": 9, "fractional width": 8, "signed": True})
        QU_IN_H = QuType(qu_h_config["bitwidth"], qu_h_config["fractional width"], qu_h_config["signed"])
        
        qu_y_config = config.get("Quantization format of y", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_IN_y = QuType(qu_y_config["bitwidth"], qu_y_config["fractional width"], qu_y_config["signed"])
        
        qu_a_config = config.get("Quantization format of a", {"bitwidth": 4, "fractional width": 4, "signed": True})
        QU_IN_a = QuType(qu_a_config["bitwidth"], qu_a_config["fractional width"], qu_a_config["signed"])
        
        qu_d_config = config.get("Quantization format of D", {"bitwidth": 5, "fractional width": 4, "signed": True})
        QU_IN_D = QuType(qu_d_config["bitwidth"], qu_d_config["fractional width"], qu_d_config["signed"])
        
        # Load output quantization types
        qu_ymf_config = config.get("Quantization format of ymf", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_ymf = QuType(qu_ymf_config["bitwidth"], qu_ymf_config["fractional width"], qu_ymf_config["signed"])
        
        qu_x1_config = config.get("Quantization format of x1", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_x1 = QuType(qu_x1_config["bitwidth"], qu_x1_config["fractional width"], qu_x1_config["signed"])
        
        qu_b2_config = config.get("Quantization format of b2", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_b2 = QuType(qu_b2_config["bitwidth"], qu_b2_config["fractional width"], qu_b2_config["signed"])
        
        qu_d2_config = config.get("Quantization format of d2", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_d2 = QuType(qu_d2_config["bitwidth"], qu_d2_config["fractional width"], qu_d2_config["signed"])
        
        qu_Dx1_config = config.get("Quantization format of Dx1", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_Dx1 = QuType(qu_Dx1_config["bitwidth"], qu_Dx1_config["fractional width"], qu_Dx1_config["signed"])
        
        qu_x2_config = config.get("Quantization format of x2", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_x2 = QuType(qu_x2_config["bitwidth"], qu_x2_config["fractional width"], qu_x2_config["signed"])
        
        qu_b3_config = config.get("Quantization format of b3", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_b3 = QuType(qu_b3_config["bitwidth"], qu_b3_config["fractional width"], qu_b3_config["signed"])
        
        qu_d3_config = config.get("Quantization format of d3", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_d3 = QuType(qu_d3_config["bitwidth"], qu_d3_config["fractional width"], qu_d3_config["signed"])
        
        qu_Dx2_config = config.get("Quantization format of Dx2", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_Dx2 = QuType(qu_Dx2_config["bitwidth"], qu_Dx2_config["fractional width"], qu_Dx2_config["signed"])
        
        qu_x3_config = config.get("Quantization format of x3", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_x3 = QuType(qu_x3_config["bitwidth"], qu_x3_config["fractional width"], qu_x3_config["signed"])
        
        qu_b4_config = config.get("Quantization format of b4", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_b4 = QuType(qu_b4_config["bitwidth"], qu_b4_config["fractional width"], qu_b4_config["signed"])
        
        qu_d4_config = config.get("Quantization format of d4", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_d4 = QuType(qu_d4_config["bitwidth"], qu_d4_config["fractional width"], qu_d4_config["signed"])
        
        qu_Dx3_config = config.get("Quantization format of Dx3", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_Dx3 = QuType(qu_Dx3_config["bitwidth"], qu_Dx3_config["fractional width"], qu_Dx3_config["signed"])
        
        qu_x4_config = config.get("Quantization format of x4", {"bitwidth": 9, "fractional width": 4, "signed": True})
        QU_OUT_x4 = QuType(qu_x4_config["bitwidth"], qu_x4_config["fractional width"], qu_x4_config["signed"])
        
        # Load mode configurations
        qu_mode_str = config.get("Quantization Mode", "TRN.TCPL")
        if qu_mode_str == "TRN.TCPL":
            QU_MODE = QuMode.TRN.TCPL
        elif qu_mode_str == "TRN.SMGN":
            QU_MODE = QuMode.TRN.SMGN
        elif qu_mode_str == "RND.POS_INF":
            QU_MODE = QuMode.RND.POS_INF
        elif qu_mode_str == "RND.NEG_INF":
            QU_MODE = QuMode.RND.NEG_INF
        elif qu_mode_str == "RND.ZERO":
            QU_MODE = QuMode.RND.ZERO
        elif qu_mode_str == "RND.INF":
            QU_MODE = QuMode.RND.INF
        elif qu_mode_str == "RND.CONV":
            QU_MODE = QuMode.RND.CONV
        else:
            print(f"Warning: Unknown Quantization Mode '{qu_mode_str}', using default TRN.TCPL")
            QU_MODE = QuMode.TRN.TCPL
        
        of_mode_str = config.get("Overflow Mode", "WRP.TCPL")
        if of_mode_str == "WRP.TCPL":
            OF_MODE = OfMode.WRP.TCPL
        elif of_mode_str == "SAT.TCPL":
            OF_MODE = OfMode.SAT.TCPL
        elif of_mode_str == "SAT.SMGN":
            OF_MODE = OfMode.SAT.SMGN
        elif of_mode_str == "SAT.ZERO":
            OF_MODE = OfMode.SAT.ZERO
        else:
            print(f"Warning: Unknown Overflow Mode '{of_mode_str}', using default WRP.TCPL")
            OF_MODE = OfMode.WRP.TCPL
        
        PIPELINE_STAGES = config.get("Pipeline Stages", {"Multiplication": 1, "Adder Tree": 1})
        
    except FileNotFoundError:
        print(f"Warning: Config file {ConfigFileName} not found. Using default parameters.")
        # Use default parameters
        Tx = 16
        Rx = 256
        ITERATIONS = 2
        IF_RST_N = True
        ADDERTREE_PIPELINES = 3
        
        QU_IN_H = QuType(9, 8, True)
        QU_IN_y = QuType(9, 4, True)
        QU_IN_a = QuType(4, 4, True)
        QU_IN_D = QuType(5, 4, True)
        
        QU_OUT_ymf = QuType(9, 4, True)
        QU_OUT_x1 = QuType(9, 4, True)
        QU_OUT_b2 = QuType(9, 4, True)
        QU_OUT_d2 = QuType(9, 4, True)
        QU_OUT_Dx1 = QuType(9, 4, True)
        QU_OUT_x2 = QuType(9, 4, True)
        QU_OUT_b3 = QuType(9, 4, True)
        QU_OUT_d3 = QuType(9, 4, True)
        QU_OUT_Dx2 = QuType(9, 4, True)
        QU_OUT_x3 = QuType(9, 4, True)
        QU_OUT_b4 = QuType(9, 4, True)
        QU_OUT_d4 = QuType(9, 4, True)
        QU_OUT_Dx3 = QuType(9, 4, True)
        QU_OUT_x4 = QuType(9, 4, True)
        
        QU_MODE = QuMode.TRN.TCPL
        OF_MODE = OfMode.WRP.TCPL

    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file {ConfigFileName}: {e}")
        return
    
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    # Generate Module

    moduleloader.reset()
    moduleloader.set_root_dir(GenRoot)
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()
    
    start_gen_time = time.perf_counter()
    ModulelNSA_MMSE(
        Tx=Tx,
        Rx=Rx,
        AdderTree_PIPELINES=ADDERTREE_PIPELINES,
        QU_IN_H=QU_IN_H,
        QU_IN_y=QU_IN_y,
        QU_IN_a=QU_IN_a,
        QU_IN_D=QU_IN_D,
        QU_OUT_ymf=QU_OUT_ymf,
        QU_OUT_x1=QU_OUT_x1,
        QU_OUT_b2=QU_OUT_b2,
        QU_OUT_d2=QU_OUT_d2,
        QU_OUT_Dx1=QU_OUT_Dx1,
        QU_OUT_x2=QU_OUT_x2,
        QU_OUT_b3=QU_OUT_b3,
        QU_OUT_d3=QU_OUT_d3,
        QU_OUT_Dx2=QU_OUT_Dx2,
        QU_OUT_x3=QU_OUT_x3,
        QU_OUT_b4=QU_OUT_b4,
        QU_OUT_d4=QU_OUT_d4,
        QU_OUT_Dx3=QU_OUT_Dx3,
        QU_OUT_x4=QU_OUT_x4,
        iterations=ITERATIONS,
        QU_MODE=QU_MODE,
        OF_MODE=OF_MODE,
        IF_RST_N=IF_RST_N
    )
    end_gen_time = time.perf_counter()
    print(f"Generated  in {end_gen_time - start_gen_time:.2f} seconds.\n")
    return end_gen_time - start_gen_time    
    
if __name__ == "__main__":
    GenlNSA(ConfigFileName="./config.json", GenRoot="./RTL")
    # moduleloader.set_root_dir("./RTL")
    # moduleloader.set_naming_mode("SEQUENTIAL")
    # # moduleloader.saveParams()
    # moduleloader.disEnableWarning()

    # # ModuleAdd(QU_IN_1=QuType(9,3,True),QU_IN_2=QuType(10,4,True),QU_OUT=QuType(9,3,True),N_PIPELINES=0) # Combinational

    # ModulelNSA_MMSE(Tx=16, Rx=256, AdderTree_PIPELINES=1,QU_IN_H= QuType(9,8,True), QU_IN_y= QuType(9,4,True), QU_IN_a= QuType(4,4,True), QU_IN_D= QuType(5,4,True), QU_OUT_ymf= QuType(9,4,True), QU_OUT_x1= QuType(9,4,True), QU_OUT_b2= QuType(9,4,True), QU_OUT_d2= QuType(9,4,True), QU_OUT_Dx1= QuType(9,4,True),QU_OUT_x2= QuType(9,4,True),QU_OUT_b3= QuType(9,4,True),QU_OUT_d3= QuType(9,4,True),QU_OUT_Dx2= QuType(9,4,True),QU_OUT_x3= QuType(9,4,True),QU_OUT_b4= QuType(9,4,True),QU_OUT_d4= QuType(9,4,True),QU_OUT_Dx3= QuType(9,4,True),QU_OUT_x4= QuType(9,4,True),iterations=2,QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=True) 