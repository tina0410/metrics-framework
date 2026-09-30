###################################################################################################
# Module Name: CFG_LATCH
# Description: Per-slot configuration latching register bank.
#   Packs all runtime configuration inputs into a single wide register that
#   updates synchronously whenever latch_en is asserted (slot_boundary or
#   S_IDLE).  When latch_en is low the register retains its current value
#   via a self-feedback mux (clock-enable emulation using ModuleDelay).
#
#   Implementation pattern:
#     packed_raw  = {all raw inputs}
#     packed_d    = latch_en ? packed_raw : packed_cfg   (mux)
#     packed_cfg  = ModuleDelay(packed_d)                (register)
#     cfg_*       = unpacked slices of packed_cfg        (assign)
#
#   All bits reset to 0 on reset (original non-zero reset values are
#   intentionally dropped per design decision).
#
# Author: Auto-generated
# Date: 2026.3.7
# Version: V1.0.0
# Dependency Modules: Delay
###################################################################################################
import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from basic_modules import QuType, ModuleDelay


@convert
def ModuleCFG_LATCH(Qu_slot_idx: QuType,counter_width: int,N_CLK: int,IF_RST_N: bool,has_is_double_dmrs: bool,has_is_enhanced: bool,has_dmrs_type: bool,has_typeA_pos: bool,cdm_sel_bits: int,has_is_ECP: bool,n_add_width: int,num_ports: int) -> None:
    """
    Per-slot configuration latch bank.

    All raw inputs are packed into a single TOTAL_W-bit vector.  A mux
    feeds either the fresh raw value (latch_en=1) or the current registered
    value (latch_en=0) into a ModuleDelay.  The delay output is then
    unpacked back to individual cfg_* output wires.

    Reset: all bits → 0 (async if IF_RST_N=True, sync otherwise).

    :param Qu_slot_idx: QuType(4, 0, False)
    :param counter_width: 9
    :param N_CLK: 1
        Pipeline stages (1 = single-cycle register).
    :param IF_RST_N: True
        True → asynchronous reset (negedge rst_n).
        False → No reset.
    :param has_is_double_dmrs: False
    :param has_is_enhanced: False
    :param has_dmrs_type: False
    :param has_typeA_pos: False
    :param cdm_sel_bits: 0
        Width of num_cdm_groups_without_data port. 0 = port absent.
    :param has_is_ECP: False
    :param n_add_width: 0
        Width of n_additional_dmrs port. 0 = port absent.
    :param num_ports: 0
        Number of per-port port_enable_N / cfg_port_enable_N pairs. 0 = absent.
    """
    # ---- Build ordered field list: (raw_port_name, cfg_port_name, width) ----
    # First entry = MSBs in concat expression, last entry = LSBs.
    SI_DWT = Qu_slot_idx.DWT

    fields: list[tuple[str, str, int]] = []
    fields.append(('N_ID',                'cfg_N_ID',                16))
    fields.append(('n_scid',              'cfg_n_scid',              1))
    fields.append(('current_slot_idx',    'cfg_current_slot_idx',    SI_DWT))
    fields.append(('pusch_symbol_length', 'cfg_pusch_symbol_length', 4))
    fields.append(('num_RBs',             'cfg_num_RBs',             counter_width))
    if has_is_double_dmrs:
        fields.append(('is_double_dmrs',            'cfg_is_double_dmrs',             1))
    if has_is_enhanced:
        fields.append(('is_enhanced',               'cfg_is_enhanced',                1))
    if has_dmrs_type:
        fields.append(('dmrs_type',                 'cfg_dmrs_type',                  1))
    if has_typeA_pos:
        fields.append(('dmrs_typeA_pos_sel',        'cfg_dmrs_typeA_pos_sel',         1))
    if cdm_sel_bits > 0:
        fields.append(('num_cdm_groups_without_data', 'cfg_num_cdm_groups_without_data', cdm_sel_bits))
    if has_is_ECP:
        fields.append(('is_ECP',                    'cfg_is_ECP',                     1))
    if n_add_width > 0:
        fields.append(('n_additional_dmrs',         'cfg_n_additional_dmrs',          n_add_width))
    for i in range(num_ports):
        fields.append((f'port_enable_{i}', f'cfg_port_enable_{i}', 1))

    TOTAL_W = sum(w for _, _, w in fields)

    # ---- Module port list ----
    #/ `timescale 1ns / 1ps
    #/ module CFG_LATCH (
    #/     clk
    if IF_RST_N:
        #/ , rst_n
        pass
    #/ , latch_en
    for raw_name, cfg_name, width in fields:
        #/ , `raw_name`
        pass
    for raw_name, cfg_name, width in fields:
        #/ , `cfg_name`
        pass
    #/ );

    # ---- Port type declarations ----
    #/ input wire clk;
    if IF_RST_N:
        #/ input wire rst_n;
        pass
    #/ input wire latch_en;
    #/ 
    for raw_name, cfg_name, width in fields:
        if width == 1:
            #/ input wire `raw_name`;
            pass
        else:
            #/ input wire [`width`-1:0] `raw_name`;
            pass
    #/ 
    for raw_name, cfg_name, width in fields:
        if width == 1:
            #/ output wire `cfg_name`;
            pass
        else:
            #/ output wire [`width`-1:0] `cfg_name`;
            pass
    #/ 

    # ---- Pack raw inputs ----
    _concat_raw = "{" + ", ".join(r for r, _, _ in fields) + "}"
    #/ wire [`TOTAL_W`-1:0] packed_raw = `_concat_raw`;
    #/ 

    # ---- Mux: latch_en selects new value or hold (self-feedback) ----
    #/ wire [`TOTAL_W`-1:0] packed_cfg;
    #/ wire [`TOTAL_W`-1:0] packed_d = latch_en ? packed_raw : packed_cfg;
    #/ 

    # ---- ModuleDelay: N_CLK-stage register (with reset to 0) ----
    _delay_ports: dict = {'i_data': 'packed_d', 'o_data': 'packed_cfg', 'i_clk': 'clk'}
    if IF_RST_N:
        _delay_ports['i_rst_n'] = 'rst_n'
    ModuleDelay(DWT=TOTAL_W, N_CLK=N_CLK, IF_RST_N=IF_RST_N, PORTS=_delay_ports)
    #/ 

    # ---- Unpack: assign each cfg_* from its slice of packed_cfg ----
    #/ // Unpack: last field in list → lowest bits
    _offset = 0
    for raw_name, cfg_name, width in reversed(fields):
        _hi = _offset + width - 1
        _lo = _offset
        #/ assign `cfg_name` = packed_cfg[`_hi`:`_lo`];
        _offset += width
    #/ 

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    ModuleCFG_LATCH(
        Qu_slot_idx=QuType(4, 0, False),
        counter_width=9,
        N_CLK=1,
        IF_RST_N=True,
        has_is_double_dmrs=False,
        has_is_enhanced=False,
        has_dmrs_type=True,
        has_typeA_pos=False,
        cdm_sel_bits=1,
        has_is_ECP=False,
        n_add_width=2,
        num_ports=2,
    )
