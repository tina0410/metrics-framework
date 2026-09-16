# coding = utf-8
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Verithon testbench generator for AdderTree.

from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

from Generator.BasicModules.AdderTree import ModuleAdderTree


@convert
def ModuleTbAdderTree(QU_IN, QU_OUT, N_PIPELINES, QU_MODE, OF_MODE, IF_RST_N, N_INPUTS):
    PACKED_DWT = QU_IN.DWT * N_INPUTS
    vectors = [
        [index + 1 for index in range(N_INPUTS)],
        [((index * 17) + 3) & ((1 << QU_IN.DWT) - 1) for index in range(N_INPUTS)],
        [((1 << QU_IN.DWT) - 1) if index % 2 else 0 for index in range(N_INPUTS)],
    ]

    #/ `timescale 1ns/1ps
    #/ module TbAdderTree;
    #/ reg [`PACKED_DWT`-1:0] i_data;
    #/ wire [`QU_OUT.DWT`-1:0] o_data;
    if N_PIPELINES > 0:
        #/ reg i_clk;
        if IF_RST_N:
            #/ reg i_rst_n;
            pass

    ports = {"i_data": "i_data", "o_data": "o_data"}
    if N_PIPELINES > 0:
        ports["i_clk"] = "i_clk"
        if IF_RST_N:
            ports["i_rst_n"] = "i_rst_n"

    ModuleAdderTree(QU_IN=QU_IN, QU_OUT=QU_OUT, N_PIPELINES=N_PIPELINES, QU_MODE=QU_MODE, OF_MODE=OF_MODE, IF_RST_N=IF_RST_N, N_INPUTS=N_INPUTS, CONFIG_MODE="A", PORTS=ports)

    if N_PIPELINES > 0:
        #/ initial i_clk = 1'b0;
        #/ always #5 i_clk = ~i_clk;
        pass

    #/ task check;
    #/     input [`PACKED_DWT`-1:0] value;
    #/     input [`QU_OUT.DWT`-1:0] expected;
    #/     begin
    if N_PIPELINES > 0:
        #/         @(negedge i_clk);
        #/         i_data = value;
        #/         repeat (`N_PIPELINES`) @(posedge i_clk);
        #/         #1;
        pass
    else:
        #/         i_data = value;
        #/         #1;
        pass
    #/         if (o_data !== expected) begin
    #/             $display("AdderTree mismatch: in=%h got=%h expected=%h", value, o_data, expected);
    #/             $fatal(1);
    #/         end
    #/     end
    #/ endtask

    #/ initial begin
    #/     i_data = `PACKED_DWT`'b0;
    if N_PIPELINES > 0 and IF_RST_N:
        #/     i_rst_n = 1'b0;
        #/     #2;
        #/     i_rst_n = 1'b1;
        pass
    for values in vectors:
        packed = sum(
            (value & ((1 << QU_IN.DWT) - 1)) << (index * QU_IN.DWT)
            for index, value in enumerate(values)
        )
        expected = sum(values) & ((1 << QU_OUT.DWT) - 1)
        #/     check(`PACKED_DWT`'h`format(packed, 'x')`, `QU_OUT.DWT`'h`format(expected, 'x')`);
    #/     $display("PASS AdderTree N_INPUTS=`N_INPUTS` N_PIPELINES=`N_PIPELINES`");
    #/     $finish;
    #/ end
    #/ endmodule
