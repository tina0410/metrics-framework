import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

import pytv
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader


from enum import Enum
from PyTU import QuMode, OfMode, QuType
from Delay import ModuleDelay
from FxMatch import ModuleFxMatch
from PEinterone import ModulePEinterone
from Add import ModuleAdd
from Mul import ModuleMul
from AdderTree import ModuleAdderTree
import math 
import numpy as np

@convert
def ModuleDataflowPEone(QU:QuType, unique_pe_addresses, edgea, starta,  edgec, Eq, code_line, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=False):
    if type(IF_RST_N) == bool:
        IF_RST_N = [IF_RST_N] * len(unique_pe_addresses) *4 # 2 in order to meet the requirements of non-rectangular arrays
    #print(unique_pe_addresses)
    #/ module DATAFLOWPEONE (
    for pe_address in edgea:
        i, j = pe_address
        for id in range(1,len(Eq)):
            #/  In`Eq[id]`_`i`_`j`,
            pass
        pass
    for pe_address in edgec:
        i, j = pe_address
        #/ Out`Eq[0]`_`i`_`j`,
        pass
    #/  i_clk
    if any(IF_RST_N) == True:
        #/ , i_rst_n
        pass    
    #/ );
    
    #/ input wire i_clk; 
    if any(IF_RST_N) == True:
        #/ input wire i_rst_n;
        pass
    for pe_address in edgea:
        i, j = pe_address
        for id in range(1,len(Eq)):
            #/ input [`QU[Eq[id]].DWT-1`:0] In`Eq[id]`_`i`_`j`;
            pass
        pass


    #/  // Output Signals
    for pe_address in edgec:
        i, j = pe_address
        #/ output [`QU[Eq[0]].DWT-1`:0] Out`Eq[0]`_`i`_`j`;
        pass
    
    for pe_address in edgea:
        i, j = pe_address
        for id in range(1,len(Eq)):
            #/ wire [`QU[Eq[id]].DWT-1`:0] `Eq[id]`_`i`_`j`;
            pass
        pass
        #/ // Assign Input to edge PEs
    for pe_address in edgea:
        i, j = pe_address
        for id in range(1,len(Eq)):
            daa = starta[id][i, j]
            inst_ports_daa = {
                "i_data": f"In{Eq[id]}_{i}_{j}",
                "o_data": f"{Eq[id]}_{i}_{j}"
            }
            if daa > 0:
                inst_ports_daa["i_clk"] = "i_clk"
                if IF_RST_N[0]:
                    inst_ports_daa["i_rst_n"] = "i_rst_n"

            ModuleDelay(DWT = QU[Eq[id]].DWT, N_CLK = daa, IF_RST_N = IF_RST_N[0], PORTS = inst_ports_daa)
            
        
    for pe in unique_pe_addresses:
        i, j = pe
        inst_ports_pe = {
            f"o_data_{Eq[0]}": f"Out{Eq[0]}_{i}_{j}",
            "i_clk": "i_clk"
        }
        if IF_RST_N[0]:
            inst_ports_pe["i_rst_n"] = "i_rst_n"
        for id in range(1,len(Eq)):
            inst_ports_pe[f"i_data_{Eq[id]}"] = f"{Eq[id]}_{i}_{j}"
        ModulePEinterone(QU= QU,  N_PIPELINES=3, code_line=code_line, Eq=Eq, QU_MODE = QU_MODE, OF_MODE = OF_MODE, IF_RST_N=IF_RST_N[0], PORTS = inst_ports_pe)
    #/ endmodule

            
            