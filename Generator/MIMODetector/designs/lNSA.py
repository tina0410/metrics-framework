import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

import pytv
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

import re
from collections import OrderedDict
from enum import Enum
from PyTU import QuMode, OfMode, QuType
from Delay import ModuleDelay
from Delayreg import ModuleDelayreg
from FxMatch import ModuleFxMatch
from DataflowPE import ModuleDataflowPE
from DataflowPEone import ModuleDataflowPEone
import math 
import numpy as np
from typing import List, Set
import Getloop
import GetIS
import copy
def find_first_occurrence(lst, target):

    for i, sublist in enumerate(lst):
        for j, item in enumerate(sublist):
            if item == target:
                return (i, j)
    return None
    
def extract_constants_from_list(code_list: List) -> List[str]:
    """
    从列表中提取所有方程中的常数（不带[i]的变量），去重后返回列表。
    
    Args:
        code_list: 可能包含字符串方程的列表（如 `'x2[i] = x1[i] + a'`）。
        
    Returns:
        去重后的常数列表（如 `['a', 'b']`）。
    """
    constants = []
    seen = set()  # 用于去重
    
    for item in code_list:
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
    
    return constants

@convert
def ModulelNSA(QU:QuType, passa, passb, passc, edgea,  start_time_a,  start_time_b, edgeb, In_C, edgec, start_time_C, unique_pe_addresses, I , J, K, Eq, transpose, code_line, AdderTree_PIPELINES,QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=False):
    starttimea=copy.deepcopy(start_time_a)
    starttimeb=copy.deepcopy(start_time_b)
#     code = """
# for i in range(3):
#     for j in range(4):
#         for k in range(5):
#             d[i, j] += H[i,k] * y[k, j]
#     """
    
#     T = np.array([
#         [1, 0, 0],
#         [0, 1, 0],
#         [1, 1, 1]
#     ])
###################################################################################################
    constants=extract_constants_from_list(code_line) #返回常数['a']
    
    outputs = {eq[0] for eq in Eq}  # {'C', 'E'}
    input_info = OrderedDict() 

    for eq_idx, eq in enumerate(Eq):
        for var_idx, var in enumerate(eq[1:], start=1):  # 跳过输出变量（索引0）
            if var not in input_info and var not in outputs:
                input_info[var] = (eq_idx, var_idx)

    input_elements = list(input_info.keys())  # 保持顺序的输入变量 ['A', 'B', 'D']
    input_indices = list(input_info.values())  # 对应的首次出现位置 [(0, 1), (0, 2), (1, 1)]
    
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
            
    #/ module PE(
    for a, b in input_indices:
        #/  i_data_`Eq[a][b]`,
        pass
    #/  o_data,
    #/  en,
    for i in range(1+len(Eq)//4*2):
        #/ control_`i`,
        pass
    #/  i_clk
    if IF_RST_N == True:
        #/ , i_rst_n
        pass      
    #/);
    
    #/ input wire i_clk; 
    #/ input wire en;
    for i in range(1+len(Eq)//4*2):
        #/ input wire control_`i`;
        pass
    if IF_RST_N == True:
        #/ input wire i_rst_n;
        pass
    


    for a, b in input_indices:
        if Eq[a][b] in constants:
            #/ input wire [`QU[Eq[a][b]].DWT`-1:0] i_data_`Eq[a][b]`;
            pass
        else:
            if b==1:
                if Eq[a][b] in {"D1", "D2", "D4"}:
                    #/ input wire [`QU[Eq[a][b]].DWT`-1:0] i_data_`Eq[a][b]`;
                    pass                
                else:
                    #/ input wire [`QU[Eq[a][b]].DWT * max(I[a], K[a])`-1:0] i_data_`Eq[a][b]`;
                    pass
            else:
                #/ input wire [`QU[Eq[a][b]].DWT * K[a] * J[a]`-1:0] i_data_`Eq[a][b]`;
                pass
    #/ output wire [`QU[Eq[len(Eq)-1][0]].DWT `-1:0] o_data;
    
    for a, b in intermediate_indices:
        if Eq[a][b] in {"d2", "x1", "x2", "d3", "ymf", "Dx1", "Dx2"}:
            #/  wire [`QU[Eq[a][b]].DWT `-1:0] data_`Eq[a][b]`;
            pass            
        else:
            #/  wire [`QU[Eq[a][b]].DWT * I[a] * J[b]`-1:0] data_`Eq[a][b]`;
            pass


    for tn in range(len(Eq)):
    
                    
        inst_ports_PE = {
            "i_clk": "i_clk"
        }
        if IF_RST_N:
            inst_ports_PE["i_rst_n"] = "i_rst_n"   

############################################input A#######################################################
        if code_line[tn]==0:
            indexa = 0
            if tn==0:
                inst_ports_PE["control"] = f"control_0"
            else:
                inst_ports_PE["control"] = f"control_{((tn-1)//4)*2+(tn-1)%4}"
            for pe in edgea[tn]:
                i, j = pe
                if Eq[tn][1] in input_elements:
                    inst_ports_PE[f"InA_{i}_{j}"] = f"i_data_{Eq[tn][1]}[{indexa+1}*{QU[Eq[tn][1]].DWT}-1:{indexa}*{QU[Eq[tn][1]].DWT}]"
                else:
                    inst_ports_PE[f"InA_{i}_{j}"] = f"data_{Eq[tn][1]}[{indexa+1}*{QU[Eq[tn][1]].DWT}-1:{indexa}*{QU[Eq[tn][1]].DWT}]"
                indexa += 1
                        
############################################input B####################################################### 
            indexb = 0
            for pe in edgeb[tn]:
                i, j = pe
                if Eq[tn][2] in input_elements:
                    inst_ports_PE[f"InB_{i}_{j}"] = f"i_data_{Eq[tn][2]}[{indexb+1}*{QU[Eq[tn][2]].DWT}-1:{indexb}*{QU[Eq[tn][2]].DWT}]"    
                else:
                    inst_ports_PE[f"InB_{i}_{j}"] = f"data_{Eq[tn][2]}[{indexb+1}*{QU[Eq[tn][2]].DWT}-1:{indexb}*{QU[Eq[tn][2]].DWT}]"  
                indexb += 1                   

############################################ output C #######################################################
            indexc = 0                        
            for pe in edgec[tn]:
                i, j = pe
                if Eq[tn][0] in final_outputs:
                    inst_ports_PE[f"OutC_{i}_{j}"] = f"o_data[{indexc+1}*{QU[Eq[tn][0]].DWT}-1:{indexc}*{QU[Eq[tn][0]].DWT}]"
                else:
                    inst_ports_PE[f"OutC_{i}_{j}"] = f"data_{Eq[tn][0]}[{indexc+1}*{QU[Eq[tn][0]].DWT}-1:{indexc}*{QU[Eq[tn][0]].DWT}]"
                indexc+=1
                
            if Eq[tn][1] in input_elements:
                # for tnn in range(tn):
                #     for key in starttimea[tn]:
                #         starttimea[tn][key] = np.int64(starttimea[tn][key]+ min(start_time_C[tnn].values()))
                for key in starttimea[tn]:
                    starttimea[tn][key] = np.int64(0)
            else:
                for key in starttimea[tn]:
                    starttimea[tn][key] = np.int64(0)  
                i,j=find_first_occurrence(Eq,Eq[tn][1])
                for tnn in range(i+1,tn):
                    for key in starttimea[tn]:
                        starttimea[tn][key] = np.int64(starttimea[tn][key]+ min(start_time_C[tnn].values()))       
                    
            if Eq[tn][2] in input_elements:
                for tnn in range(tn):
                    for key in starttimeb[tn]:
                        starttimeb[tn][key] = np.int64(starttimeb[tn][key]+ min(start_time_C[tnn].values()))
            else:
                for key in starttimeb[tn]:
                    starttimeb[tn][key] = np.int64(0)  
                i,j=find_first_occurrence(Eq,Eq[tn][2])
                for tnn in range(i+1,tn):
                    for key in starttimeb[tn]:
                        starttimeb[tn][key] = np.int64(starttimeb[tn][key]+ min(start_time_C[tnn].values()))    
                        

            ModuleDataflowPE(QU_IN_A=QU[Eq[tn][1]], QU_IN_B=QU[Eq[tn][2]], QU_OUT=QU[Eq[tn][0]], unique_pe_addresses=unique_pe_addresses[tn], passa=passa[tn], passb=passb[tn], passc=passc[tn], edgea=edgea[tn], starta=starttimea[tn], edgeb=edgeb[tn], startb=starttimeb[tn], edgec=edgec[tn], In_C=In_C[tn], K=K[tn],AdderTree_PIPELINES=AdderTree_PIPELINES, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N, PORTS = inst_ports_PE)
        else:
            for id in range(1,len(Eq[tn])):
                index=0
                for pe in edgea[tn]:
                    i, j = pe
                    if Eq[tn][id] in input_elements:
                        if Eq[tn][id] in constants:
                             inst_ports_PE[f"In{Eq[tn][id]}_{i}_{j}"] = f"i_data_{Eq[tn][id]}"    
                        else:
                            inst_ports_PE[f"In{Eq[tn][id]}_{i}_{j}"] = f"i_data_{Eq[tn][id]}[{index+1}*{QU[Eq[tn][id]].DWT}-1:{index}*{QU[Eq[tn][id]].DWT}]"    
                    else:
                        inst_ports_PE[f"In{Eq[tn][id]}_{i}_{j}"] = f"data_{Eq[tn][id]}[{index+1}*{QU[Eq[tn][id]].DWT}-1:{index}*{QU[Eq[tn][id]].DWT}]"  
                    index+=1
            indexc = 0                        
            for pe in edgec[tn]:
                i, j = pe
                if Eq[tn][0] in final_outputs:
                    inst_ports_PE[f"Out{Eq[tn][0]}_{i}_{j}"] = f"o_data[{indexc+1}*{QU[Eq[tn][0]].DWT}-1:{indexc}*{QU[Eq[tn][0]].DWT}]"
                else:
                    inst_ports_PE[f"Out{Eq[tn][0]}_{i}_{j}"] = f"data_{Eq[tn][0]}[{indexc+1}*{QU[Eq[tn][0]].DWT}-1:{indexc}*{QU[Eq[tn][0]].DWT}]"
                indexc+=1
            
            start=[]
            for si in range(0,len(Eq[tn])):
                start.append(copy.deepcopy(start_time_a[tn]))

            for si in range(1,len(Eq[tn])):
                if Eq[tn][si] in input_elements:
                    for key in starttimea[tn]:
                        start[si][key] = np.int64(0) 
                    # for tnn in range(tn):
                    #     for key in starttimea[tn]:
                    #         start[si][key] = np.int64(start[si][key]+ min(start_time_C[tnn].values()))
                else:
                    for key in starttimea[tn]:
                        start[si][key] = np.int64(0)  
                    i,j=find_first_occurrence(Eq,Eq[tn][si])
                    for tnn in range(i+1,tn):
                        for key in starttimea[tn]:
                            start[si][key] = np.int64(start[si][key]+ min(start_time_C[tnn].values()))
            
            ModuleDataflowPEone(QU=QU,unique_pe_addresses=unique_pe_addresses[tn], edgea=edgea[tn], starta=start, edgec=edgec[tn], Eq=Eq[tn], code_line=code_line[tn], QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N, PORTS = inst_ports_PE)

    #/ endmodule 
                        
                
                    
    