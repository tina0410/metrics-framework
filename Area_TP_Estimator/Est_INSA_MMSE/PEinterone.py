import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

from PyTU import QuMode, OfMode, QuType
from EstModule import Est_ADD, Est_SUB, Est_MUL
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


def extract_non_multiplied_vars(code_line):
    # 提取右边表达式
    rhs = code_line.split('=')[1].strip()
    
    # 按 '+' 和 '-' 拆分（忽略空格）
    parts = []
    current_part = ""
    for char in rhs:
        if char in '+-':
            if current_part:
                parts.append(current_part)
                current_part = ""
        else:
            if char != ' ':
                current_part += char
    if current_part:
        parts.append(current_part)
    
    # 筛选没有乘法的变量名
    non_multiplied_vars = []
    for part in parts:
        if '*' not in part:  # 没有乘法运算
            var_name = part.split('[')[0]  # 去掉 [i]
            non_multiplied_vars.append(var_name)
    
    # 去重
    unique_vars = list(set(non_multiplied_vars))
    return unique_vars
    
    
def Est_PEinterone(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, QU:QuType, code_line, Eq, N_PIPELINES=0, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=False):
    area = 0
    # Clock, Resets and Enables
    if N_PIPELINES > 0 and type(IF_RST_N) == bool:
        # Expand the boolean to a list of the same value
        IF_RST_N = [IF_RST_N] * N_PIPELINES        
    
    multiplication_matches = re.finditer(
        r'([+-]?\s*\d*\.?\d*\s*\*\s*[a-zA-Z_]\w*)(?:\[i\])?|([a-zA-Z_]\w*(?:\[i\])?\s*\*\s*[a-zA-Z_]\w*)(?:\[i\])?',
        code_line
    )
    multiplication_list = []
    for idx, match in enumerate(multiplication_matches):
        term = match.group(0).replace(" ", "").replace("[i]", "").replace("[j]","")  # Remove spaces and [i] [j]
        if "*" in term:
            left, right = term.split("*")
            # Check if left is a number (e.g., "2*x1" -> left="2", right="x1")
            if left.replace(".", "").isdigit() or (left.startswith("-") and left[1:].replace(".", "").isdigit()):
                multiplication_list.append([float(left), right])
            else:
                multiplication_list.append([left, right])
    modified_formula = code_line
    for idx, (left, right) in enumerate(multiplication_list):
        term_to_replace = f"{left} * {right}[i]" if "[i]" in code_line else f"{left} * {right}"
        modified_formula = modified_formula.replace(term_to_replace, f"MUL_{idx}")
    modified_formula = modified_formula.replace("[i]", "").replace("[j]","")
    
    for mi in range(len(multiplication_list)):
        if isinstance(multiplication_list[mi][0], str):

            QU_IN_1 = QU[multiplication_list[mi][0]]
            QU_IN_2 = QU[multiplication_list[mi][1]]
            QU_OUT = QU[Eq[0]]
            area += Est_MUL(Model_MUL, Model_SU_out, SU_in_db, QU_IN_1.DWT, QU_IN_1.FRAC, QU_IN_1.IF_SIGNED, QU_IN_2.DWT, QU_IN_2.FRAC, QU_IN_2.IF_SIGNED, QU_OUT.DWT, QU_OUT.FRAC, 1, IF_RST_N[0])              
        else:
            pass
            
    not_mul = extract_non_multiplied_vars(code_line=code_line)
    for nmul in not_mul:
        if IF_RST_N[0] == True and type(IF_RST_N[0]) == bool:
            area += 6.72 * QU[Eq[0]].DWT * 1
        elif IF_RST_N[0] == False and type(IF_RST_N[0]) == bool:
            area += 5.88 * QU[Eq[0]].DWT * 1
        else:
            for i in range(1):
                if IF_RST_N[0][i] == True:
                    area += 6.72 * QU[Eq[0]].DWT
                else:
                    area += 5.88 * QU[Eq[0]].DWT
    
    right_side = modified_formula.split('=')[1].strip()
    terms = []
    current_term = ""
    sign = 1  
    for char in right_side:
        if char in '+-':
            if current_term:  
                terms.append((sign, current_term.strip()))
                current_term = ""
            sign = 1 if char == '+' else -1
        else:
            current_term += char
    if current_term:
        terms.append((sign, current_term.strip()))
    elementsn = [term[1] for term in terms]   # ['x1', 'x1', 'x1', 'D*b']
    elements = [s.replace('*', '') for s in elementsn]
    sign_flags = [0 if term[0] == 1 else 1 for term in terms]  #[0, 0, 1, 1]
    
    if len(sign_flags)>1:
        area += Est_AddSubTree(ModelAdd, Sub_db, QU_IN = QU[Eq[0]], QU_OUT=QU[Eq[0]], sign_flags=sign_flags, N_PIPELINES=math.ceil(math.log2(len(sign_flags))),N_INPUTS=len(sign_flags), IF_RST_N=IF_RST_N[0])     
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
    QU = {}

    QU['a'] =  QuType(2, 0, True)
    QU['D5'] = QuType(2, 0, True)
    QU['x1'] =   QuType(2, 0, True)
    QU['x2'] =   QuType(2, 0, True)
    QU['Dx2'] =  QuType(2, 0, True)
    QU['d3'] =   QuType(2, 0, True)
    QU['x3'] =   QuType(12, 0, True)
    
    a = Est_PEinterone(ModelAdd, Model_MUL, Model_SU_out, SU_in_db, Sub_db, QU=QU, code_line="x3[i] = x1[i] + x2[i] - a*Dx2[i] + D5[i]*d3[i]", Eq=["x3", "x1", "x2", "a", "Dx2", "D5", "d3"], N_PIPELINES=1)
    print("Estimated area:", a)
    
    end = time.time()
    print("Time taken: ", end - start)