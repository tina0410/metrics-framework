# coding = utf-8
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Description: Verithon testbench generator for Delay.

from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

from Generator.BasicModules.Delay.Delay import ModuleDelay


@convert
def ModuleTbDelay(DWT, N_CLK, IF_RST_N):
    HAS_RST_N = IF_RST_N if isinstance(IF_RST_N, bool) else any(IF_RST_N)
    values = [0, 1, (1 << DWT) - 1, 0x5A & ((1 << DWT) - 1)]

    #/ `timescale 1ns/1ps
    #/ module TbDelay;
    #/ reg [`DWT`-1:0] i_data;
    #/ wire [`DWT`-1:0] o_data;
    if N_CLK > 0:
        #/ reg i_clk;
        if HAS_RST_N:
            #/ reg i_rst_n;
            pass

    ports = {"i_data": "i_data", "o_data": "o_data"}
    if N_CLK > 0:
        ports["i_clk"] = "i_clk"
        if HAS_RST_N:
            ports["i_rst_n"] = "i_rst_n"
    ModuleDelay(DWT=DWT, N_CLK=N_CLK, IF_RST_N=IF_RST_N, PORTS=ports)

    if N_CLK > 0:
        #/ initial i_clk = 1'b0;
        #/ always #5 i_clk = ~i_clk;
        pass

    #/ task check;
    #/     input [`DWT`-1:0] value;
    #/     begin
    if N_CLK > 0:
        #/         @(negedge i_clk);
        #/         i_data = value;
        #/         repeat (`N_CLK`) @(posedge i_clk);
        #/         #1;
        pass
    else:
        #/         i_data = value;
        #/         #1;
        pass
    #/         if (o_data !== value) begin
    #/             $display("Delay mismatch: got=%h expected=%h", o_data, value);
    #/             $fatal(1);
    #/         end
    #/     end
    #/ endtask

    #/ initial begin
    #/     i_data = `DWT`'b0;
    if N_CLK > 0 and HAS_RST_N:
        #/     i_rst_n = 1'b0;
        #/     #2;
        #/     if (o_data !== `DWT`'b0) $fatal(1, "reset did not clear Delay output");
        #/     i_rst_n = 1'b1;
        pass
    for value in values:
        #/     check(`DWT`'h`format(value, 'x')`);
        pass
    #/     $display("PASS Delay DWT=`DWT` N_CLK=`N_CLK`");
    #/     $finish;
    #/ end
    #/ endmodule
