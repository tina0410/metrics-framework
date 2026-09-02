# coding = utf-8
# Date: 2025.2.22
# Author: Jiayan Xu
# Author: LiPtP
# Author: Yifang Dai
# Description:
# A Verithon file generating Verilog testbench and Cpp Verification Files.


import pdb
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from collections import OrderedDict
from TbDelay import ModuleTbDelay
# Modify version at here
import sys
import os
import PyTB
import math
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# change the version of the module by modifing parameters.py
'''
You need to update module name here if you change the DUT.
'''
DUT_NAME = "lNSA" 
module_name = f"designs.{DUT_NAME}"
try:
    module = __import__(module_name, fromlist=[f"Module{DUT_NAME}"])
    ModulePE = getattr(module, f"Module{DUT_NAME}")
except ModuleNotFoundError:
    print('module version not found.')



# ModuleTb tests the top module of the design, and it generates a testbench 

@convert 
def ModuleTbPE(iterations, QU, IF_RST_N, QU_MODE, OF_MODE, In_A, start_time_a, start_time_b, In_B, In_C, Out_C, start_time_C, end_time_C, unique_pe_addresses, passa, passb, passc, Eq, code_line, AdderTree_PIPELINES,transpose,input_file_dir="../..", N_FRAMES=1, CLOCK_PERIOD_NS=10.0, I=3, J=4, K=5):
    outputs = {eq[0] for eq in Eq}  # {'C', 'E'}
    input_info = OrderedDict()  # 存储变量及其首次出现的位置

    for eq_idx, eq in enumerate(Eq):
        for var_idx, var in enumerate(eq[1:], start=1):  # 跳过输出变量（索引0）
            if var not in input_info and var not in outputs:
                input_info[var] = (eq_idx, var_idx)

    input_elements = list(input_info.keys())  # 保持顺序的输入变量 ['A', 'B', 'D']
    input_indices = list(input_info.values())  # 对应的首次出现位置 [(0, 1), (0, 2), (1, 1)]
    
    all_outputs = []
    all_indices = []
    for i, eq in enumerate(Eq):
        all_outputs.append(eq[0])  # 收集输出变量
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
    #/ `timescale 1ns/1ps
    #/ module TbPE;
    #/ // Inputs
    Init=[]
    Infiles=[]
    print("Eqqq:",Eq[len(Eq)-1][0])#Eq: [['ymf', 'HT', 'y'], ['x1', 'D', 'ymf'], ['b2', 'H', 'x1'], ['d2', 'HT', 'b2'], ['Dx1', 'D', 'x1'], ['x2', 'x1', 'a', 'Dx1', 'D', 'd2']]
    for a, b in input_indices:
        Init.append(f"i_data_{Eq[a][b]}")
        Infiles.append(f"PE_i_data_{Eq[a][b]}.txt")
        if b==1:
            if Eq[a][b] in {"D1", "D2", "D4"}:
                #/ reg [`QU[Eq[a][b]].DWT `-1:0] Input_i_data_`Eq[a][b]` = `QU[Eq[a][b]].DWT`'b0;
                #/ reg [`QU[Eq[a][b]].DWT `-1:0] i_data_`Eq[a][b]`=`QU[Eq[a][b]].DWT `'b0 ;
                #/ wire [`QU[Eq[a][b]].DWT `-1:0] i_data_`Eq[a][b]`_d;
                pass
            else:
                #/ reg [`QU[Eq[a][b]].DWT * max(I[a], K[a])`-1:0] Input_i_data_`Eq[a][b]` = `QU[Eq[a][b]].DWT * max(I[a], K[a])`'b0;
                #/ reg [`QU[Eq[a][b]].DWT * max(I[a], K[a])`-1:0] i_data_`Eq[a][b]`=`QU[Eq[a][b]].DWT * max(I[a], K[a])`'b0 ;
                #/ wire [`QU[Eq[a][b]].DWT * max(I[a], K[a])`-1:0] i_data_`Eq[a][b]`_d;
                pass
        else:
            #/ reg [`QU[Eq[a][b]].DWT * K[a] * J[a]`-1:0] Input_i_data_`Eq[a][b]` = `QU[Eq[a][b]].DWT * K[a] * J[a]`'b0;
            #/ reg [`QU[Eq[a][b]].DWT * K[a] * J[a]`-1:0] i_data_`Eq[a][b]`=`QU[Eq[a][b]].DWT * K[a] * J[a]`'b0 ;
            #/ wire [`QU[Eq[a][b]].DWT * K[a] * J[a]`-1:0] i_data_`Eq[a][b]`_d;
            pass
    #/ reg clk;
    #/ reg PEen;
    #/ reg i_rst_n;
    for i in range(1+len(Eq)//4*2):
        #/ reg control_`i`;
        #/ reg active_`i` = 0;
        #/ reg [20:0] counter_`i` = 21'b0; 
        pass
    
    
    for i in range(1+len(Eq)//4*2):
        #/ always @(posedge clk) begin
        #/     if (!active_`i`) begin
        #/         // 初始等待6个时钟周期
        if i%2==0:
            if i>1:
                #/    if (counter_`i` == `2+AdderTree_PIPELINES+1+I[0]+(i//2-1)*(I[0]+3+AdderTree_PIPELINES+1)`) begin  // 从0开始计数，5表示6个周期
                pass
            else:
                #/    if (counter_`i` == `2+I[0]*(i//2)`) begin  // 从0开始计数，5表示6个周期     
                pass           
            pass
        else:
            #/    if (counter_`i` == `3+AdderTree_PIPELINES+(i//2)*(I[0]+3+AdderTree_PIPELINES+1)`) begin  // 从0开始计数，5表示6个周期
            pass
        #/             active_`i` <= 1'b1;
        #/             counter_`i` <= 0;
        #/             control_`i` <= 1'b1;      // 第一个脉冲
        #/         end
        #/         else begin
        #/             counter_`i` <= counter_`i` + 1;
        #/             control_`i` <= 1'b0;
        #/         end
        #/     end
        #/     else begin
        #/         // 正常工作阶段，每5个时钟周期一个脉冲
        #/         if (counter_`i` == `I[0]-1`) begin  // 从0开始计数，4表示5个周期
        #/             control_`i` <= 1'b1;      // 输出高电平
        #/             counter_`i` <= 0;       // 重置计数器
        #/         end
        #/         else begin
        #/             control_`i` <= 1'b0;      // 其他时间输出低电平
        #/             counter_`i` <= counter_`i` + 1;
        #/         end
        #/     end
        #/ end
        pass


    #/ // Outputs
    #/ wire [`QU[Eq[len(Eq)-1][0]].DWT * I[len(Eq)-1] * J[len(Eq)-1]`-1:0] o_data;
    #/ // Input ready and Output ready Indicators
    #/ // Instantiate the DUT
     
    if iterations == 3:
        inst_ports_H3 = {
            "i_data": "i_data_H3",
            "o_data": "i_data_H3_d" 
        }
        inst_ports_H3["i_clk"] = "clk"
        ModuleTbDelay(DWT = QU['H1'].DWT * I[2] , N_CLK = 1+AdderTree_PIPELINES+(I[0]+3+AdderTree_PIPELINES+1)*2, IF_RST_N = False, PORTS = inst_ports_H3)   
         
        inst_ports_HT4 = {
            "i_data": "i_data_HT4",
            "o_data": "i_data_HT4_d" 
        }
        inst_ports_HT4["i_clk"] = "clk"
        ModuleTbDelay(DWT = QU['H1'].DWT * I[2] , N_CLK = I[0]+AdderTree_PIPELINES+1+(I[0]+3+AdderTree_PIPELINES+1)*2, IF_RST_N = False, PORTS = inst_ports_HT4)        
        inst_ports_D6 = {
            "i_data": "i_data_D6",
            "o_data": "i_data_D6_d" 
        }
        inst_ports_D6["i_clk"] = "clk"
        ModuleTbDelay(DWT = QU['D1'].DWT , N_CLK = I[0]+AdderTree_PIPELINES+1+(I[0]+3+AdderTree_PIPELINES+1)*2+AdderTree_PIPELINES, IF_RST_N = False, PORTS = inst_ports_D6)

        inst_ports_D7 = {
            "i_data": "i_data_D7",
            "o_data": "i_data_D7_d" 
        }
        inst_ports_D7["i_clk"] = "clk"
        ModuleTbDelay(DWT = QU['D1'].DWT , N_CLK = I[0]+AdderTree_PIPELINES+1+(I[0]+3+AdderTree_PIPELINES+1)*2+AdderTree_PIPELINES+1, IF_RST_N = False, PORTS = inst_ports_D7)
            
    inst_ports_H1 = {
         "i_data": "i_data_H1",
         "o_data": "i_data_H1_d" 
    }
    inst_ports_H1["i_clk"] = "clk"
    ModuleTbDelay(DWT = QU['H1'].DWT * I[2] , N_CLK = 1+AdderTree_PIPELINES, IF_RST_N = False, PORTS = inst_ports_H1)
    
    inst_ports_H2 = {
         "i_data": "i_data_H2",
         "o_data": "i_data_H2_d" 
    }
    inst_ports_H2["i_clk"] = "clk"
    ModuleTbDelay(DWT = QU['H1'].DWT * I[2] , N_CLK = 1+AdderTree_PIPELINES+(I[0]+3+AdderTree_PIPELINES+1), IF_RST_N = False, PORTS = inst_ports_H2)

    inst_ports_HT1 = {
         "i_data": "i_data_HT1",
         "o_data": "i_data_HT1_d" 
    }
    ModuleTbDelay(DWT = QU['H1'].DWT * I[2] , N_CLK = 0, IF_RST_N = False, PORTS = inst_ports_HT1)
        
    inst_ports_y = {
         "i_data": "i_data_y",
         "o_data": "i_data_y_d" 
    }
    ModuleTbDelay(DWT = QU['y'].DWT *  K[0], N_CLK = 0, IF_RST_N = False, PORTS = inst_ports_y)
    
    inst_ports_a = {
         "i_data": "i_data_a",
         "o_data": "i_data_a_d" 
    }
    ModuleTbDelay(DWT = QU['a'].DWT , N_CLK = 0, IF_RST_N = False, PORTS = inst_ports_a)
    
    inst_ports_HT2 = {
         "i_data": "i_data_HT2",
         "o_data": "i_data_HT2_d" 
    }
    inst_ports_HT2["i_clk"] = "clk"
    ModuleTbDelay(DWT = QU['H1'].DWT * I[2] , N_CLK = I[0]+AdderTree_PIPELINES+1, IF_RST_N = False, PORTS = inst_ports_HT2)

    inst_ports_HT3 = {
         "i_data": "i_data_HT3",
         "o_data": "i_data_HT3_d" 
    }
    inst_ports_HT3["i_clk"] = "clk"
    ModuleTbDelay(DWT = QU['H1'].DWT * I[2] , N_CLK = I[0]+AdderTree_PIPELINES+1+(I[0]+3+AdderTree_PIPELINES+1), IF_RST_N = False, PORTS = inst_ports_HT3)

    inst_ports_D1 = {
         "i_data": "i_data_D1",
         "o_data": "i_data_D1_d" 
    }
    inst_ports_D1["i_clk"] = "clk"
    ModuleTbDelay(DWT = QU['D1'].DWT , N_CLK = AdderTree_PIPELINES, IF_RST_N = False, PORTS = inst_ports_D1)
   
    inst_ports_D2 = {
         "i_data": "i_data_D2",
         "o_data": "i_data_D2_d" 
    }
    inst_ports_D2["i_clk"] = "clk"
    ModuleTbDelay(DWT = QU['D1'].DWT , N_CLK = I[0]+AdderTree_PIPELINES+AdderTree_PIPELINES+1, IF_RST_N = False, PORTS = inst_ports_D2)

    inst_ports_D3 = {
         "i_data": "i_data_D3",
         "o_data": "i_data_D3_d" 
    }
    inst_ports_D3["i_clk"] = "clk"
    ModuleTbDelay(DWT = QU['D1'].DWT , N_CLK = I[0]+AdderTree_PIPELINES+AdderTree_PIPELINES+1+1, IF_RST_N = False, PORTS = inst_ports_D3)

    inst_ports_D4 = {
         "i_data": "i_data_D4",
         "o_data": "i_data_D4_d" 
    }
    inst_ports_D4["i_clk"] = "clk"
    ModuleTbDelay(DWT = QU['D1'].DWT , N_CLK = I[0]+AdderTree_PIPELINES+1+(I[0]+3+AdderTree_PIPELINES+1)+AdderTree_PIPELINES, IF_RST_N = False, PORTS = inst_ports_D4)

    inst_ports_D5 = {
         "i_data": "i_data_D5",
         "o_data": "i_data_D5_d" 
    }
    inst_ports_D5["i_clk"] = "clk"
    ModuleTbDelay(DWT = QU['D1'].DWT , N_CLK = I[0]+AdderTree_PIPELINES+1+(I[0]+3+AdderTree_PIPELINES+1)+AdderTree_PIPELINES+1, IF_RST_N = False, PORTS = inst_ports_D5)
    
    tb_module_name = "TbPE"
    START_CYCLES=3
    inst_ports = {
        "o_data": "o_data",
        "en":"PEen",
        "i_rst_n":"i_rst_n",
        "i_clk":"clk"
    }
    for i in range(1+len(Eq)//4*2):
        inst_ports[f"control_{i}"] = f"control_{i}"
        pass
    for a, b in input_indices:
        inst_ports[f"i_data_{Eq[a][b]}"] = f"i_data_{Eq[a][b]}_d"
    #/ // Instantiate the DUT
    ModulePE(PORTS = inst_ports, QU = QU,passa=passa, passb=passb, passc=passc, edgea=In_A, start_time_a=start_time_a,  start_time_b=start_time_b, edgeb=In_B, In_C=In_C, edgec=Out_C, start_time_C=start_time_C, unique_pe_addresses=unique_pe_addresses,I=I, J=J, K=K, Eq=Eq, transpose=transpose, code_line=code_line,AdderTree_PIPELINES=AdderTree_PIPELINES, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N = IF_RST_N)
    
    #/ // Drive clk signal
    PyTB.Moduledrive_clk(port = "clk", period = CLOCK_PERIOD_NS, OUTMODE = "PRINT")

    #/ // Initialize Inputs
    PyTB.ModuleInitialize(ports = Init,OUTMODE = "PRINT")

    PyTB.Moduledrive_enable(port = "PEen", start = 4, clk = "clk", OUTMODE = "PRINT")
    #/ // Drive rst signal
    PyTB.Moduledrive_arst(port = "i_rst_n", clk="clk", start=1, last=1, OUTMODE = "PRINT")

    # Note: Input data is generated in CppRun module.

    #/ // Drive input signal
    input_file_name_1 = input_file_dir.rstrip("/\\") + "/Input_Files"
    input_file_name_2 = input_file_dir.rstrip("/\\") + "/Input_Files"

    #/ reg en;
    #/ initial begin
    #/    en <= 0;
    #/ end
    for i in range(len(Init)):
        PyTB.Moduledrive_input_signal(clk = "clk",grp= f"input_data{Init[i]}", ports=[Init[i]], files = [Infiles[i]],input_file_dir=input_file_name_1, n_latency=2, n_cycle = 1, n_excites = 300, OUTMODE = "PRINT")
    #/ // Dump output signal using mode A
    output_file_name = input_file_dir.rstrip("/\\") + "/Output_Files"
    print([Init[1]])
    
    handles1=[]
    n_stamps1=[]
    indexc=0
    for pe_address in Out_C[len(Eq)-1]:
        i, j = pe_address
        for t in range(start_time_C[len(Eq)-1][i,j], end_time_C[len(Eq)-1][i,j]+1):
            handles1.append(f"o_data[{indexc+1}*{QU[Eq[len(Eq)-1][0]].DWT}-1:{indexc}*{QU[Eq[len(Eq)-1][0]].DWT}]")
            n_stamps1.append(t)
        indexc+=1
            #PyTB.Moduledump( clk="clk", grp= f"output_data{i}{j}", output_file_dir= output_file_name, names=[f"PE_o_data"], handles=[f"o_data[{i*J+j+1}*{QU_OUT.DWT}-1:{i*J+j}*{QU_OUT.DWT}]"], n_latency=t, if_end= True, end_wait=100,  n_cycle=1, n_dump = N_FRAMES, OUTMODE = "PRINT" )
    zipped = zip(n_stamps1, range(len(n_stamps1)), handles1)  # (value, index, list2_item)
    sorted_zipped = sorted(zipped, key=lambda x: (x[0], x[1]))  # 按 list1 的值和原始索引排序

    # 解压得到排序后的 list1 和 list2
    n_stamps = [x[0] for x in sorted_zipped]
    handles = [x[2] for x in sorted_zipped]
    
    n_stamps = n_stamps+ [x[0] + I[0] for x in sorted_zipped]
    handles = handles +[x[2] for x in sorted_zipped]
    n_stamps = n_stamps+ [x[0] + 2*I[0] for x in sorted_zipped]
    handles = handles +[x[2] for x in sorted_zipped]
    for tnn in range(len(Eq)-1):
        n_stamps = [x + min(start_time_C[tnn].values()) for x in n_stamps]
    PyTB.Moduledump( clk="clk", grp= "output_data", output_file_dir= output_file_name, names=["PE_o_data"], handles=handles, if_end= True, end_wait=100,  n_dump = N_FRAMES, OUTMODE = "PRINT" ,n_stamps= n_stamps)

    # generated_tbs = moduleloader.getParams("Tb")
    # n_generated_tbs = 0
    # if generated_tbs is not None:
    #     n_generated_tbs = len(generated_tbs)

    # n_generated_tb_str = PyTB.int_to_hex_with_length(n_generated_tbs+1)
    # new_tb_name = tb_module_name + n_generated_tb_str
    new_tb_name = tb_module_name + PyTB.int_to_hex_with_length(1)

    #/ initial begin
    #/     $dumpfile("wave.vcd");
    #/     $dumpvars(0, `new_tb_name`);
    #/ end
    #/ endmodule


