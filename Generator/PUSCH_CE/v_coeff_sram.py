###################################################################################################
# Module Name: COEFF_SRAM
# Description: Coefficient SRAM for LMMSE interpolation matrix storage.
#   Stores W[k][j] coefficients (N_OUTPUT × N_PILOTS entries) in register-file
#   arrays inferrable as SRAM.
#
#   Two storage modes (selected at elaborate-time via COEFF_STORAGE parameter):
#     'ROM':  Coefficients hardwired at build time. No write interface.
#     'SRAM': Coefficients loaded at runtime via a sequential write port
#             during the FSM S_COEFF_LOAD state. Read port delivers
#             a full column of coefficients (all N_OUTPUT values for a given
#             pilot j) in a single cycle.
#     'BOTH': Dual-mode. Hardwired ROM as default; SRAM overlay loaded at
#             runtime. A cfg_use_sram input selects the active source.
#
#   Read interface:  Addressed by pilot index j → outputs all N_OUTPUT W[k][j].
#   Write interface: Sequential word-at-a-time (addr = k * N_PILOTS + j).
#
#   For Hybrid mode: Two banks (Type1 / Type2) selected by dmrs_type.
#
# Author: Auto-generated
# Date: 2026.3.11
# Version: V1.0.0
###################################################################################################
import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import List, Literal, Optional
from basic_modules import QuType


@convert
def ModuleCOEFF_SRAM(N_OUTPUT: int, N_PILOTS: int, Qu_COEFF: QuType, COEFF_STORAGE: Literal['ROM', 'SRAM', 'BOTH'] = 'BOTH', is_hybrid: bool = False, rom_data_bank0: Optional[List[List[int]]] = None, rom_data_bank1: Optional[List[List[int]]] = None, BEAT_MODE: bool = False, N_PILOTS_PER_BEAT: int = 1, FILL_BEATS: int = 1):
    """
    Coefficient SRAM / ROM for LMMSE interpolation.

    Two addressing schemes:
      BEAT_MODE=False (default): Column-parallel read.
        Stores W[N_OUTPUT × N_PILOTS]. rd_pilot_idx selects a pilot column,
        returning all N_OUTPUT values simultaneously.
      BEAT_MODE=True: Beat-parallel read (for freq-domain LMMSE core).
        Stores W reshaped as [FILL_BEATS][N_OUTPUT × N_PILOTS_PER_BEAT].
        rd_beat_idx selects a beat, returning all N_OUTPUT × N_PILOTS_PER_BEAT
        coefficients for one beat simultaneously.

    Write port: sequential word-at-a-time during COEFF_LOAD phase.

    :param N_OUTPUT: 48
        Number of output REs (e.g. 12 × LMMSE_P).
    :param N_PILOTS: 24
        Number of pilot inputs (e.g. 6 × LMMSE_P).
    :param Qu_COEFF: QuType(12, 10, True)
        QuType for coefficients. COEFF_DWT = Qu_COEFF.DWT.
    :param COEFF_STORAGE: 'BOTH'
        Storage mode: 'ROM', 'SRAM', or 'BOTH'.
    :param is_hybrid: False
        True for dual-bank (Type1/Type2) support.
    :param rom_data_bank0: None
        ROM initialisation data [N_OUTPUT][N_PILOTS] as quantised integers.
        Required when COEFF_STORAGE is 'ROM' or 'BOTH'.
    :param rom_data_bank1: None
        Second bank ROM data (Hybrid mode only).
    :param BEAT_MODE: False
        If True, use beat-indexed storage for freq-domain LMMSE core.
    :param N_PILOTS_PER_BEAT: 1
        Number of pilots processed per beat (only used when BEAT_MODE=True).
    :param FILL_BEATS: 1
        Number of beats (only used when BEAT_MODE=True).
    """

    # Derive raw width from QuType
    COEFF_DWT = Qu_COEFF.DWT

    TOTAL_ENTRIES = N_OUTPUT * N_PILOTS
    ADDR_W = max(math.ceil(math.log2(TOTAL_ENTRIES)), 1)

    if BEAT_MODE:
        # Beat-indexed mode: read one beat's worth of coefficients at a time
        COEFF_PER_BEAT = N_OUTPUT * N_PILOTS_PER_BEAT
        RD_DATA_W = COEFF_PER_BEAT * COEFF_DWT
        BEAT_IDX_W = max(math.ceil(math.log2(FILL_BEATS)), 1)
    else:
        # Column mode: read all N_OUTPUT coefficients for one pilot
        PILOT_IDX_W = max(math.ceil(math.log2(N_PILOTS)), 1)
        RD_DATA_W = N_OUTPUT * COEFF_DWT

    has_rom = COEFF_STORAGE in ('ROM', 'BOTH')
    has_sram = COEFF_STORAGE in ('SRAM', 'BOTH')
    has_both = COEFF_STORAGE == 'BOTH'

    N_BANKS = 2 if is_hybrid else 1

    #/ `timescale 1ns / 1ps
    #/ module COEFF_SRAM (
    #/     input clk,
    #/     input rst_n,

    if has_sram:
        #/ // Write interface -- COEFF_LOAD phase
        #/ input                   wr_en,
        #/ input [`ADDR_W`-1:0]    wr_addr,
        #/ input [`COEFF_DWT`-1:0] wr_data,
        if is_hybrid:
            #/ input wr_bank_sel,
            pass

    #/ // Read interface -- RUN phase
    if BEAT_MODE:
        #/ input [`BEAT_IDX_W`-1:0] rd_beat_idx,
        pass
    else:
        #/ input [`PILOT_IDX_W`-1:0] rd_pilot_idx,
        pass
    if is_hybrid:
        #/ input rd_bank_sel,
        pass
    if has_both:
        #/ input cfg_use_sram,
        pass

    #/ output [`RD_DATA_W`-1:0] rd_data
    #/ );

    # =========================================================================
    # ROM: Hardwired coefficient storage
    # =========================================================================
    if has_rom:
        for bank in range(N_BANKS):
            rom_data = rom_data_bank0 if bank == 0 else rom_data_bank1
            suffix = f"_b{bank}" if is_hybrid else ""
            #/ // ===== ROM Bank `bank` =====
            if BEAT_MODE:
                # Beat-indexed ROM: each entry = N_OUTPUT * N_PILOTS_PER_BEAT coefficients
                for beat in range(FILL_BEATS):
                    parts = []
                    for k in range(N_OUTPUT - 1, -1, -1):
                        for q in range(N_PILOTS_PER_BEAT - 1, -1, -1):
                            j = beat * N_PILOTS_PER_BEAT + q
                            val = rom_data[k][j] if rom_data is not None else 0
                            val_unsigned = val & ((1 << COEFF_DWT) - 1)
                            parts.append(f"{COEFF_DWT}'d{val_unsigned}")
                    concat = "{" + ", ".join(parts) + "}"
                    #/ wire [`RD_DATA_W`-1:0] `f"rom{suffix}_beat_{beat}"` = `concat`;
                    pass

                # ROM beat MUX
                #/ reg [`RD_DATA_W`-1:0] `f"rom{suffix}_rd"`;
                #/ always @(*) begin
                #/     case (rd_beat_idx)
                for beat in range(FILL_BEATS):
                    #/ `BEAT_IDX_W`'d`beat`: `f"rom{suffix}_rd"` = `f"rom{suffix}_beat_{beat}"`;
                    pass
                #/ default: `f"rom{suffix}_rd"` = `RD_DATA_W`'d0;
                #/ endcase
                #/ end
            else:
                # Column-indexed ROM: each entry = N_OUTPUT coefficients for pilot j
                for j in range(N_PILOTS):
                    parts = []
                    for k in range(N_OUTPUT - 1, -1, -1):
                        val = rom_data[k][j] if rom_data is not None else 0
                        val_unsigned = val & ((1 << COEFF_DWT) - 1)
                        parts.append(f"{COEFF_DWT}'d{val_unsigned}")
                    concat = "{" + ", ".join(parts) + "}"
                    #/ wire [`RD_DATA_W`-1:0] `f"rom{suffix}_col_{j}"` = `concat`;
                    pass

                # ROM column MUX
                #/ reg [`RD_DATA_W`-1:0] `f"rom{suffix}_rd"`;
                #/ always @(*) begin
                #/     case (rd_pilot_idx)
                for j in range(N_PILOTS):
                    #/ `PILOT_IDX_W`'d`j`: `f"rom{suffix}_rd"` = `f"rom{suffix}_col_{j}"`;
                    pass
                #/ default: `f"rom{suffix}_rd"` = `RD_DATA_W`'d0;
                #/ endcase
                #/ end

    # =========================================================================
    # SRAM: Runtime-loadable coefficient storage
    # =========================================================================
    if has_sram:
        #/ // ===== COEFF_SRAM write clock gate =====
        #/ reg wr_en_latched;
        #/ always @(clk or wr_en)
        #/     if (!clk) wr_en_latched <= wr_en;
        #/ wire clk_wr = clk & wr_en_latched;
        #/
        for bank in range(N_BANKS):
            suffix = f"_b{bank}" if is_hybrid else ""
            #/ // ===== SRAM Bank `bank` =====
            #/ reg [`COEFF_DWT`-1:0] `f"sram{suffix}"` [0:`TOTAL_ENTRIES - 1`];

            # Write logic
            if is_hybrid:
                #/ always @(posedge clk_wr) begin
                #/     if (wr_bank_sel == 1'b`bank`) begin
                #/         `f"sram{suffix}"`[wr_addr] <= wr_data;
                #/     end
                #/ end
                pass
            else:
                #/ always @(posedge clk_wr) begin
                #/     `f"sram{suffix}"`[wr_addr] <= wr_data;
                #/ end
                pass

            if BEAT_MODE:
                # Read: gather all coefficients for the selected beat
                # Storage layout: w[k][q] at address k * N_PILOTS + (beat * N_PILOTS_PER_BEAT + q)
                for k in range(N_OUTPUT):
                    for q in range(N_PILOTS_PER_BEAT):
                        addr_expr = f"{k} * {N_PILOTS} + rd_beat_idx * {N_PILOTS_PER_BEAT} + {q}"
                        flat_idx = k * N_PILOTS_PER_BEAT + q
                        #/ wire [`COEFF_DWT`-1:0] `f"sram{suffix}_e{flat_idx}"` = `f"sram{suffix}"`[`addr_expr`];
                        pass
                # Pack into wide bus (same bit ordering as ROM beat mode)
                sram_parts = []
                for k in range(N_OUTPUT - 1, -1, -1):
                    for q in range(N_PILOTS_PER_BEAT - 1, -1, -1):
                        flat_idx = k * N_PILOTS_PER_BEAT + q
                        sram_parts.append(f"sram{suffix}_e{flat_idx}")
                sram_concat = "{" + ", ".join(sram_parts) + "}"
                #/ wire [`RD_DATA_W`-1:0] `f"sram{suffix}_rd"` = `sram_concat`;
            else:
                # Read: gather a full column (all N_OUTPUT coefficients for pilot j)
                for k in range(N_OUTPUT):
                    addr_expr = f"{k} * {N_PILOTS} + rd_pilot_idx"
                    #/ wire [`COEFF_DWT`-1:0] `f"sram{suffix}_k{k}"` = `f"sram{suffix}"`[`addr_expr`];
                    pass

                # Pack into wide bus
                sram_parts = [f"sram{suffix}_k{k}" for k in range(N_OUTPUT - 1, -1, -1)]
                sram_concat = "{" + ", ".join(sram_parts) + "}"
                #/ wire [`RD_DATA_W`-1:0] `f"sram{suffix}_rd"` = `sram_concat`;

    # =========================================================================
    # Output MUX
    # =========================================================================
    if has_both and is_hybrid:
        # 4-way: {rom_b0, rom_b1} × {sram_b0, sram_b1} selected by cfg_use_sram × rd_bank_sel
        #/ assign rd_data = cfg_use_sram
        #/ ? (rd_bank_sel ? sram_b1_rd : sram_b0_rd)
        #/ : (rd_bank_sel ? rom_b1_rd  : rom_b0_rd);
        pass
    elif has_both:
        #/ assign rd_data = cfg_use_sram ? sram_rd : rom_rd;
        pass
    elif has_rom and is_hybrid:
        #/ assign rd_data = rd_bank_sel ? rom_b1_rd : rom_b0_rd;
        pass
    elif has_rom:
        #/ assign rd_data = rom_rd;
        pass
    elif has_sram and is_hybrid:
        #/ assign rd_data = rd_bank_sel ? sram_b1_rd : sram_b0_rd;
        pass
    elif has_sram:
        #/ assign rd_data = sram_rd;
        pass

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    # Test: ROM-only, non-hybrid
    rom0 = [[i * 10 + j for j in range(6)] for i in range(12)]
    ModuleCOEFF_SRAM(
        N_OUTPUT=12,
        N_PILOTS=6,
        Qu_COEFF=QuType(12, 10, True),
        COEFF_STORAGE='BOTH',
        is_hybrid=False,
        rom_data_bank0=rom0,
        rom_data_bank1=None,
    )

    # Test: SRAM-only, beat mode (freq-domain LMMSE)
    ModuleCOEFF_SRAM(
        N_OUTPUT=48,
        N_PILOTS=24,
        Qu_COEFF=QuType(12, 10, True),
        COEFF_STORAGE='SRAM',
        is_hybrid=False,
        rom_data_bank0=None,
        rom_data_bank1=None,
        BEAT_MODE=True,
        N_PILOTS_PER_BEAT=6,
        FILL_BEATS=4,
    )
