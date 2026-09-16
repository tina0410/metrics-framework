# coding = utf-8
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description:
# A Verithon file generating Verilog testbench.


import pdb
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

import os
import PyTB

from Generator.BasicModules.Sub import ModuleSub

# ModuleTb tests the top module of the design, and it generates a testbench

@convert
def ModuleTbSub(QU_IN_1, QU_IN_2, QU_OUT, N_CLK, IF_RST_N, QU_MODE, OF_MODE, io_file_dir="../..",N_FRAMES=100):
    #/ `timescale 1ns/1ps
    #/ module TbSub;
    #/ // Inputs
    #/ reg [`QU_IN_1.DWT`-1:0] Input_i_data_1;
    #/ reg [`QU_IN_2.DWT` -1:0] Input_i_data_2;
    #/ reg [`QU_IN_1.DWT`-1:0] i_data_1;
    #/ reg [`QU_IN_2.DWT` -1:0] i_data_2;
    #/ reg clk;
    #/ reg i_rst_n;
    #/ reg enable;
    #/ // Outputs
    #/ wire [`QU_OUT.DWT`-1:0] o_data;
    #/ // Input ready and Output ready Indicators
    #/ reg Input_rdy;
    #/ reg Output_rdy;
    #/ // Instantiate the DUT
    tb_module_name = "TbSub"
    START_CYCLES=3
    inst_ports = {
        "i_data_1":"i_data_1",
        "i_data_2":"i_data_2",
        "o_data": "o_data",
        "i_rst_n":"i_rst_n",
        "i_clk":"clk",
    }
    #/ // Instantiate the DUT
    ModuleSub(PORTS = inst_ports, QU_IN_1 = QU_IN_1, QU_IN_2 = QU_IN_2, QU_OUT = QU_OUT, N_CLK = N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N = IF_RST_N)

    #/ // Drive clk signal
    PyTB.Moduledrive_clk(port = "clk", period = 10, OUTMODE = "PRINT")

    #/ // Initialize Inputs
    PyTB.ModuleInitialize(ports = ["i_data_1","i_data_2","enable"],OUTMODE = "PRINT")

    #/ // Drive rst signal
    PyTB.Moduledrive_arst(port = "i_rst_n",start=1, last=1, OUTMODE = "PRINT")

    # The root directory is ./RTL/Testcases
    input_files_dir = os.path.join(io_file_dir,"Input_Files")
    output_files_dir = os.path.join(io_file_dir,"Output_Files")
    # Note: Input data is generated in CppRun module.
    #/ // Drive input signal
    # Mode A2
    PyTB.Moduledrive_input_signal(clk = "clk", ports=["i_data_1","i_data_2"], files = ["sub_i_data_1.txt","sub_i_data_2.txt"], if_en= True, en_name= "enable", input_file_dir=input_files_dir, n_latency=30, n_cycle = 1, n_excites = N_FRAMES, OUTMODE = "PRINT")
    #/ // Dump output signal
    # Mode A2
    PyTB.Moduledump(clk="clk", grp= "output_data_A2", output_file_dir= output_files_dir, names=["sub_o_data"], handles=["o_data"], n_latency= N_CLK, if_end= True, end_wait=100, en="enable",n_cycle=1, n_dump = N_FRAMES, OUTMODE = "PRINT")


    new_tb_name = tb_module_name + PyTB.int_to_hex_with_length(1)
    #/ initial begin
    #/     $dumpfile("wave.vcd");
    #/     $dumpvars(0, `new_tb_name`);
    #/ end
    #/ endmodule
