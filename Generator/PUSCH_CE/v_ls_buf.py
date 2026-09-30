import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import Optional, Dict


@convert
def ModuleLS_BUF(max_occasions: int, SRAM_DEPTH: int, DATA_WIDTH: int, SRAM_MACRO_CONFIG: Optional[Dict] = None) -> None:
    """
    Pre-FI pilot buffer — stores raw LS pilot estimates per RB per occasion.

    Same-width read and write (no banking, no transpose). One SRAM per occasion:
      - Occasions 0..N-2: single-port (write during S_RUN, read during S_TI).
      - Occasion N-1: dual-port 1R1W (concurrent LS tail write + FI read
        for early drain pipelining).
      - max_occasions == 1: sole occasion is dual-port.

    Write: averaging output during S_RUN (1 RB/clk).
    Read: FI core during S_TI (address driven by FI core, one occasion at a time).

    :param max_occasions: 3
    :param SRAM_DEPTH: 273
    :param DATA_WIDTH: 288
        Total bit width per entry = N_PILOTS_PER_RB * RB_PAR * 2 * Qu_H_LS.DWT.
    :param SRAM_MACRO_CONFIG: None
        When set, generates SRAM macro instantiations.  Dict with keys:
          - ``'sp_module'``: SP SRAM module name
          - ``'dp_module'``: 1R1W RF module name
          - ``'macro_depth'``: Actual macro depth (must be >= SRAM_DEPTH)
    """
    if max_occasions < 1:
        raise ValueError("max_occasions must be >= 1")
    if SRAM_DEPTH < 1:
        raise ValueError("SRAM_DEPTH must be >= 1")

    ADDR_WIDTH = max(math.ceil(math.log2(SRAM_DEPTH)), 1) if SRAM_DEPTH > 1 else 1
    OCC_SEL_WIDTH = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1

    USE_MACRO = SRAM_MACRO_CONFIG is not None
    if USE_MACRO:
        if 'roles' not in SRAM_MACRO_CONFIG:
            raise ValueError("SRAM_MACRO_CONFIG requires candidate-derived memory roles")
        _SP_ROLE = SRAM_MACRO_CONFIG['roles']['ls_buffer_single_port']
        _SP_TIEOFFS = SRAM_MACRO_CONFIG.get('sp_tieoff_ports', [("RET1N", "1'b1")])
        _DP_TIEOFFS = SRAM_MACRO_CONFIG.get('dp_tieoff_ports', [("RET1N", "1'b1")])
        _DP_ROLE = SRAM_MACRO_CONFIG['roles']['ls_buffer_one_read_one_write']
        if _SP_ROLE['logical_width'] != DATA_WIDTH or _DP_ROLE['logical_width'] != DATA_WIDTH:
            raise ValueError("LS buffer memory role width mismatch")
        if _SP_ROLE['macro_depth'] != _DP_ROLE['macro_depth']:
            raise ValueError("LS buffer macro depths must match")
        MACRO_DEPTH = _SP_ROLE['macro_depth']
        MACRO_ADDR_WIDTH = max(math.ceil(math.log2(MACRO_DEPTH)), 1)
        if MACRO_DEPTH < SRAM_DEPTH:
            raise ValueError(f"SRAM macro depth={MACRO_DEPTH} < SRAM_DEPTH={SRAM_DEPTH}")

    #/ `timescale 1ns / 1ps
    #/ module LS_BUF (
    #/     input clk,
    #/     input rst_n,
    #/     
    #/     // Write interface -- from averaging output during S_RUN
    #/     input wr_en,
    if max_occasions > 1:
        #/ input [`OCC_SEL_WIDTH`-1:0] wr_occasion_sel,
        pass
    #/ input [`ADDR_WIDTH`-1:0] wr_addr,
    #/ input [`DATA_WIDTH`-1:0] wr_data,
    #/ 
    #/ // Read interface -- FI core during S_TI
    #/ input rd_en,
    if max_occasions > 1:
        #/ input [`OCC_SEL_WIDTH`-1:0] rd_occasion_sel,
        pass
    #/ input  [`ADDR_WIDTH`-1:0] rd_addr,
    #/ output [`DATA_WIDTH`-1:0] rd_data
    #/ );

    if not USE_MACRO:
        # ==================================================================
        # BEHAVIORAL MODE: reg arrays
        # ==================================================================

        for occ in range(max_occasions):
            is_dual = (occ == max_occasions - 1)
            mode_label = 'dual_port' if is_dual else 'single_port'
            #/ // ===== Occasion `occ` SRAM (`mode_label`) =====
            if is_dual:
                #/ // synthesis: infer dual-port block RAM -- 1R1W
                pass
            #/ reg [`DATA_WIDTH`-1:0] `f"sram_occ{occ}"` [0:`SRAM_DEPTH`-1];
            pass

        #/ 

        # ---- Write logic: decode wr_occasion_sel ----
        for occ in range(max_occasions):
            #/ always @(posedge clk) begin
            if max_occasions > 1:
                #/ if (wr_en && (wr_occasion_sel == `OCC_SEL_WIDTH`'d`occ`)) begin
                pass
            else:
                #/ if (wr_en) begin
                pass
            #/ `f"sram_occ{occ}"`[wr_addr] <= wr_data;
            #/ end
            #/ end
            #/ 
            pass

        # ---- Read logic: synchronous 1-clk latency, mux by occasion ----
        #/ reg [`DATA_WIDTH`-1:0] sram_rd_raw;
        if max_occasions > 1:
            #/ reg [`OCC_SEL_WIDTH`-1:0] rd_occasion_sel_q;
            #/ always @(posedge clk) begin
            #/     if (rd_en) begin
            #/         rd_occasion_sel_q <= rd_occasion_sel;
            #/     end
            #/ end
            pass

        # Per-occasion read registers
        for occ in range(max_occasions):
            #/ reg [`DATA_WIDTH`-1:0] `f"sram_rd_occ{occ}"`;
            pass
        #/ 

        for occ in range(max_occasions):
            #/ always @(posedge clk) begin
            #/     if (rd_en) begin
            #/         `f"sram_rd_occ{occ}"` <= `f"sram_occ{occ}"`[rd_addr];
            #/     end
            #/ end
            #/ 
            pass

        # Output mux
        if max_occasions > 1:
            #/ always @(*) begin
            #/     case (rd_occasion_sel_q)
            for occ in range(max_occasions):
                #/ `OCC_SEL_WIDTH`'d`occ`: sram_rd_raw = `f"sram_rd_occ{occ}"`;
                pass
            #/ default: sram_rd_raw = {`DATA_WIDTH`{1'bx}};
            #/ endcase
            #/ end
            pass
        else:
            #/ always @(*) begin
            #/     sram_rd_raw = sram_rd_occ0;
            #/ end
            pass

        #/ assign rd_data = sram_rd_raw;

    else:
        # ==================================================================
        # MACRO MODE: TSMC 65 nm GP ARM SRAM macro instantiations
        # ==================================================================
        ADDR_PAD = MACRO_ADDR_WIDTH - ADDR_WIDTH
        wr_addr_ext = f"{{{ADDR_PAD}'b0, wr_addr}}" if ADDR_PAD > 0 else "wr_addr"
        rd_addr_ext = f"{{{ADDR_PAD}'b0, rd_addr}}" if ADDR_PAD > 0 else "rd_addr"

        for occ in range(max_occasions):
            if max_occasions > 1:
                #/ wire `f"wr_en_occ{occ}"` = wr_en & (wr_occasion_sel == `OCC_SEL_WIDTH`'d`occ`);
                pass
            else:
                #/ wire wr_en_occ0 = wr_en;
                pass

        for occ in range(max_occasions):
            is_dual = (occ == max_occasions - 1)
            inst = f"u_sram_occ{occ}"
            #/ wire [`DATA_WIDTH`-1:0] `f"sram_q_occ{occ}"`;

            if not is_dual:
                # --- SP SRAM (or DP used as SP when width mismatch) ---
                if max_occasions > 1:
                    #/ wire `f"sp_rd_en_occ{occ}"` = rd_en & (rd_occasion_sel == `OCC_SEL_WIDTH`'d`occ`);
                    #/ wire `f"sp_cen_occ{occ}"` = ~(`f"wr_en_occ{occ}"` | `f"sp_rd_en_occ{occ}"`);
                    pass
                else:
                    #/ wire `f"sp_cen_occ{occ}"` = ~(`f"wr_en_occ{occ}"` | rd_en);
                    pass
                #/ wire `f"sp_wen_occ{occ}"` = ~`f"wr_en_occ{occ}"`;
                sp_addr_expr = f'{f"wr_en_occ{occ}"} ? {wr_addr_ext} : {rd_addr_ext}'
                #/ wire [`MACRO_ADDR_WIDTH`-1:0] `f"sp_addr_occ{occ}"` = `sp_addr_expr`;

                _tile_offset = 0
                for _tile_idx, _tile in enumerate(_SP_ROLE['tiles']):
                    _tile_width = _tile['width']
                    _tile_module = _tile['module']
                    _tile_hi = _tile_offset + _tile_width - 1
                    _tile_q = f"sram_q_occ{occ}_tile{_tile_idx}"
                    _tile_inst = f"{inst}_tile{_tile_idx}"
                    #/ wire [`_tile_width`-1:0] `_tile_q`;
                    #/ `_tile_module` `_tile_inst` (
                    #/     .CLK    (clk),
                    #/     .CEN    (`f"sp_cen_occ{occ}"`),
                    #/     .WEN    (`f"sp_wen_occ{occ}"`),
                    #/     .A      (`f"sp_addr_occ{occ}"`),
                    #/     .D      (wr_data[`_tile_hi`:`_tile_offset`]),
                    #/     .Q      (`_tile_q`)`"," if _SP_TIEOFFS else ""`
                    for _ti, (_port, _val) in enumerate(_SP_TIEOFFS):
                        _comma = "," if _ti < len(_SP_TIEOFFS) - 1 else ""
                        #/     .`_port`  (`_val`)`_comma`
                        pass
                    #/ );
                    #/ assign `f"sram_q_occ{occ}"`[`_tile_hi`:`_tile_offset`] = `_tile_q`;
                    _tile_offset = _tile_hi + 1
            else:
                # --- 1R1W DP ---
                if max_occasions > 1:
                    #/ wire `f"dp_rd_en_occ{occ}"` = rd_en & (rd_occasion_sel == `OCC_SEL_WIDTH`'d`occ`);
                    pass
                else:
                    #/ wire `f"dp_rd_en_occ{occ}"` = rd_en;
                    pass

                _tile_offset = 0
                for _tile_idx, _tile in enumerate(_DP_ROLE['tiles']):
                    _tile_width = _tile['width']
                    _tile_module = _tile['module']
                    _tile_hi = _tile_offset + _tile_width - 1
                    _tile_q = f"sram_q_occ{occ}_tile{_tile_idx}"
                    _tile_inst = f"{inst}_tile{_tile_idx}"
                    #/ wire [`_tile_width`-1:0] `_tile_q`;
                    #/ `_tile_module` `_tile_inst` (
                    #/     .CLKA   (clk),
                    #/     .CENA   (~`f"dp_rd_en_occ{occ}"`),
                    #/     .AA     (`rd_addr_ext`),
                    #/     .QA     (`_tile_q`),
                    #/     .CLKB   (clk),
                    #/     .CENB   (~`f"wr_en_occ{occ}"`),
                    #/     .AB     (`wr_addr_ext`),
                    #/     .DB     (wr_data[`_tile_hi`:`_tile_offset`])`"," if _DP_TIEOFFS else ""`
                    for _ti, (_port, _val) in enumerate(_DP_TIEOFFS):
                        _comma = "," if _ti < len(_DP_TIEOFFS) - 1 else ""
                        #/     .`_port`  (`_val`)`_comma`
                        pass
                    #/ );
                    #/ assign `f"sram_q_occ{occ}"`[`_tile_hi`:`_tile_offset`] = `_tile_q`;
                    _tile_offset = _tile_hi + 1

        # ---- Output mux ----
        if max_occasions > 1:
            #/ reg [`OCC_SEL_WIDTH`-1:0] rd_occasion_sel_q;
            #/ always @(posedge clk) begin
            #/     if (rd_en) begin
            #/         rd_occasion_sel_q <= rd_occasion_sel;
            #/     end
            #/ end
            pass

        #/ reg [`DATA_WIDTH`-1:0] sram_rd_raw;
        if max_occasions > 1:
            #/ always @(*) begin
            #/     case (rd_occasion_sel_q)
            for occ in range(max_occasions):
                #/ `OCC_SEL_WIDTH`'d`occ`: sram_rd_raw = `f"sram_q_occ{occ}"`;
                pass
            #/ default: sram_rd_raw = {`DATA_WIDTH`{1'bx}};
            #/ endcase
            #/ end
            pass
        else:
            #/ always @(*) begin
            #/     sram_rd_raw = sram_q_occ0;
            #/ end
            pass

        #/ assign rd_data = sram_rd_raw;

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    ModuleLS_BUF(
        max_occasions=3,
        SRAM_DEPTH=273,
        DATA_WIDTH=288,
    )
