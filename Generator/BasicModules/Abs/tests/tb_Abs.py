# coding = utf-8
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Generate the Verilog testbench for Abs.

import os
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

import PyTB

from Generator.BasicModules.Abs.Abs import ModuleAbs


@convert
def ModuleTbAbs(QU_IN, QU_OUT, N_CLK, IF_RST_N, QU_MODE, OF_MODE, io_file_dir="../..", N_FRAMES=32):
    #/ `timescale 1ns/1ps
    #/ module TbAbs;
    #/     reg  [`QU_IN.DWT`-1:0] Input_i_data;
    #/     reg  [`QU_IN.DWT`-1:0] i_data;
    #/     reg                     clk;
    if N_CLK > 0 and IF_RST_N:
        #/     reg                     i_rst_n;
        pass
    #/     wire [`QU_OUT.DWT`-1:0] o_data;

    inst_ports = {
        "i_data": "i_data",
        "o_data": "o_data",
    }
    if N_CLK > 0:
        inst_ports["i_clk"] = "clk"
        if IF_RST_N:
            inst_ports["i_rst_n"] = "i_rst_n"

    #/ // Instantiate the DUT
    ModuleAbs(QU_IN=QU_IN, QU_OUT=QU_OUT, N_CLK=N_CLK, IF_RST_N=IF_RST_N, QU_MODE=QU_MODE, OF_MODE=OF_MODE, PORTS=inst_ports)

    PyTB.Moduledrive_clk(port="clk", period=10, OUTMODE="PRINT")
    PyTB.ModuleInitialize(ports=["i_data"], OUTMODE="PRINT")

    if N_CLK > 0 and IF_RST_N:
        PyTB.Moduledrive_arst(port="i_rst_n", clk="clk", start=1, last=1, OUTMODE="PRINT")

    input_files_dir = os.path.join(io_file_dir, "Input_Files")
    output_files_dir = os.path.join(io_file_dir, "Output_Files")

    PyTB.Moduledrive_input_signal(clk="clk", ports=["i_data"], files=["abs_i_data.txt"], input_file_dir=input_files_dir, n_latency=3, n_cycle=1, n_excites=N_FRAMES, OUTMODE="PRINT")

    PyTB.Moduledump(clk="clk", grp="output_data", output_file_dir=output_files_dir, names=["abs_o_data"], handles=["o_data"], n_latency=N_CLK, if_end=True, end_wait=10, n_cycle=1, n_dump=N_FRAMES, OUTMODE="PRINT")

    tb_module_name = "TbAbs"
    new_tb_name = tb_module_name + PyTB.int_to_hex_with_length(1)

    #/ initial begin
    #/     $dumpfile("wave.vcd");
    #/     $dumpvars(0, `new_tb_name`);
    #/ end
    #/ endmodule
