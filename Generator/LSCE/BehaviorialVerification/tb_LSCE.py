# coding = utf-8
# Last Modified Date: 2025.3.12
# Author: Jiayan Xu
# Author: LiPtP
# Description:
# A Verithon file generating Verilog testbench.

import pdb
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

# Modify version at here
import sys
import os
import PyTB
from PyTU import QuMode, OfMode, QuType
import math

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# change the version of the module by modifing parameters.py
'''
You need to update module name here if you change the DUT.
'''
DUT_NAME = "LSCE" 
module_name = f"designs.{DUT_NAME}"
try:
    module = __import__(module_name, fromlist=[f"Module{DUT_NAME}"])
    ModuleLSCE = getattr(module, f"Module{DUT_NAME}")
except ModuleNotFoundError:
    print('module version not found.')


@convert 
def ModuleTbLSCE(N_T:int, N_R:int, P_T:int, P_R:int, QU_Y:QuType, QU_P:QuType, QU_H:QuType, QU_M_V:QuType, QU_MODE:QuMode, OF_MODE:OfMode, N_PIPELINES:list=[1, 1], CLOCK_PERIOD_NS:float=10.0, input_file_dir="../../Input_Files", output_file_dir="../../Output_Files", N_FRAMES=50):
    # Parse the input arguments
    STG_T = math.ceil(N_T / P_T)
    # End of Input Argument Parsing #
    #/  `timescale 1ns/1ps
    #/  module TbLSCE;
    #/  //======== Data Input and Output Ports ========//
    #/  reg [`P_R`*`P_T`*`QU_Y.DWT`-1:0] Input_i_Y, i_Y;
    #/  reg [`P_T`*`QU_P.DWT`-1:0] Input_i_P, i_P;
    #/  wire [`P_R`*`QU_H.DWT`-1:0] o_H;
    if STG_T > 1:
        #/  reg [1:0] Input_i_ctrl_stg, i_ctrl_stg;
        pass
    
    #/  reg clk;
    #/  reg en;
    #/  //======== Module Instantiation ========//
    inst_ports = {
        "i_Y": "i_Y",
        "i_P": "i_P",
        "o_H": "o_H",
        "i_clk": "clk"
    }
    if STG_T > 1:
        inst_ports["i_ctrl_stg"] = "i_ctrl_stg"
    ModuleLSCE(N_T=N_T, N_R=N_R, P_T=P_T, P_R=P_R, QU_Y=QU_Y, QU_P=QU_P, QU_H=QU_H, QU_M_V=QU_M_V, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_PIPELINES=N_PIPELINES, PORTS=inst_ports)
    
    #/  //======== Signal Drive ========//
    #   Clk
    PyTB.Moduledrive_clk(port = "clk", period = CLOCK_PERIOD_NS, OUTMODE = "PRINT")
    #   Initialization
    PyTB.ModuleInitialize(ports = ["i_Y", "Input_i_Y", "i_P", "Input_i_P", "en"], OUTMODE = "PRINT")
    #   Excitation
    PyTB.Moduledrive_input_signal(ports = ["i_Y", "i_P"], files = ["i_Y.txt", "i_P.txt"], n_cycle = 1, if_en = True, OUTMODE = "PRINT", input_file_dir=input_file_dir)
    if STG_T > 1:
        PyTB.Moduledrive_input_signal(ports = ["i_ctrl_stg"], files = ["i_ctrl_stg.txt"], n_cycle = 1, if_en = True, OUTMODE = "PRINT", input_file_dir=input_file_dir)
    TotalLatency = N_PIPELINES[0] + N_PIPELINES[1]
    if STG_T > 1:
        TotalLatency += STG_T
    #   Dump Input
    PyTB.Moduledump(grp="in", names = ["i_Y_out", "i_P_out"], handles = ["i_Y", "i_P"], n_latency = 0, n_cycle = 1, n_dump = N_FRAMES*STG_T, if_end = False, OUTMODE = "PRINT", output_file_dir=output_file_dir)
    if STG_T > 1:
        PyTB.Moduledump(grp="in_stg", names = ["i_ctrl_stg_out"], handles = ["i_ctrl_stg"], n_latency = 0, n_cycle = 1, n_dump = (N_FRAMES*STG_T)+TotalLatency-STG_T, if_end = False, OUTMODE = "PRINT", output_file_dir=output_file_dir)
    #   Dump Output
    PyTB.Moduledump(grp="out", names=["o_H"], handles=["o_H"], n_latency=TotalLatency, n_cycle=STG_T, n_dump=N_FRAMES, if_end=True, OUTMODE="PRINT", output_file_dir=output_file_dir)
    
    new_tb_name = "TbLSCE" + PyTB.int_to_hex_with_length(1)
    
    #/ initial begin
    #/     $dumpfile("wave.vcd");
    #/     $dumpvars(0, `new_tb_name`);
    #/ end
    #/ endmodule


