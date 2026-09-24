from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))
import math

@convert
def ModuleSYMBOL_COUNTER(max_pusch_symbols: int) -> None:
    """
    Symbol-level counter for tracking current OFDM symbol index during channel estimation.

    This counter tracks which PUSCH symbol is currently being processed. It increments
    by 1 each time the current beat is the last beat of the symbol — i.e., the RBs
    processed on this beat include or exceed num_RBs. It also generates sym_boundary_strb,
    which signals that the current beat has reached or exceeded the symbol boundary.
    This strobe resets the RB counter and triggers downstream c_init reload / FSM transitions.



    Parameters:
    :param max_pusch_symbols: 14
        Maximum number of PUSCH symbols per slot (determines symbol counter bit width).
        Typical values: 14 (normal CP), 12 (extended CP).
    :type max_pusch_symbols: int
    """

    if max_pusch_symbols <= 0:
        raise ValueError("max_pusch_symbols must be positive")

    symbol_width  = math.ceil(math.log2(max_pusch_symbols)) if max_pusch_symbols > 1 else 1

    #/ `timescale 1ns / 1ps
    #/ module SYMBOL_COUNTER(
    #/     input                           clk,
    #/     input                           rst_n,
    #/     input                           ctrl_ctr_en,
    #/     input                           ctrl_sym_switch,
    #/     input      [`symbol_width`-1:0] pusch_symbol_length,
    #/     output reg [`symbol_width`-1:0] ctrl_sym_idx,
    #/     output     [`symbol_width`-1:0] ctrl_sym_idx_next,
    #/     output                          ctrl_slot_boundary
    #/ );
    #/
    #/ // ctrl_sym_idx_next: combinational look-ahead for pilot detection alignment
    #/ assign ctrl_sym_idx_next = (ctrl_sym_idx >= pusch_symbol_length - `symbol_width`'d1)
    #/ ? `symbol_width`'d0
    #/ : ctrl_sym_idx + `symbol_width`'d1;
    #/
    #/ // Symbol counter: increment on each qualified ctrl_sym_switch, wrap at pusch_symbol_length
    #/ always @(posedge clk or negedge rst_n) begin
    #/     if (!rst_n) begin
    #/         ctrl_sym_idx <= `symbol_width`'d0;
    #/     end
    #/     else if (!ctrl_ctr_en) begin
    #/         ctrl_sym_idx <= `symbol_width`'d0;
    #/     end
    #/     else begin
    #/         if (ctrl_sym_switch) begin
    #/             if (ctrl_sym_idx >= pusch_symbol_length - `symbol_width`'d1) begin
    #/                 ctrl_sym_idx <= `symbol_width`'d0;
    #/             end else begin
    #/                 ctrl_sym_idx <= ctrl_sym_idx + `symbol_width`'d1;
    #/             end
    #/         end
    #/     end
    #/ end
    #/
    #/ // ctrl_slot_boundary = ctrl_sym_switch and last symbol in this slot
    #/ assign ctrl_slot_boundary = ctrl_sym_switch & (ctrl_sym_idx >= pusch_symbol_length - `symbol_width`'d1);
    #/ endmodule
