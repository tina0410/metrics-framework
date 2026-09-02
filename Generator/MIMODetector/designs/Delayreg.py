import pytv
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

from enum import Enum

from PyTU import QuMode, OfMode, QuType

@convert
def ModuleDelayreg(DWT, N_CLK = 1, IF_RST_N = False):
    # Parsing the input arguments
    if N_CLK > 0 and type(IF_RST_N) == bool:
        # Expand the boolean to a list of the same value
        IF_RST_N = [IF_RST_N] * N_CLK
    # End Parsing the input arguments
    #/ module Delay(
    #/    i_data, o_data
    if N_CLK > 0:
        #/    , i_clk
        if any(IF_RST_N):
            #/    , i_rst_n
            pass
    #/ );
    #/ // Input and output ports
    #/ input [`DWT`-1:0] i_data;
    #/ output reg [`DWT`-1:0] o_data;
    if N_CLK > 0:
        #/ input i_clk;
        if any(IF_RST_N):
            #/ input i_rst_n;
            pass

    if N_CLK == 0:
        #/ assign o_data = i_data;
        pass
    else: # N_CLK > 0
        #/ reg [`DWT`-1:0] data_d [0:`N_CLK`-1];
        if IF_RST_N[0]:
            #/ always @(posedge i_clk, negedge i_rst_n) begin
            #/     if (~i_rst_n) begin
            #/         data_d[0] <= `DWT`'b0;
            #/     end 
            #/     else begin
            #/         o_data <= i_data;
            #/     end
            #/ end
            pass
        else:
            #/ always @(posedge i_clk) begin
            #/    o_data <= i_data;
            #/ end
            pass
    #/ endmodule