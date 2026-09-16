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
from Generator.BasicModules.Comp import ModuleComp



# ModuleTb tests the top module of the design, and it generates a testbench

@convert
def ModuleTbComp(QU_IN_1, QU_IN_2, QU_OUT, N_CLK, IF_RST_N, QU_MODE, OF_MODE, io_file_dir="../..",N_FRAMES=100, IF_GIDX=True, IF_LIDX=True, IF_EIDX=True, IF_GVAL=True, IF_LVAL=True):
    #/ `timescale 1ns/1ps
    #/ module TbComp;
    #/ // Inputs
    #/ reg [`QU_IN_1.DWT`-1:0] Input_i_data_1;
    #/ reg [`QU_IN_2.DWT` -1:0] Input_i_data_2;
    #/ reg [`QU_IN_1.DWT`-1:0] i_data_1;
    #/ reg [`QU_IN_2.DWT` -1:0] i_data_2;
    #/ reg clk;
    #/ reg i_rst_n;
    #/ // Outputs
    #/ wire o_gidx;
    #/ wire o_lidx;
    #/ wire o_eidx;
    #/ wire [`QU_OUT.DWT`-1:0] o_gval;
    #/ wire [`QU_OUT.DWT`-1:0] o_lval;
    #/ // Input ready and Output ready Indicators
    #/ reg Input_rdy;
    #/ reg Output_rdy;
    #/ // Instantiate the DUT
    tb_module_name = "TbComp"
    START_CYCLES=3
    inst_ports = {
        "i_data_1":"i_data_1",
        "i_data_2":"i_data_2",
        "o_gidx":"o_gidx",
        "o_lidx": "o_lidx",
        "o_eidx": "o_eidx",
        "o_gval": "o_gval",
        "o_lval": "o_lval",
        "i_rst_n":"i_rst_n",
        "i_clk":"clk",
    }
    #/ // Instantiate the DUT
    ModuleComp(PORTS = inst_ports, QU_IN_1 = QU_IN_1, QU_IN_2 = QU_IN_2, QU_OUT = QU_OUT, N_PIPELINES = N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N = IF_RST_N, IF_GIDX = IF_GIDX, IF_LIDX = IF_LIDX, IF_EIDX = IF_EIDX, IF_GVAL = IF_GVAL, IF_LVAL = IF_LVAL)

    #/ // Drive clk signal
    PyTB.Moduledrive_clk(port = "clk", period = 10, OUTMODE = "PRINT")

    #/ // Initialize Inputs
    PyTB.ModuleInitialize(ports = ["i_data_1","i_data_2"],OUTMODE = "PRINT")


    #/ // Drive rst signal
    PyTB.Moduledrive_arst(port = "i_rst_n",start=1, last=1, OUTMODE = "PRINT")



    # Note: Input data is generated in CppRun module.
    # The root directory is ./RTL/Testcases

    input_files_dir = os.path.join(io_file_dir,"Input_Files")
    output_files_dir = os.path.join(io_file_dir,"Output_Files")
    # Note: Input data is generated in CppRun module.

    #/ // Drive input signal

    PyTB.Moduledrive_input_signal(clk = "clk",ports=["i_data_1","i_data_2"], files = ["Comp_i_data_1.txt","Comp_i_data_2.txt"],input_file_dir=input_files_dir,n_latency=30, n_cycle = 1, n_excites = N_FRAMES, OUTMODE = "PRINT")

    #/ // Dump output signal

    print(output_files_dir)
    PyTB.Moduledump(clk="clk", grp= "output_data", output_file_dir= output_files_dir, names=["Comp_o_gidx","Comp_o_lidx","Comp_o_eidx","Comp_o_gval","Comp_o_lval"], handles=["o_gidx","o_lidx","o_eidx","o_gval","o_lval"], n_latency= N_CLK, if_end= True, end_wait=100, n_cycle=1, n_dump = N_FRAMES, OUTMODE = "PRINT")
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
