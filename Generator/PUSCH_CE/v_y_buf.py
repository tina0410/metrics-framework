import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import Optional, Dict


@convert
def ModuleY_BUF(max_occasions: int, symbols_per_occasion: int, SRAM_DEPTH: int, DATA_WIDTH: int, SRAM_MACRO_CONFIG: Optional[Dict] = None) -> None:
    """
    Shared pre-LS Y buffer for rate-matched LS-FI pipeline.

    Stores received Y samples (after Y_PATH_REDUCE) before port separation.
    One instance per RX antenna pipeline, shared across all target ports.

    Address space: {occasion, symbol_within_occasion, rb_addr}
      - occasion: 0..max_occasions-1
      - symbol:   0..symbols_per_occasion-1 (1 for single DMRS, 2 for double)
      - rb_addr:  0..SRAM_DEPTH-1

    Write: Y_PATH_REDUCE output during S_RUN at input rate (1 RB/clk).
    Read: LS-FI window controller during S_TI (1 RB/clk, occasion/symbol selected).

    The last occasion bank uses dual-port (1R1W) for early-drain overlap.
    All other occasion banks use single-port.

    :param max_occasions: max number of DMRS occasions (1 + max(additional_DMRS_range))
    :param symbols_per_occasion: 1 (single DMRS) or 2 (double DMRS)
    :param SRAM_DEPTH: ceil(max_num_RBs / RB_PARALLELISM) per symbol
    :param DATA_WIDTH: len(required_re_per_rb) * COMPLEX_DWT_Y
    """
    if max_occasions < 1:
        raise ValueError("max_occasions must be >= 1")
    if symbols_per_occasion not in (1, 2):
        raise ValueError("symbols_per_occasion must be 1 or 2")

    TOTAL_PLANES = max_occasions * symbols_per_occasion
    ADDR_WIDTH = max(math.ceil(math.log2(SRAM_DEPTH)), 1) if SRAM_DEPTH > 1 else 1
    PLANE_SEL_WIDTH = max(math.ceil(math.log2(TOTAL_PLANES)), 1) if TOTAL_PLANES > 1 else 1

    #/ `timescale 1ns / 1ps
    #/ module Y_BUF (
    #/     input clk,
    #/     input rst_n,
    #/
    #/     // Write interface -- from Y_PATH_REDUCE during S_RUN
    #/     input wr_en,
    if TOTAL_PLANES > 1:
        #/ input [`PLANE_SEL_WIDTH`-1:0] wr_plane_sel,
        pass
    #/     input [`ADDR_WIDTH`-1:0] wr_addr,
    #/     input [`DATA_WIDTH`-1:0] wr_data,
    #/
    #/     // Read interface -- LS-FI window controller during windowed phase
    #/     input rd_en,
    if TOTAL_PLANES > 1:
        #/ input [`PLANE_SEL_WIDTH`-1:0] rd_plane_sel,
        pass
    #/     input  [`ADDR_WIDTH`-1:0] rd_addr,
    #/     output [`DATA_WIDTH`-1:0] rd_data
    #/ );

    # Behavioral mode: reg arrays, one per plane
    for plane in range(TOTAL_PLANES):
        is_last = (plane == TOTAL_PLANES - 1)
        occ = plane // symbols_per_occasion
        sym = plane % symbols_per_occasion
        mode_label = 'dual_port' if is_last else 'single_port'
        #/ // ===== Plane `plane` (occasion `occ`, symbol `sym`) — `mode_label` =====
        #/ reg [`DATA_WIDTH`-1:0] `f"sram_plane{plane}"` [0:`SRAM_DEPTH`-1];

    #/

    # ---- Write logic ----
    for plane in range(TOTAL_PLANES):
        if TOTAL_PLANES > 1:
            cond = f"wr_en && (wr_plane_sel == {PLANE_SEL_WIDTH}'d{plane})"
        else:
            cond = "wr_en"
        #/ always @(posedge clk) begin
        #/     if (`cond`)
        #/         `f"sram_plane{plane}"`[wr_addr] <= wr_data;
        #/ end

    #/

    # ---- Read logic ----
    # The window controller presents the plane and RB0 address throughout its
    # P_LOAD_CTX prefetch cycle.  Select the plane combinationally so RB0 is
    # already valid at the following edge, when the LS pipeline consumes it.
    # Registering only the plane selector here makes the first RB after every
    # plane change come from the previous occasion/symbol.
    #/ reg [`DATA_WIDTH`-1:0] rd_data_r;
    if TOTAL_PLANES > 1:
        #/ always @(*) begin
        #/     case (rd_plane_sel)
        for plane in range(TOTAL_PLANES):
            #/ `PLANE_SEL_WIDTH`'d`plane`: rd_data_r = `f"sram_plane{plane}"`[rd_addr];
            pass
        #/     default: rd_data_r = `DATA_WIDTH`'d0;
        #/     endcase
        #/ end
    else:
        #/ always @(*) begin
        #/     rd_data_r = sram_plane0[rd_addr];
        #/ end
        pass  # single-plane: combinational read from sram_plane0

    #/ assign rd_data = rd_data_r;

    #/ endmodule
