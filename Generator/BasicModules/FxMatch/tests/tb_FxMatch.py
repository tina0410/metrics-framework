# coding = utf-8
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description:
# A Verithon file generating Verilog testbench.

# Important Notes:
# Do not add any line breaks to a module function definition.
# To generate a testbench with different behavior, modify parameters *here*. Avoid modifications to PyTB.py.

from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader


import os
import PyTB

from Generator.BasicModules.FxMatch.FxMatch import ModuleFxMatch

@convert
def ModuleTbFxMatch(QU_IN, QU_OUT, N_CLK, IF_RST_N, QU_MODE, OF_MODE, io_file_dir="../..", N_FRAMES=50):
    #/ `timescale 1ns/1ps
    #/ module TbFxMatch;
    #/ // Inputs
    #/ reg [`QU_IN.DWT`-1:0] Input_i_data;
    #/ reg [`QU_IN.DWT`-1:0] i_data;
    #/ reg i_clk;
    #/ reg i_rst_n;
    #/ // Outputs
    #/ wire [`QU_OUT.DWT`-1:0] o_data;
    #/ // Instantiate the DUT

    tb_module_name = f"TbFxMatch"
    START_CYCLES=3
    inst_ports = {
        "i_data": "i_data",
        "o_data": "o_data",
        "i_clk": "i_clk",
        "i_rst_n": "i_rst_n"
    }
    #/ // Instantiate the DUT, requires kwargs
    ModuleFxMatch(QU_IN = QU_IN, QU_OUT=QU_OUT, N_CLK=N_CLK, IF_RST_N = IF_RST_N, QU_MODE = QU_MODE, OF_MODE = OF_MODE, PORTS = inst_ports)

    #/ // Drive clk signal
    PyTB.Moduledrive_clk(port = "i_clk", period = 10, OUTMODE = "PRINT")

    #/ // Initialize Inputs
    PyTB.ModuleInitialize(ports = ["i_data"],OUTMODE = "PRINT")


    #/ // Drive rst signal
    PyTB.Moduledrive_arst(port = "i_rst_n", clk="i_clk", start=1, last=1, OUTMODE = "PRINT")
    #/
    #/

    # The root directory is ./RTL/Testcases
    input_files_dir = os.path.join(io_file_dir,"Input_Files")
    output_files_dir = os.path.join(io_file_dir,"Output_Files")

    #/ // Drive input signal with `N_FRAMES` inputs using mode A2

    PyTB.Moduledrive_input_signal(clk = "i_clk",ports=["i_data"], files = ["fxmatch_i_data.txt"],input_file_dir=input_files_dir,n_latency=30, n_cycle = 1, n_excites = N_FRAMES, OUTMODE = "PRINT")

    #/ // Dump output signal using mode A

    PyTB.Moduledump( clk="i_clk", grp= "output_data", output_file_dir= output_files_dir, names=["fxmatch_o_data"], handles=["o_data"], n_latency= N_CLK, if_end= True, end_wait=100, n_cycle=1, n_dump = N_FRAMES, OUTMODE = "PRINT")
    #/ // Dump the wave.vcd file
    new_tb_name = tb_module_name + PyTB.int_to_hex_with_length(1)
    #/ initial begin
    #/     $dumpfile("wave.vcd");
    #/     $dumpvars(0, `new_tb_name`);
    #/ end
    #/ endmodule
