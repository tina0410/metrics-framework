###################################################################################################
# Module Name: PILOT_SRAM_BANK
# Description: Per-antenna-port banked SRAM for storing frequency-interpolated pilot estimates.
#   Each bank contains ``max_occasions`` SRAM arrays (per-occasion mixed mode):
#   - Occasions 0..N-2: single-port (write and read in separate FSM phases).
#   - Occasion N-1: dual-port (allows concurrent write of last occasion
#     while TI reads earlier occasions for early drain).
#   Read-during-write on same address yields old data (synchronous SRAM),
#   which is correct since TI reads previous occasion data. The FSM
#   guarantees TI reads and FREQ_INTERP writes target different addresses
#   under normal operation (different RB sweep phases).
#   Split into ``N_BANKS = 12 // TI_RE_PARALLELISM`` narrow banks.
#   - Write phase (S_RUN): all banks written simultaneously (full 12-RE word).
#   - Read phase (S_TIME_INTERP): only the bank selected by ``rd_bank_sel`` is
#     read, reducing read power and providing the TI_RE_PARALLELISM-wide slice
#     directly without an external MUX.
#   Write and read never occur simultaneously (different FSM phases).
#
#   Data organisation per bank SRAM entry:
#     { RE_{g*P+P-1}_complex, ..., RE_{g*P+1}_complex, RE_{g*P}_complex }
#     width = TI_RE_PARALLELISM × H_interp_f_DWT bits
###################################################################################################
import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import Optional, Dict
from basic_modules import QuType


@convert
def ModulePILOT_SRAM_BANK(max_occasions: int, SRAM_DEPTH: int, Qu_H_interp_f: QuType, TI_RE_PARALLELISM: int = 12, RB_PARALLELISM: int = 1, SRAM_MACRO_CONFIG: Optional[Dict] = None) -> None:
    """
    Per-antenna-port banked SRAM for pilot storage across DMRS occasions.

    Contains ``max_occasions × N_BANKS`` independent SRAM arrays, where
    ``N_BANKS = RB_PARALLELISM × 12 // TI_RE_PARALLELISM``.  All banks share
    the same address bus.  During write, all banks are written in parallel from
    the full write data.  During read, only the bank selected by
    ``rd_bank_sel`` is read, providing TI_RE_PARALLELISM REs for one RB.

    **SRAM mode** (per-occasion mixed):
      - Occasions 0..N-2 use single-port arrays (no concurrent R/W).
      - Occasion N-1 uses a dual-port array (port A = write, port B = read)
        so TI can read earlier occasions while LS writes the last one.
      - When ``max_occasions == 1``, the single occasion is dual-port.

    :param max_occasions: 3
    :param SRAM_DEPTH: 273
    :param Qu_H_interp_f: QuType(12, 4, True)
        Per-component QuType for frequency-interpolated H estimates.
        Complex wire width = 2 * Qu_H_interp_f.DWT.
    :param TI_RE_PARALLELISM: 3
    :param RB_PARALLELISM: 1
    :param SRAM_MACRO_CONFIG: None
        When set, generates SRAM macro instantiations instead of behavioral
        ``reg`` arrays.  Dict with keys:
          - ``'sp_module'``: SP SRAM module name (e.g. ``'sram_sp_72x512'``)
          - ``'dp_module'``: 1R1W RF module name (e.g. ``'sram_1r1w_72x512'``)
          - ``'macro_depth'``: Actual macro depth (must be >= SRAM_DEPTH)
        When None (default), generates behavioral ``reg`` arrays for simulation.
    """
    if max_occasions < 1:
        raise ValueError("max_occasions must be >= 1")
    if SRAM_DEPTH < 1:
        raise ValueError("SRAM_DEPTH must be >= 1")
    if 12 % TI_RE_PARALLELISM != 0:
        raise ValueError(f"TI_RE_PARALLELISM={TI_RE_PARALLELISM} must divide 12")

    # Derive complex wire width from per-component QuType
    H_interp_f_DWT = 2 * Qu_H_interp_f.DWT

    N_BANKS = RB_PARALLELISM * (12 // TI_RE_PARALLELISM)
    FULL_DATA_WIDTH = RB_PARALLELISM * 12 * H_interp_f_DWT  # write port width
    BANK_DATA_WIDTH = TI_RE_PARALLELISM * H_interp_f_DWT    # per-bank read width
    ADDR_WIDTH = max(math.ceil(math.log2(SRAM_DEPTH)), 1) if SRAM_DEPTH > 1 else 1
    OCC_SEL_WIDTH = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1
    BANK_SEL_WIDTH = max(math.ceil(math.log2(N_BANKS)), 1) if N_BANKS > 1 else 1

    USE_MACRO = SRAM_MACRO_CONFIG is not None
    if USE_MACRO:
        if 'roles' not in SRAM_MACRO_CONFIG:
            raise ValueError("SRAM_MACRO_CONFIG requires candidate-derived memory roles")
        _SP_ROLE = SRAM_MACRO_CONFIG['roles']['pilot_buffer_single_port']
        _DP_ROLE = SRAM_MACRO_CONFIG['roles']['pilot_buffer_one_read_one_write']
        _SP_TIEOFFS = SRAM_MACRO_CONFIG.get('sp_tieoff_ports', [("RET1N", "1'b1")])
        _DP_TIEOFFS = SRAM_MACRO_CONFIG.get('dp_tieoff_ports', [("RET1N", "1'b1")])
        if _SP_ROLE['logical_width'] != BANK_DATA_WIDTH or _DP_ROLE['logical_width'] != BANK_DATA_WIDTH:
            raise ValueError("pilot buffer memory role width mismatch")
        if _SP_ROLE['macro_depth'] != _DP_ROLE['macro_depth']:
            raise ValueError("pilot buffer macro depths must match")
        MACRO_DEPTH = _SP_ROLE['macro_depth']
        MACRO_ADDR_WIDTH = max(math.ceil(math.log2(MACRO_DEPTH)), 1)
        if MACRO_DEPTH < SRAM_DEPTH:
            raise ValueError(f"SRAM macro depth={MACRO_DEPTH} < SRAM_DEPTH={SRAM_DEPTH}")

    #/ `timescale 1ns / 1ps
    #/ module PILOT_SRAM_BANK (
    #/     input clk,
    #/     input rst_n,
    #/     
    #/     // Write interface -- during S_RUN, from freq-interp pipeline
    #/     input wr_en,
    if max_occasions > 1:
        #/ input [`OCC_SEL_WIDTH`-1:0] wr_occasion_sel,
        pass
    #/ input [`ADDR_WIDTH`-1:0]      wr_addr,
    #/ input [`FULL_DATA_WIDTH`-1:0] wr_data,
    #/ 
    #/ // Read interface -- during S_TIME_INTERP, from TI controller
    #/ input                    rd_en,
    #/ input [`ADDR_WIDTH`-1:0] rd_addr,
    if N_BANKS > 1:
        #/ input [`BANK_SEL_WIDTH`-1:0] rd_bank_sel,
        pass

    # Declare per-occasion read-data output ports (bank-width)
    for occ in range(max_occasions):
        if occ < max_occasions - 1:
            #/ output [`BANK_DATA_WIDTH`-1:0] `f"rd_data_occ{occ}"`,
            pass
        else:
            #/ output [`BANK_DATA_WIDTH`-1:0] `f"rd_data_occ{occ}"`
            pass

    #/ );
    #/ 

    if not USE_MACRO:
        # ==================================================================
        # BEHAVIORAL MODE: reg arrays (for simulation / FPGA)
        # ==================================================================

        # ---- Per-occasion, per-bank SRAM arrays ----
        # Mixed mode: occasions 0..N-2 single-port, occasion N-1 dual-port
        for occ in range(max_occasions):
            is_dual = (occ == max_occasions - 1)
            mode_label = 'dual_port' if is_dual else 'single_port'
            for bank in range(N_BANKS):
                #/ // ===== Occasion `occ`, Bank `bank` SRAM (`mode_label`) =====
                if is_dual:
                    #/ // synthesis: infer dual-port block RAM (port A=write, port B=read)
                    pass
                #/ reg [`BANK_DATA_WIDTH`-1:0] `f"sram_occ{occ}_b{bank}"` [0:`SRAM_DEPTH`-1];
                pass
            #/
            pass

        # ---- Write logic: all banks written in parallel, decode wr_occasion_sel ----
        for occ in range(max_occasions):
            for bank in range(N_BANKS):
                lo = bank * BANK_DATA_WIDTH
                hi = lo + BANK_DATA_WIDTH - 1
                #/ always @(posedge clk) begin
                if max_occasions > 1:
                    #/ if (wr_en && (wr_occasion_sel == `OCC_SEL_WIDTH`'d`occ`)) begin
                    pass
                else:
                    #/ if (wr_en) begin
                    pass
                #/ `f"sram_occ{occ}_b{bank}"`[wr_addr] <= wr_data[`hi`:`lo`];
                #/ end
                #/ end
                #/
                pass

        # ---- Read logic: only selected bank reads (synchronous, 1-clk latency) ----
        for occ in range(max_occasions):
            #/ reg [`BANK_DATA_WIDTH`-1:0] `f"sram_rd_occ{occ}"`;
            pass
        #/

        for occ in range(max_occasions):
            #/ always @(posedge clk) begin
            #/     if (rd_en) begin
            if N_BANKS > 1:
                #/ case (rd_bank_sel)
                for bank in range(N_BANKS):
                    #/ `BANK_SEL_WIDTH`'d`bank`: `f"sram_rd_occ{occ}"` <= `f"sram_occ{occ}_b{bank}"`[rd_addr];
                    pass
                #/ default: `f"sram_rd_occ{occ}"` <= {`BANK_DATA_WIDTH`{1'bx}};
                #/ endcase
                pass
            else:
                #/ `f"sram_rd_occ{occ}"` <= `f"sram_occ{occ}_b0"`[rd_addr];
                pass
            #/ end
            #/ end
            #/
            pass

        # ---- Output assignments ----
        for occ in range(max_occasions):
            #/ assign `f"rd_data_occ{occ}"` = `f"sram_rd_occ{occ}"`;
            pass

        #/ // SRAM: per-occasion mixed mode (occ 0..N-2 single_port, occ N-1 dual_port)

    else:
        # ==================================================================
        # MACRO MODE: TSMC 65 nm GP ARM SRAM macro instantiations (for ASIC)
        # ==================================================================
        # SP occasions (0..N-2): ARM SP SRAM — single shared address port
        #   Ports: CLK, CEN(~en), WEN(~wr), A, D, Q, EMA, EMAW, RET1N,
        #          TEN, TCEN, TWEN, TA, TD, SI, SE, DFTRAMBYP
        # DP occasion (N-1): ARM 1R1W RF — separate read/write ports
        #   Ports: CLKA, CENA(~rd_en), AA, QA,
        #          CLKB, CENB(~wr_en), AB, DB,
        #          EMAA, EMAB, RET1N, COLLDISN

        # Internal wires for write-enable per occasion
        for occ in range(max_occasions):
            if max_occasions > 1:
                #/ wire `f"wr_en_occ{occ}"` = wr_en & (wr_occasion_sel == `OCC_SEL_WIDTH`'d`occ`);
                pass
            else:
                #/ wire wr_en_occ0 = wr_en;
                pass

        # Address zero-extension (macro may be deeper than design needs)
        ADDR_PAD = MACRO_ADDR_WIDTH - ADDR_WIDTH
        wr_addr_ext = f"{{{ADDR_PAD}'b0, wr_addr}}" if ADDR_PAD > 0 else "wr_addr"
        rd_addr_ext = f"{{{ADDR_PAD}'b0, rd_addr}}" if ADDR_PAD > 0 else "rd_addr"

        # Per-occasion, per-bank macro instantiation
        for occ in range(max_occasions):
            is_dual = (occ == max_occasions - 1)
            for bank in range(N_BANKS):
                lo = bank * BANK_DATA_WIDTH
                hi = lo + BANK_DATA_WIDTH - 1
                inst = f"u_sram_occ{occ}_b{bank}"

                # Per-bank read data wire
                #/ wire [`BANK_DATA_WIDTH`-1:0] `f"sram_q_occ{occ}_b{bank}"`;
                pass

                if not is_dual:
                    # --- SP SRAM: shared address for read/write ---
                    # CEN active when either reading this bank or writing this occasion
                    if N_BANKS > 1:
                        #/ wire `f"sp_rd_sel_occ{occ}_b{bank}"` = rd_en & (rd_bank_sel == `BANK_SEL_WIDTH`'d`bank`);
                        #/ wire `f"sp_cen_occ{occ}_b{bank}"` = ~(`f"wr_en_occ{occ}"` | `f"sp_rd_sel_occ{occ}_b{bank}"`);
                        #/ wire `f"sp_wen_occ{occ}_b{bank}"` = ~`f"wr_en_occ{occ}"`;
                        sp_addr_expr = f'{f"wr_en_occ{occ}"} ? {wr_addr_ext} : {rd_addr_ext}'
                        #/ wire [`MACRO_ADDR_WIDTH`-1:0] `f"sp_addr_occ{occ}_b{bank}"` = `sp_addr_expr`;
                        pass
                    else:
                        #/ wire `f"sp_cen_occ{occ}_b{bank}"` = ~(`f"wr_en_occ{occ}"` | rd_en);
                        #/ wire `f"sp_wen_occ{occ}_b{bank}"` = ~`f"wr_en_occ{occ}"`;
                        sp_addr_expr = f'{f"wr_en_occ{occ}"} ? {wr_addr_ext} : {rd_addr_ext}'
                        #/ wire [`MACRO_ADDR_WIDTH`-1:0] `f"sp_addr_occ{occ}_b{bank}"` = `sp_addr_expr`;
                        pass

                    _tile_offset = 0
                    for _tile_idx, _tile in enumerate(_SP_ROLE['tiles']):
                        _tile_width = _tile['width']
                        _tile_module = _tile['module']
                        _tile_hi = _tile_offset + _tile_width - 1
                        _tile_q = f"sram_q_occ{occ}_b{bank}_tile{_tile_idx}"
                        _tile_inst = f"{inst}_tile{_tile_idx}"
                        #/ wire [`_tile_width`-1:0] `_tile_q`;
                        #/ `_tile_module` `_tile_inst` (
                        #/     .CLK    (clk),
                        #/     .CEN    (`f"sp_cen_occ{occ}_b{bank}"`),
                        #/     .WEN    (`f"sp_wen_occ{occ}_b{bank}"`),
                        #/     .A      (`f"sp_addr_occ{occ}_b{bank}"`),
                        #/     .D      (wr_data[`lo + _tile_hi`:`lo + _tile_offset`]),
                        #/     .Q      (`_tile_q`)`"," if _SP_TIEOFFS else ""`
                        for _ti, (_port, _val) in enumerate(_SP_TIEOFFS):
                            _comma = "," if _ti < len(_SP_TIEOFFS) - 1 else ""
                            #/     .`_port`  (`_val`)`_comma`
                            pass
                        #/ );
                        #/ assign `f"sram_q_occ{occ}_b{bank}"`[`_tile_hi`:`_tile_offset`] = `_tile_q`;
                        _tile_offset = _tile_hi + 1
                else:
                    # --- 1R1W RF: separate read/write ports ---
                    if N_BANKS > 1:
                        #/ wire `f"dp_rd_en_occ{occ}_b{bank}"` = rd_en & (rd_bank_sel == `BANK_SEL_WIDTH`'d`bank`);
                        pass
                    else:
                        #/ wire `f"dp_rd_en_occ{occ}_b{bank}"` = rd_en;
                        pass

                    _tile_offset = 0
                    for _tile_idx, _tile in enumerate(_DP_ROLE['tiles']):
                        _tile_width = _tile['width']
                        _tile_module = _tile['module']
                        _tile_hi = _tile_offset + _tile_width - 1
                        _tile_q = f"sram_q_occ{occ}_b{bank}_tile{_tile_idx}"
                        _tile_inst = f"{inst}_tile{_tile_idx}"
                        #/ wire [`_tile_width`-1:0] `_tile_q`;
                        #/ `_tile_module` `_tile_inst` (
                        #/     .CLKA   (clk),
                        #/     .CENA   (~`f"dp_rd_en_occ{occ}_b{bank}"`),
                        #/     .AA     (`rd_addr_ext`),
                        #/     .QA     (`_tile_q`),
                        #/     .CLKB   (clk),
                        #/     .CENB   (~`f"wr_en_occ{occ}"`),
                        #/     .AB     (`wr_addr_ext`),
                        #/     .DB     (wr_data[`lo + _tile_hi`:`lo + _tile_offset`])`"," if _DP_TIEOFFS else ""`
                        for _ti, (_port, _val) in enumerate(_DP_TIEOFFS):
                            _comma = "," if _ti < len(_DP_TIEOFFS) - 1 else ""
                            #/     .`_port`  (`_val`)`_comma`
                            pass
                        #/ );
                        #/ assign `f"sram_q_occ{occ}_b{bank}"`[`_tile_hi`:`_tile_offset`] = `_tile_q`;
                        _tile_offset = _tile_hi + 1

        # ---- Read MUX: macros already provide the one synchronous read stage ----
        if N_BANKS > 1:
            #/ reg [`BANK_SEL_WIDTH`-1:0] rd_bank_sel_q;
            #/ always @(posedge clk) begin
            #/     if (rd_en) begin
            #/         rd_bank_sel_q <= rd_bank_sel;
            #/     end
            #/ end
            pass
        for occ in range(max_occasions):
            #/ reg [`BANK_DATA_WIDTH`-1:0] `f"sram_rd_occ{occ}"`;
            if N_BANKS > 1:
                #/ always @(*) begin
                #/     case (rd_bank_sel_q)
                for bank in range(N_BANKS):
                    #/     `BANK_SEL_WIDTH`'d`bank`: `f"sram_rd_occ{occ}"` = `f"sram_q_occ{occ}_b{bank}"`;
                    pass
                #/     default: `f"sram_rd_occ{occ}"` = {`BANK_DATA_WIDTH`{1'bx}};
                #/     endcase
                #/ end
                pass
            else:
                #/ always @(*) begin
                #/     `f"sram_rd_occ{occ}"` = `f"sram_q_occ{occ}_b0"`;
                #/ end
                pass
            #/ assign `f"rd_data_occ{occ}"` = `f"sram_rd_occ{occ}"`;
            pass

        #/ // SRAM: macro mode (TSMC 65 nm GP ARM SP + 1R1W memory)

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    # Behavioral mode (simulation)
    ModulePILOT_SRAM_BANK(
        max_occasions=3,
        SRAM_DEPTH=273,
        Qu_H_interp_f=QuType(12, 4, True),
        TI_RE_PARALLELISM=3,
        RB_PARALLELISM=1,
    )

    # Macro mode (ASIC synthesis)
    ModulePILOT_SRAM_BANK(
        max_occasions=3,
        SRAM_DEPTH=273,
        Qu_H_interp_f=QuType(12, 4, True),
        TI_RE_PARALLELISM=3,
        RB_PARALLELISM=1,
        SRAM_MACRO_CONFIG={
            'sp_module': 'sram_sp_72x512',
            'dp_module': 'sram_1r1w_72x512',
            'macro_depth': 512,
        },
    )
