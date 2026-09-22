###################################################################################################
# Module Name: SimpleSRAM
# Description: Parameterised SRAM wrapper for FPGA block RAM inference.
#   Two modes:
#     'SP'  — Single-port: one address bus, separate wr_en / rd_en.
#     'SDP' — Simple dual-port: independent wr_addr / rd_addr.
#   Synchronous read with 1-clock latency in both modes.
#   IF_RST_N controls the output register reset only (SRAM contents
#   are never reset — matches FPGA block RAM behaviour).
#
# Author: Auto-generated (refactoring)
# Date: 2026.3.15
# Version: V0.1.0
# Dependency Modules: None
###################################################################################################
import math
import pytv
from pytv.Converter import convert
from typing import Literal


@convert
def ModuleSimpleSRAM(DWT: int, DEPTH: int, MODE: Literal['SP', 'SDP'], IF_RST_N: bool) -> None:
    """
    Parameterised SRAM wrapper inferrable as FPGA block RAM.

    **SP mode** (single-port):
      One shared address bus.  Write and read enables must be mutually
      exclusive (caller's responsibility).

    **SDP mode** (simple dual-port):
      Independent write and read address buses.  Concurrent read/write
      to *different* addresses is supported.

    Synchronous read — output appears 1 clock after ``rd_en`` assertion.

    :param DWT: 24
        Data width (bits).
    :type DWT: int
    :param DEPTH: 273
        Number of entries.
    :type DEPTH: int
    :param MODE: 'SP'
        ``'SP'`` for single-port, ``'SDP'`` for simple dual-port.
    :type MODE: Literal['SP', 'SDP']
    :param IF_RST_N: False
        Whether the output register uses asynchronous active-low reset.
    :type IF_RST_N: bool
    """
    if DEPTH < 1:
        raise ValueError("DEPTH must be >= 1")
    if DWT < 1:
        raise ValueError("DWT must be >= 1")
    if MODE not in ('SP', 'SDP'):
        raise ValueError(f"MODE must be 'SP' or 'SDP', got {MODE!r}")

    ADDR_WIDTH = max(math.ceil(math.log2(DEPTH)), 1) if DEPTH > 1 else 1

    #/ `timescale 1ns / 1ps
    #/ module SimpleSRAM (
    #/     input clk,
    if IF_RST_N:
        #/ input rst_n,
        pass

    if MODE == 'SP':
        #/ input [`ADDR_WIDTH`-1:0] addr,
        pass
    else:
        #/ input [`ADDR_WIDTH`-1:0] wr_addr,
        #/ input [`ADDR_WIDTH`-1:0] rd_addr,
        pass

    #/ input              wr_en,
    #/ input  [`DWT`-1:0] wr_data,
    #/ input              rd_en,
    #/ output [`DWT`-1:0] rd_data
    #/ );

    # ---- SRAM array ----
    #/ reg [`DWT`-1:0] mem [0:`DEPTH`-1];
    #/ reg [`DWT`-1:0] rd_data_reg;

    # ---- Write logic ----
    if MODE == 'SP':
        #/ always @(posedge clk) begin
        #/     if (wr_en) begin
        #/         mem[addr] <= wr_data;
        #/     end
        #/ end
        pass
    else:
        #/ always @(posedge clk) begin
        #/     if (wr_en) begin
        #/         mem[wr_addr] <= wr_data;
        #/     end
        #/ end
        pass

    # ---- Read logic (synchronous, 1-clk latency) ----
    if MODE == 'SP':
        if IF_RST_N:
            #/ always @(posedge clk or negedge rst_n) begin
            #/     if (!rst_n) begin
            #/         rd_data_reg <= `DWT`'b0;
            #/     end else begin
            #/         if (rd_en) begin
            #/             rd_data_reg <= mem[addr];
            #/         end
            #/     end
            #/ end
            pass
        else:
            #/ always @(posedge clk) begin
            #/     if (rd_en) begin
            #/         rd_data_reg <= mem[addr];
            #/     end
            #/ end
            pass
    else:
        if IF_RST_N:
            #/ always @(posedge clk or negedge rst_n) begin
            #/     if (!rst_n) begin
            #/         rd_data_reg <= `DWT`'b0;
            #/     end else begin
            #/         if (rd_en) begin
            #/             rd_data_reg <= mem[rd_addr];
            #/         end
            #/     end
            #/ end
            pass
        else:
            #/ always @(posedge clk) begin
            #/     if (rd_en) begin
            #/         rd_data_reg <= mem[rd_addr];
            #/     end
            #/ end
            pass

    #/ assign rd_data = rd_data_reg;
    #/ endmodule
