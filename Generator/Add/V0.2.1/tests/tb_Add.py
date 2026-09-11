# coding = utf-8
# Date: 2025.2.22
# Author: Jiayan Xu
# Author: LiPtP
# Description:
# A Verithon file generating Verilog testbench and Cpp Verification Files.


import pdb
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

# Modify version at here
import sys
import os
import PyTB

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# change the version of the module by modifing parameters.py
'''
You need to update module name here if you change the DUT.
'''
DUT_NAME = "Add" 
module_name = f"designs.{DUT_NAME}"
try:
    module = __import__(module_name, fromlist=[f"Module{DUT_NAME}"])
    ModuleAdd = getattr(module, f"Module{DUT_NAME}")
except ModuleNotFoundError:
    print('module version not found.')



# ModuleTb tests the top module of the design, and it generates a testbench 

@convert 
def ModuleTbAdd(QU_IN_1, QU_IN_2, QU_OUT, N_CLK, IF_RST_N, QU_MODE, OF_MODE, input_file_dir="../..",N_FRAMES=100, CLK_PERIOD=10):
    #/ `timescale 1ns/1ps
    #/ module TbAdd;
    #/ // Inputs
    #/ reg [`QU_IN_1.DWT`-1:0] Input_i_data_1;
    #/ reg [`QU_IN_2.DWT` -1:0] Input_i_data_2;
    #/ reg [`QU_IN_1.DWT`-1:0] i_data_1;
    #/ reg [`QU_IN_2.DWT` -1:0] i_data_2;
    #/ reg clk;
    #/ reg en;
    #/ reg i_rst_n;
    #/ // Outputs
    #/ wire [`QU_OUT.DWT`-1:0] o_data;
    #/ // Input ready and Output ready Indicators
    #/ reg Input_rdy;
    #/ reg Output_rdy;
    #/ // Instantiate the DUT
    tb_module_name = "TbAdd"
    START_CYCLES=3
    inst_ports = {
        "i_data_1":"i_data_1",
        "i_data_2":"i_data_2",
        "o_data": "o_data",
        "i_clk":"clk",
    }
    if (any(IF_RST_N) if isinstance(IF_RST_N, list) else IF_RST_N):
        inst_ports["i_rst_n"] = "i_rst_n"
    #/ // Instantiate the DUT
    ModuleAdd(PORTS = inst_ports, QU_IN_1 = QU_IN_1, QU_IN_2 = QU_IN_2, QU_OUT = QU_OUT, N_PIPELINES = N_CLK, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N = IF_RST_N)
    
    #/ // Drive clk signal
    PyTB.Moduledrive_clk(port = "clk", period = CLK_PERIOD, OUTMODE = "PRINT")

    #/ // Initialize Inputs
    PyTB.ModuleInitialize(ports = ["i_data_1","i_data_2"],OUTMODE = "PRINT")

    #/ // Enable signal
    PyTB.Moduledrive_enable(port = "en", start = 3, clk = "clk", OUTMODE = "PRINT")

    #/ // Drive rst signal
    PyTB.Moduledrive_arst(port = "i_rst_n",start=1, last=1, OUTMODE = "PRINT")

    #/ // Drive input ready and output ready signal
    PyTB.Moduledrive_rdy(port_en = "en", port_in = "Input_rdy", port_out = "Output_rdy",clk_period = CLK_PERIOD, clk= "clk", start = START_CYCLES, latency = N_CLK, N_excitations=2*(N_FRAMES+10),OUTMODE = "PRINT")

    # Note: Input data is generated in CppRun module.

    #/ // Drive input signal
    input_file_name_1 = os.path.join(input_file_dir,"Input_Files/add_i_data_1.txt").replace("\\", "/")
    input_file_name_2 = os.path.join(input_file_dir,"Input_Files/add_i_data_2.txt").replace("\\", "/")
    PyTB.Moduledrive_input(port = "i_data_1",fistream_port="Input_i_data_1", wait_cycles=2 ,file_name =input_file_name_1, OUTMODE = "PRINT")
    PyTB.Moduledrive_input(port = "i_data_2",fistream_port="Input_i_data_2", wait_cycles=2 ,file_name =input_file_name_2, OUTMODE = "PRINT")

    #/ // Dump output signal
    
    output_file_name = os.path.join(input_file_dir,"Output_Files/add_o_data.txt").replace("\\", "/")
    PyTB.Moduledump_output(port = "o_data",fostream_port="Output_o_data", wait_cycles=2 ,file_name = output_file_name, N_excitations=N_FRAMES, OUTMODE = "PRINT")
    
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


