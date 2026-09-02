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
from PEinter import ModulePEinter
from Add import ModuleAdd
from Mul import ModuleMul
from AdderTree import ModuleAdderTree
import math 
import numpy as np

@convert
def ModuleDataflowPE(QU_IN_A:QuType, QU_IN_B:QuType, QU_OUT:QuType, unique_pe_addresses, passa, passb, passc, edgea, starta, edgeb, startb, edgec, In_C, K, AdderTree_PIPELINES,QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=False):
    pia, pja, da = passa[0], passa[1], passa[2]
    pib, pjb, db = passb[0], passb[1], passb[2]
    pic, pjc, dc = passc[0], passc[1], passc[2]
    if type(IF_RST_N) == bool:
        IF_RST_N = [IF_RST_N] * len(unique_pe_addresses) *4 # 2 in order to meet the requirements of non-rectangular arrays
    #print(unique_pe_addresses)
    #/ module DATAFLOWPE (
    #/ control,
    for pe_address in edgea:
        i, j = pe_address
        #/ InA_`i`_`j`,
        pass
    #/  // Input Vector
    for pe_address in edgeb:
        i, j = pe_address
        #/ InB_`i`_`j`,
        pass
    #/  // Output Signals
    for pe_address in edgec:
        i, j = pe_address
        #/ OutC_`i`_`j`,
        pass
    #/  i_clk
    if any(IF_RST_N) == True:
        #/ , i_rst_n
        pass    
    #/ );
    
    #/ input wire i_clk; 
    #/ input wire control;
    if any(IF_RST_N) == True:
        #/ input wire i_rst_n;
        pass
    for pe_address in edgea:
        i, j = pe_address
        #/ input [`QU_IN_A.DWT-1`:0] InA_`i`_`j`;
        pass
    #/  // Input Vector
    for pe_address in edgeb:
        i, j = pe_address
        #/ input [`QU_IN_B.DWT-1`:0] InB_`i`_`j`;
        pass
    #/  // Output Signals
    for pe_address in edgec:
        i, j = pe_address
        #/ output [`QU_OUT.DWT-1`:0] OutC_`i`_`j`;
        pass
        

    # Internal signals
    #/  // Deinfe A ports
    for pe_address in unique_pe_addresses:
        i, j = pe_address
        #/  wire [`QU_IN_A.DWT-1`:0] A_`i`_`j`;
    #/  // Deinfe Delayed ports
    for pe_address in unique_pe_addresses:
        i, j = pe_address
        #/  wire [`QU_IN_A.DWT-1`:0] A_`i`_`j`_d`da`;

    #/  // Deinfe B ports
    for pe_address in unique_pe_addresses:
        i, j = pe_address
        #/  wire [`QU_IN_B.DWT-1`:0] B_`i`_`j`;

    #/  // Deinfe Delayed B ports
    for pe_address in unique_pe_addresses:
        i, j = pe_address
        #/  wire [`QU_IN_B.DWT-1`:0] B_`i`_`j`_d`db`;
    #/  // Deinfe C ports
    for pe_address in unique_pe_addresses:
        i, j = pe_address
        #/  wire [`QU_OUT.DWT-1`:0] C_`i`_`j`;
    #/  // Deinfe Delayed C ports
    for pe_address in unique_pe_addresses:
        i, j = pe_address
        #/  wire [`QU_OUT.DWT-1`:0] C_`i`_`j`_d`dc`;
    #/  // Deinfe Pass ports
    for pe_address in unique_pe_addresses:
        i, j = pe_address
        #/  wire [`QU_OUT.DWT-1`:0] P_`i`_`j`;



    #/ // Align A
    if passa[0] == 0 and passa[1] == 0:
        pass
    else:
        for pe in unique_pe_addresses:
            i, j = pe
            ii = i + pia
            jj = j + pja
            if (ii, jj) in unique_pe_addresses:
                porta = f'A_{i}_{j}_d{da}'
                #/  assign A_`ii`_`jj` = `porta`;
                pass

    #/ // Align B
    if passb[0] == 0 and passb[1] == 0:
        for pe_address in unique_pe_addresses:
            i, j = pe_address
            #/  wire [`QU_IN_B.DWT-1`:0] selB_`i`_`j`;
            #/ assign selB_`i`_`j` = (control == 1'b1) ? B_`i`_`j` : B_`i`_`j`_d`db`;
        pass
    else:
        for pe in unique_pe_addresses:
            i, j = pe
            ii = i + pib
            jj = j + pjb
            if (ii, jj) in unique_pe_addresses:
                portb = f'B_{i}_{j}_d{db}'
                #/  assign B_`ii`_`jj` = `portb`;
                pass

    #/ // Align C
    if passc[2] == 0:
        for pe in edgec:
            i, j = pe
            #/  wire [`QU_OUT.DWT * K-1`:0] S_`i`_`j`;
            for k in range(K):
                #/  assign S_`i`_`j`[`QU_OUT.DWT * (k+1)-1`:`QU_OUT.DWT * k`] = C_`i-int(passc[0])*k`_`j-int(passc[1])*k`;
                # #/ `type(passc[0])`
                pass 
        pass
    else:
        for pe in unique_pe_addresses:
            i, j = pe
            ii = i + pic
            jj = j + pjc
            if (ii, jj) in unique_pe_addresses:
                portc = f'C_{i}_{j}_d{dc}'
                #/  assign P_`ii`_`jj` = `portc`;
                pass
    #/ // Assign Input to edge PEs
    for pe_address in edgea:
        i, j = pe_address
        daa = starta[i, j]
        inst_ports_daa = {
            "i_data": f"InA_{i}_{j}",
            "o_data": f"A_{i}_{j}"
        }
        if daa > 0:
            inst_ports_daa["i_clk"] = "i_clk"
            if IF_RST_N[0]:
                inst_ports_daa["i_rst_n"] = "i_rst_n"

        ModuleDelay(DWT = QU_IN_A.DWT, N_CLK = daa, IF_RST_N = IF_RST_N[0], PORTS = inst_ports_daa)


    for pe_address in edgeb:
        i, j = pe_address
        dbb = startb[i, j]
        inst_ports_dbb = {
            "i_data": f"InB_{i}_{j}",
            "o_data": f"B_{i}_{j}"
        }
        if dbb > 0:
            inst_ports_dbb["i_clk"] = "i_clk"
            if IF_RST_N[1]:
                inst_ports_dbb["i_rst_n"] = "i_rst_n"

        ModuleDelay(DWT = QU_IN_B.DWT, N_CLK = dbb, IF_RST_N = IF_RST_N[1], PORTS = inst_ports_dbb)

    #/ // Assign Output to edge PEs
    if passc[2] == 0:
        for pe_address in edgec:
            i, j = pe_address 
            inst_ports_addert={
                "i_data": f"S_{i}_{j}",
                "o_data": f"OutC_{i}_{j}",
                "i_clk" : "i_clk"         
            }
            if IF_RST_N[1]:
                inst_ports_addert["i_rst_n"] = "i_rst_n"
            ModuleAdderTree(QU_IN=QU_OUT, QU_OUT=QU_OUT, N_PIPELINES=AdderTree_PIPELINES, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N[1], N_INPUTS=K, PORTS = inst_ports_addert)   
    else:
        for pe_address in edgec:
            i, j = pe_address
            #/ assign OutC_`i`_`j` = C_`i`_`j`_d1;

        
        

    


    #/  // Instantiate PEs
    if passc[0]==0 and passc[1]==0:
        for pe in unique_pe_addresses:
            i, j = pe
            pe_ports = {
                "i_data_1": f"A_{i}_{j}",
                "i_data_2": f"B_{i}_{j}",
                "i_data_3": f"P_{i}_{j}",
                "i_sel": "control",
                "o_data": f"C_{i}_{j}"
            }
            ModulePEinter(QU_IN_1 = QU_IN_A, QU_IN_2=QU_IN_B, QU_IN_3=QU_OUT, QU_OUT=QU_OUT, passc=passc, N_PIPELINES=0, QU_MODE = QU_MODE, OF_MODE = OF_MODE, IF_RST_N=False, PORTS = pe_ports)
    elif passc[2] == 0:
        for pe in unique_pe_addresses:
            i, j = pe
            if passb[0] == 0 and passb[1] == 0:
                pe_ports = {
                    "i_data_1": f"A_{i}_{j}",
                    "i_data_2": f"selB_{i}_{j}",
                    "o_data": f"C_{i}_{j}"
                }
            else:
                pe_ports = {
                    "i_data_1": f"A_{i}_{j}",
                    "i_data_2": f"B_{i}_{j}",
                    "o_data": f"C_{i}_{j}"
                }
            ModuleMul(QU_IN_1 = QU_IN_A, QU_IN_2=QU_IN_B, QU_OUT=QU_OUT, N_PIPELINES=0, QU_MODE = QU_MODE, OF_MODE = OF_MODE, IF_RST_N=False, PORTS = pe_ports)              
    else:
        for pe in unique_pe_addresses:
            i, j = pe
            if pe in In_C:
                pe_ports = {
                    "i_data_1": f"A_{i}_{j}",
                    "i_data_2": f"B_{i}_{j}",
                    "o_data": f"C_{i}_{j}"
                }
                ModuleMul(QU_IN_1 = QU_IN_A, QU_IN_2=QU_IN_B, QU_OUT=QU_OUT, N_PIPELINES=0, QU_MODE = QU_MODE, OF_MODE = OF_MODE, IF_RST_N=False, PORTS = pe_ports)              
            else:
                pe_ports = {
                    "i_data_1": f"A_{i}_{j}",
                    "i_data_2": f"B_{i}_{j}",
                    "i_data_3": f"P_{i}_{j}",
                    "o_data": f"C_{i}_{j}"
                }
                ModulePEinter(QU_IN_1 = QU_IN_A, QU_IN_2=QU_IN_B, QU_IN_3=QU_OUT, QU_OUT=QU_OUT,passc=passc, N_PIPELINES=0, QU_MODE = QU_MODE, OF_MODE = OF_MODE, IF_RST_N=False, PORTS = pe_ports)
    #/  // Delays for A
    max_i_np = np.max([addr[1] for addr in unique_pe_addresses])
 
    for pe in unique_pe_addresses:
        i, j = pe
        inst_ports_da = {
            "i_data": f"A_{i}_{j}",
            "o_data": f"A_{i}_{j}_d{da}"
        }
        if da > 0:
            inst_ports_da["i_clk"] = "i_clk"
            if IF_RST_N[i*(max_i_np+1)+j]:
                inst_ports_da["i_rst_n"] = "i_rst_n"

        ModuleDelay(DWT = QU_IN_A.DWT, N_CLK = da, IF_RST_N = IF_RST_N[i*(max_i_np+1)+j], PORTS = inst_ports_da)

    #/  // Delays for B
    for pe in unique_pe_addresses:
        i, j = pe
        if passb[0] == 0 and passb[1] == 0:
            inst_ports_db = {
                "i_data": f"selB_{i}_{j}",
                "o_data": f"B_{i}_{j}_d{db}"
            }
        else:
            inst_ports_db = {
                "i_data": f"B_{i}_{j}",
                "o_data": f"B_{i}_{j}_d{db}"
            }
        if db > 0:
            inst_ports_db["i_clk"] = "i_clk"
            if IF_RST_N[i*(max_i_np+1)+j]:
                inst_ports_db["i_rst_n"] = "i_rst_n"

        ModuleDelay(DWT = QU_IN_B.DWT, N_CLK = db, IF_RST_N = IF_RST_N[i*(max_i_np+1)+j], PORTS = inst_ports_db)

    #/  // Delays for C
    for pe in unique_pe_addresses:
        i, j = pe
        inst_ports_dc = {
            "i_data": f"C_{i}_{j}",
            "o_data": f"C_{i}_{j}_d{dc}"
        }
        if dc > 0:
            inst_ports_dc["i_clk"] = "i_clk"
            if IF_RST_N[i*(max_i_np+1)+j]:
                inst_ports_dc["i_rst_n"] = "i_rst_n"

        ModuleDelay(DWT = QU_OUT.DWT, N_CLK = dc, IF_RST_N = IF_RST_N[i*(max_i_np+1)+j], PORTS = inst_ports_dc)
        
    #/ endmodule