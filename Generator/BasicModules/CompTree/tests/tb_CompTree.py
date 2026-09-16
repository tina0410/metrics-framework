# coding = utf-8
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description:
# A Verithon file generating Verilog testbench and Cpp Verification Files.


import pdb
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

# Modify version at here
import os
import PyTB
import math
from Generator.BasicModules.CompTree.CompTree import ModuleCompTree



# ModuleTb tests the top module of the design, and it generates a testbench

@convert
def ModuleTbCompTree(QU_IN, QU_OUT, N_CLK, IF_RST_N, QU_MODE, OF_MODE, io_file_dir="../..", N_FRAMES=100, N_INPUTS=10, CONFIG_MODE="A",IF_GIDX=False):
    n_layers = math.ceil(math.log2(N_INPUTS))
    #/ `timescale 1ns/1ps
    #/ module TbCompTree;
    #/ // Inputs
    #/ reg [`QU_IN.DWT * N_INPUTS`-1:0] Input_i_data;
    #/ reg [`QU_IN.DWT * N_INPUTS`-1:0] i_data;
    #/ reg clk;
    #/ reg i_rst_n;
    #/ // Outputs
    #/ wire [`QU_OUT.DWT`-1:0] o_gval;
    #/ wire [`n_layers`-1:0] o_gidx;
    #/ // Input ready and Output ready Indicators
    #/ reg Input_rdy;
    #/ reg Output_rdy;
    #/ // Instantiate the DUT
    tb_module_name = "TbCompTree"
    START_CYCLES=3
    inst_ports = {
        "i_data":"i_data",
        "o_gval": "o_gval",
        "o_gidx": "o_gidx",
        "i_rst_n":"i_rst_n",
        "i_clk":"clk",
    }
    #/ // Instantiate the DUT
    ModuleCompTree(PORTS = inst_ports, QU_IN = QU_IN, QU_OUT = QU_OUT, N_PIPELINES = N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N = IF_RST_N, N_INPUTS=N_INPUTS,IF_GIDX=IF_GIDX, CONFIG_MODE=CONFIG_MODE)

    #/ // Drive clk signal
    PyTB.Moduledrive_clk(port = "clk", period = 10, OUTMODE = "PRINT")

    #/ // Initialize Inputs
    PyTB.ModuleInitialize(ports = ["i_data"],OUTMODE = "PRINT")

    #/ // Drive rst signal
    PyTB.Moduledrive_arst(port = "i_rst_n",start=1, last=1, OUTMODE = "PRINT")


    # Note: Input data is generated in CppRun module.

    # #/ // Drive input signal
    # input_file_name_1 = os.path.join(input_file_dir,"Input_Files/CompTree_i_data.txt")
    # PyTB.Moduledrive_input(port = "i_data",fistream_port="Input_i_data", wait_cycles=2 ,file_name =input_file_name_1, OUTMODE = "PRINT")

    # #/ // Dump output signal

    # output_file_name = os.path.join(input_file_dir,"Output_Files/CompTree_o_gval.txt")
    # output_file_name2 = os.path.join(input_file_dir,"Output_Files/CompTree_o_gidx.txt")
    # PyTB.Moduledump_output(port = "o_gval",fostream_port="Output_o_data", wait_cycles=2 ,file_name = output_file_name, N_excitations=N_FRAMES, OUTMODE = "PRINT")
    # PyTB.Moduledump_output(port = "o_gidx",fostream_port="Output_o_gidx", wait_cycles=2 ,file_name = output_file_name2, N_excitations=N_FRAMES, OUTMODE = "PRINT")

    # Note: Input data is generated in CppRun module.

    # The root directory is ./RTL/Testcases
    input_files_dir = os.path.join(io_file_dir,"Input_Files")
    output_files_dir = os.path.join(io_file_dir,"Output_Files")
    # Note: Input data is generated in CppRun module.

    #/ // Drive input signal

    PyTB.Moduledrive_input_signal(clk = "clk",ports=["i_data"], files = ["CompTree_i_data.txt"],input_file_dir=input_files_dir,n_latency=30, n_cycle = 1, n_excites = 2*(N_FRAMES+10), OUTMODE = "PRINT")

    #/ // Dump output signal


    PyTB.Moduledump(clk="clk", grp= "output_data", output_file_dir= output_files_dir, names=["CompTree_o_gval","CompTree_o_gidx"], handles=["o_gval","o_gidx"], n_latency= N_CLK, if_end= True, end_wait=100, n_cycle=1, n_dump = N_FRAMES, OUTMODE = "PRINT")

    new_tb_name = tb_module_name + PyTB.int_to_hex_with_length(1)

    #/ initial begin
    #/     $dumpfile("wave.vcd");
    #/     $dumpvars(0, `new_tb_name`);
    #/ end
    #/ endmodule
