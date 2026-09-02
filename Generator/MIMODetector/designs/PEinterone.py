import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

import pytv
import re
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import math 

from enum import Enum
from PyTU import QuMode, OfMode, QuType
from Delay import ModuleDelay
from FxMatch import ModuleFxMatch
from Mul import ModuleMul
from AddSubTree import ModuleAddSubTree


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
    
    
@convert
def ModulePEinterone(QU:QuType, code_line, Eq, N_PIPELINES=0, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=False):
    # Clock, Resets and Enables
    if N_PIPELINES > 0 and type(IF_RST_N) == bool:
        # Expand the boolean to a list of the same value
        IF_RST_N = [IF_RST_N] * N_PIPELINES


    #/ module PEinterone(
    for id in range(1,len(Eq)):
        #/  i_data_`Eq[id]`,
        pass
    #/  o_data_`Eq[0]`
    if N_PIPELINES > 0:
        #/    ,i_clk
        if any(IF_RST_N):
            #/    , i_rst_n
            pass
    #/ );
    
    for id in range(1,len(Eq)):
        #/ input wire [`QU[Eq[id]].DWT-1`:0] i_data_`Eq[id]`;
        pass

    #/ output wire [`QU[Eq[0]].DWT-1`:0] o_data_`Eq[0]`;

    if N_PIPELINES > 0:
        #/ input wire i_clk;
        if any(IF_RST_N):
            #/ input wire i_rst_n;
            pass
        pass
    
    for id in range(1,len(Eq)):
        #/ wire [`QU[Eq[id]].DWT-1`:0] data_`Eq[id]`;
        #/ assign data_`Eq[id]`= i_data_`Eq[id]`;
        pass
        
    
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
            #/ wire [`QU[Eq[0]].DWT-1`:0] data_d_`multiplication_list[mi][0]``multiplication_list[mi][1]`;
            inst_ports_mul = {
                "i_data_1": f"data_{multiplication_list[mi][0]}",
                "i_data_2": f"data_{multiplication_list[mi][1]}",
                "o_data": f"data_d_{multiplication_list[mi][0]}{multiplication_list[mi][1]}",
                "i_clk": "i_clk"
            }
            if IF_RST_N[0]:
                inst_ports_mul["i_rst_n"] = "i_rst_n"
            
            ModuleMul(QU_IN_1 = QU[multiplication_list[mi][0]], QU_IN_2=QU[multiplication_list[mi][1]], QU_OUT=QU[Eq[0]], N_PIPELINES=1, QU_MODE = QU_MODE, OF_MODE = OF_MODE, IF_RST_N=IF_RST_N[0], PORTS = inst_ports_mul)              
        else:
            pass
            
            

    not_mul = extract_non_multiplied_vars(code_line=code_line)

    for nmul in not_mul:
        #/ wire [`QU[Eq[0]].DWT-1`:0] data_d_`nmul`;
        inst_ports_d = {
            "i_data": f"data_{nmul}",
            "o_data": f"data_d_{nmul}",
            "i_clk": "i_clk"
        }
        if IF_RST_N[0]:
            inst_ports_d["i_rst_n"] = "i_rst_n"
            
        ModuleFxMatch(QU_IN = QU[nmul], QU_OUT = QU[Eq[0]], QU_MODE = QU_MODE, OF_MODE = OF_MODE, N_CLK = 1, IF_RST_N = IF_RST_N[0], PORTS = inst_ports_d)

    
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
        #/  wire [`QU[Eq[0]].DWT*len(sign_flags)-1`:0] data_tree;
        for si in range(len(sign_flags)):
            #/ assign data_tree[`QU[Eq[0]].DWT*(si+1)-1`:`QU[Eq[0]].DWT*si`] = data_d_`elements[si]`;
            pass
        inst_ports_tree = {
            "i_data": "data_tree",
            "o_data": f"o_data_{Eq[0]}",
            "i_clk": "i_clk"
        }
        if IF_RST_N[0]:
            inst_ports_tree["i_rst_n"] = "i_rst_n"
        
        ModuleAddSubTree(QU_IN = QU[Eq[0]], QU_OUT=QU[Eq[0]], sign_flags=sign_flags, N_PIPELINES=math.ceil(math.log2(len(sign_flags))),N_INPUTS=len(sign_flags), QU_MODE = QU_MODE, OF_MODE = OF_MODE, IF_RST_N=IF_RST_N[0], PORTS = inst_ports_tree)   
    else:
        #/ assign o_data_`Eq[0]`= data_d_`multiplication_list[0][0]``multiplication_list[0][1]`;  
        pass
    #/ endmodule     