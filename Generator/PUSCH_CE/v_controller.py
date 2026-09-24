"""
Controller Wrapper Module — consolidates 5 control sub-modules:
  CE_FSM, RB_COUNTER, SYMBOL_COUNTER, PILOT_SYMBOL_DETECTION, TI_CTRL

All internal timing (switch_cond routing, delay chains, boundary signals)
is handled internally. v_top.py only sees clean, delay-aligned outputs.

Uses ControlSignalGraph from analyze_timing.py for auto-derived delays.
"""
import math
from typing import List, Literal, Any

from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from basic_modules.PyTU import QuType
from v_rb_counter import ModuleRB_COUNTER
from v_symbol_counter import ModuleSYMBOL_COUNTER
from v_fsm import ModuleCE_FSM
from v_pilot_symbol_detection import ModulePILOT_SYMBOL_DETECTION
from v_ti_ctrl import ModuleTI_CTRL
from basic_modules import ModuleDelay
from analyze_timing import ControlSignalGraph


def _delay_ports(src, dst, if_rst_n=False):
    """Build standard delay module port map."""
    p = {'i_data': src, 'o_data': dst, 'i_clk': 'clk'}
    if if_rst_n:
        p['i_rst_n'] = 'rst_n'
    return p


@convert
def ModuleCONTROLLER(min_num_RBs: int, max_num_RBs: int, RB_PARALLELISM: int, max_pusch_symbols: int, is_double_dmrs: Any, additional_DMRS_range: List[int], dmrs_typeA_pos: str, num_symbols_range: tuple, LS_DRAIN_CYCLES: int, TI_PIPELINE_DEPTH: int, TI_RE_PARALLELISM: int, HAS_COEFF_SRAM: bool, ls_ctrl_graph: ControlSignalGraph, freq_interp_method: str, max_occasions: int, counter_width: int, SRAM_ADDR_WIDTH: int, Qu_symbol_idx: QuType, INPUT_MODE: Literal['A', 'B'], is_enhanced: Any, dmrs_Type: Any, is_ECP: Any, switchable_ports: bool, ANTENNA_PORTS: List[int], has_pre_fi_buf: bool = False, FI_WINDOW_SIZE: int = 1, FI_CYCLES_PER_OCC: int = 1, FI_CYCLES_PER_OCC_SINGLE: int = 1, FI_FILL_BEATS: int = 1, HAS_TI_GATE: bool = False) -> None:
    """
    Consolidated controller wrapper for CE pipeline.

    Instantiates: CE_FSM, RB_COUNTER, SYMBOL_COUNTER,
    PILOT_SYMBOL_DETECTION, TI_CTRL.

    All delay chains (ctrl_pilot_wr_en, ctrl_first_rb_d, etc.)
    are generated internally via ControlSignalGraph.
    """

    # ---- Port declarations ----
    #/ module CONTROLLER (
    #/     input clk,
    #/     input rst_n,
    #/     input ctrl_start,

    # Config inputs
    #/ input [3:0]                 cfg_pusch_symbol_length,
    #/ input [`counter_width`-1:0] cfg_num_RBs,

    # Optional Hybrid config inputs
    if len(additional_DMRS_range) > 1:
        _n_add_max = max(additional_DMRS_range)
        _n_add_width = max(math.ceil(math.log2(_n_add_max + 1)), 1)
        #/ input [`_n_add_width`-1:0] cfg_n_additional_dmrs,
        pass

    if dmrs_typeA_pos == "Hybrid":
        #/ input cfg_dmrs_typeA_pos_sel,
        pass

    if is_double_dmrs == "Hybrid":
        #/ input cfg_is_double_dmrs,
        pass

    if HAS_COEFF_SRAM:
        #/ input  coeff_load_done,
        #/ input  coeff_reload_req,
        #/ output coeff_loading,
        pass

    # Core FSM outputs
    #/ output       ctrl_ctr_en,
    #/ output       ctrl_ls_en,
    #/ output       ctrl_ti_en,
    #/ output       slot_ce_done,
    #/ output       cfg_latch_en,

    # Counter outputs
    #/ output [`counter_width`-1:0]     ctrl_rb_idx,
    #/ output [`counter_width`-1:0]     ctrl_rb_idx_r,
    #/ output [`Qu_symbol_idx.DWT`-1:0] ctrl_sym_idx,
    #/ output [`Qu_symbol_idx.DWT`-1:0] ctrl_sym_idx_next,

    # Pilot detection outputs
    #/ output ctrl_is_pilot,
    #/ output ctrl_l_prime,
    #/ output ctrl_is_last_dmrs,

    # Symbol boundaries
    #/ output ctrl_c_init_strb,

    # Delay-aligned LS signals
    #/ output                         ctrl_pilot_wr_en_raw,
    #/ output [`SRAM_ADDR_WIDTH`-1:0] ctrl_pilot_wr_addr,
    # RB-boundary flags: only the NN and Linear FI cores consume them. Under
    # LMMSE nothing reads them, so the ports (and the delay chain behind them in
    # build_ls_ctrl_graph) are omitted rather than tied off.
    _needs_rb_boundary = freq_interp_method in ('nn', 'linear')
    if _needs_rb_boundary and not has_pre_fi_buf:
        #/ output                         ctrl_first_rb_d,
        #/ output                         ctrl_last_rb_d,
        if RB_PARALLELISM > 1:
            #/ output [`RB_PARALLELISM`-1:0] ctrl_lane_last_d,
            pass
        pass

    OCC_SEL_WIDTH = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1
    if max_occasions > 1:
        #/ output [`OCC_SEL_WIDTH`-1:0] ctrl_occ_idx,
        pass
    if has_pre_fi_buf and max_occasions > 1:
        #/ output [`OCC_SEL_WIDTH`-1:0] ctrl_ybuf_occ_tag,
        pass

    if freq_interp_method == 'lmmse' and not has_pre_fi_buf:
        #/ output ctrl_freq_interp_en,
        pass

    if has_pre_fi_buf:
        #/ output fi_trigger,
        if max_occasions > 1:
            #/ output [`OCC_SEL_WIDTH`-1:0] fi_occ_sel,
            pass
        #/ output [`SRAM_ADDR_WIDTH`-1:0] fi_window_base,
        if _needs_rb_boundary:
            #/ output fi_first_rb,
            #/ output fi_last_rb,
            if RB_PARALLELISM > 1:
                #/ output [`RB_PARALLELISM`-1:0] fi_lane_last,
                pass
            pass


    # Only INPUT_MODE type B deals with remainder RBs
    if RB_PARALLELISM > 1 and INPUT_MODE == 'B':
        bit_remainder = math.ceil(math.log2(RB_PARALLELISM))
        #/ output [`bit_remainder`-1:0] ctrl_rb_remainder,
        #/ output                       ctrl_sym_overflow,
        pass

    if RB_PARALLELISM > 1:
        RB_WITHIN_WIDTH = max(math.ceil(math.log2(RB_PARALLELISM)), 1)
        #/ output [`RB_WITHIN_WIDTH`-1:0] ti_rb_within_beat,
        pass

    # TI control outputs
    #/ output                         ctrl_ti_sram_rd_en,
    #/ output [`SRAM_ADDR_WIDTH`-1:0] ctrl_ti_rb_addr,
    ti_re_group_width = max(math.ceil(math.log2(12 // TI_RE_PARALLELISM)), 1)
    #/ output [`ti_re_group_width`-1:0] ctrl_ti_re_group,
    #/ output                           ctrl_ti_valid,
    #/ output                           ctrl_ti_done
    if HAS_TI_GATE:
        #/ ,input                          ti_start_gate
        pass

    #/ );

    # ---- Internal wires ----
    #/ wire                           ctrl_start_int = ctrl_start;
    #/ wire                           ctrl_is_pilot_int;
    #/ wire                           ctrl_l_prime_int;
    #/ wire                           ctrl_is_last_dmrs_int;
    #/ wire                           ctrl_sym_switch_int;
    #/ wire                           ctrl_c_init_strb_int = ctrl_sym_switch_int & ctrl_is_pilot_int;
    #/ wire                           ctrl_slot_boundary_int;
    #/ wire                           ctrl_ctr_en_int;
    #/ wire                           ctrl_ls_en_int;
    #/ wire                           ctrl_ti_en_int;
    #/ wire                           ctrl_ti_done_int;
    #/ wire [`counter_width`-1:0]     ctrl_rb_idx_int;
    #/ wire [`counter_width`-1:0]     ctrl_rb_idx_r_int;
    #/ wire [`Qu_symbol_idx.DWT`-1:0] ctrl_sym_idx_int;
    #/ wire [`Qu_symbol_idx.DWT`-1:0] ctrl_sym_idx_next_int;
    #/ wire [1:0]                     ce_state_int;
    # RB_COUNTER always produces its boundary metadata when RB_PARALLELISM > 1.
    # Mode B exposes the metadata through CONTROLLER; Mode A still needs typed
    # internal sinks so Verilog does not create implicit one-bit nets.
    if RB_PARALLELISM > 1 and INPUT_MODE == 'A':
        _rb_remainder_width = math.ceil(math.log2(RB_PARALLELISM))
        #/ wire                             ctrl_sym_overflow;
        #/ wire [`_rb_remainder_width`-1:0] ctrl_rb_remainder;
        pass

    # ---- 1. CE_FSM ----
    #/ // ========== CE_FSM ==========
    ports_fsm = {
        'clk': 'clk',
        'rst_n': 'rst_n',
        'start': 'ctrl_start_int',
        'is_pilot_symbol': 'ctrl_is_pilot_int',
        'l_quote': 'ctrl_l_prime_int',
        'is_last_dmrs': 'ctrl_is_last_dmrs_int',
        'sym_switch': 'ctrl_sym_switch_int',
        'ti_done': 'ctrl_ti_done_int',
        'state': 'ce_state_int',
        'slot_boundary': 'ctrl_slot_boundary_int',
        'ctrl_ctr_en': 'ctrl_ctr_en_int',
        'ctrl_ls_en': 'ctrl_ls_en_int',
        'ctrl_ti_en': 'ctrl_ti_en_int',
        'ctrl_slot_done': 'slot_ce_done',
    }
    if is_double_dmrs == "Hybrid":
        ports_fsm['is_double_dmrs'] = 'cfg_is_double_dmrs'
    if HAS_COEFF_SRAM:
        ports_fsm['coeff_load_done'] = 'coeff_load_done'
        ports_fsm['coeff_loading'] = 'coeff_loading'
        ports_fsm['coeff_reload_req'] = 'coeff_reload_req'

    ModuleCE_FSM(
        max_pusch_symbols=max_pusch_symbols,
        is_double_dmrs=is_double_dmrs,
        LS_DRAIN_CYCLES=LS_DRAIN_CYCLES,
        HAS_COEFF_SRAM=HAS_COEFF_SRAM,
        PORTS=ports_fsm  # type: ignore
    )

    # ---- 2. RB_COUNTER ----
    #/ // ========== RB_COUNTER ==========
    ports_rb = {
        'clk': 'clk',
        'rst_n': 'rst_n',
        'ctrl_ctr_en': 'ctrl_ctr_en_int',
        'num_RBs': 'cfg_num_RBs',
        'ctrl_rb_idx_r': 'ctrl_rb_idx_r_int',
        'ctrl_rb_idx': 'ctrl_rb_idx_int',
        'ctrl_sym_switch': 'ctrl_sym_switch_int',
    }
    if RB_PARALLELISM > 1:
        ports_rb['ctrl_sym_overflow'] = 'ctrl_sym_overflow'
        ports_rb['ctrl_rb_remainder'] = 'ctrl_rb_remainder'

    ModuleRB_COUNTER(
        min_RBs=min_num_RBs,
        max_RBs=max_num_RBs,
        RB_PARALLELISM=RB_PARALLELISM,
        PORTS=ports_rb  # type: ignore
    )

    # ---- 3. SYMBOL_COUNTER ----
    #/ // ========== SYMBOL_COUNTER ==========
    ports_sym = {
        'clk': 'clk',
        'rst_n': 'rst_n',
        'ctrl_ctr_en': 'ctrl_ctr_en_int',
        'ctrl_sym_switch': 'ctrl_sym_switch_int',
        'pusch_symbol_length': 'cfg_pusch_symbol_length',
        'ctrl_sym_idx': 'ctrl_sym_idx_int',
        'ctrl_sym_idx_next': 'ctrl_sym_idx_next_int',
        'ctrl_slot_boundary': 'ctrl_slot_boundary_int',
    }

    ModuleSYMBOL_COUNTER(
        max_pusch_symbols=max_pusch_symbols,
        PORTS=ports_sym  # type: ignore
    )

    # ---- 4. PILOT_SYMBOL_DETECTION ----
    #/ // ========== PILOT_SYMBOL_DETECTION ==========
    ports_pilot = {
        'ctrl_sym_idx': 'ctrl_sym_idx_int',
        'ctrl_sym_idx_next': 'ctrl_sym_idx_next_int',
        'ctrl_sym_switch': 'ctrl_sym_switch_int',
        'pusch_symbol_length': 'cfg_pusch_symbol_length',
        'ctrl_is_pilot': 'ctrl_is_pilot_int',
        'ctrl_l_prime': 'ctrl_l_prime_int',
        'ctrl_is_last_dmrs': 'ctrl_is_last_dmrs_int',
    }
    if len(additional_DMRS_range) > 1:
        ports_pilot['n_additional_dmrs'] = 'cfg_n_additional_dmrs'
    if dmrs_typeA_pos == "Hybrid":
        ports_pilot['dmrs_typeA_pos_sel'] = 'cfg_dmrs_typeA_pos_sel'
    if is_double_dmrs == "Hybrid":
        ports_pilot['is_double_dmrs'] = 'cfg_is_double_dmrs'

    ModulePILOT_SYMBOL_DETECTION(
        max_pusch_symbols=max_pusch_symbols,
        dmrs_typeA_pos=dmrs_typeA_pos,
        is_double_dmrs=is_double_dmrs,
        additional_DMRS_range=additional_DMRS_range,
        num_symbols_range=num_symbols_range,
        PORTS=ports_pilot  # type: ignore
    )

    # ---- 5. TI_CTRL ----
    #/ // ========== TI_CTRL ==========
    if HAS_TI_GATE:
        #/ wire ctrl_ti_en_gated = ctrl_ti_en_int & ti_start_gate;
        _ti_en_signal = 'ctrl_ti_en_gated'
    else:
        _ti_en_signal = 'ctrl_ti_en_int'
    ports_ti = {
        'clk': 'clk',
        'rst_n': 'rst_n',
        'ctrl_ti_en': _ti_en_signal,
        'num_RBs': 'cfg_num_RBs',
        'ctrl_ti_sram_rd_en': 'ctrl_ti_sram_rd_en',
        'ctrl_ti_rb_addr': 'ctrl_ti_rb_addr',
        'ctrl_ti_re_group': 'ctrl_ti_re_group',
        'ctrl_ti_valid': 'ctrl_ti_valid',
        'ctrl_ti_done': 'ctrl_ti_done_int',
    }
    if RB_PARALLELISM > 1:
        ports_ti['ti_rb_within_beat'] = 'ti_rb_within_beat'
    if has_pre_fi_buf:
        ports_ti['fi_trigger'] = 'fi_trigger'
        if is_double_dmrs == "Hybrid":
            ports_ti['cfg_is_double_dmrs'] = 'cfg_is_double_dmrs'
        if len(additional_DMRS_range) > 1:
            ports_ti['cfg_n_additional_dmrs'] = 'cfg_n_additional_dmrs'
        if max_occasions > 1:
            ports_ti['fi_occ_sel'] = 'fi_occ_sel'
        ports_ti['fi_window_base'] = 'fi_window_base'
        if _needs_rb_boundary:
            ports_ti['fi_first_rb'] = 'fi_first_rb'
            ports_ti['fi_last_rb'] = 'fi_last_rb'
            if RB_PARALLELISM > 1:
                ports_ti['fi_lane_last'] = 'fi_lane_last'

    ModuleTI_CTRL(
        max_num_RBs=max_num_RBs,
        RB_PARALLELISM=RB_PARALLELISM,
        TI_RE_PARALLELISM=TI_RE_PARALLELISM,
        TI_PIPELINE_DEPTH=TI_PIPELINE_DEPTH,
        has_pre_fi_buf=has_pre_fi_buf,
        max_occasions=max_occasions,
        FI_WINDOW_SIZE=FI_WINDOW_SIZE,
        FI_CYCLES_PER_OCC=FI_CYCLES_PER_OCC,
        FI_CYCLES_PER_OCC_SINGLE=FI_CYCLES_PER_OCC_SINGLE,
        FI_FILL_BEATS=FI_FILL_BEATS,
        needs_rb_boundary=_needs_rb_boundary,
        runtime_n_additional=(len(additional_DMRS_range) > 1),
        runtime_double_dmrs=(is_double_dmrs == "Hybrid"),
        PORTS=ports_ti  # type: ignore
    )

    # ---- Boundary indicators ----
    # These exist only to feed the ctrl_first_rb_d / ctrl_last_rb_d delay chains.
    # Same predicate as the g.connect() in build_ls_ctrl_graph: without it the
    # comparators would be built and then read by nothing.
    if _needs_rb_boundary and not has_pre_fi_buf:
        #/ // ========== ctrl_first_rb / ctrl_last_rb ==========
        #/ wire ctrl_first_rb = (ctrl_rb_idx_int == `counter_width`'b0);
        if RB_PARALLELISM == 1:
            #/ wire ctrl_last_rb = (ctrl_rb_idx_int + `counter_width`'d1 == cfg_num_RBs);
            pass
        else:
            #/ wire ctrl_last_rb = (ctrl_rb_idx_int + `counter_width`'d`RB_PARALLELISM` >= cfg_num_RBs);
            # Per-lane logical-last-RB flag: lane `i` on beat base `ctrl_rb_idx_int`
            # is the final RB iff `ctrl_rb_idx_int + i == cfg_num_RBs - 1`.  This
            # resolves the last RB on a partial final beat to the correct lane
            # (remainder-1) rather than assuming it is always the last physical lane.
            for _lane in range(RB_PARALLELISM):
                #/ wire ctrl_lane_last_raw`_lane` = (ctrl_rb_idx_int + `counter_width`'d`_lane` == cfg_num_RBs - `counter_width`'d1);
                pass
            #/ wire [`RB_PARALLELISM`-1:0] ctrl_lane_last_raw = {`", ".join(f"ctrl_lane_last_raw{RB_PARALLELISM-1-lane}" for lane in range(RB_PARALLELISM))`};
            pass

    # ---- Pilot SRAM write address source ----
    #/ // ========== Pilot SRAM Write Address ==========
    if RB_PARALLELISM == 1:
        #/ wire [`SRAM_ADDR_WIDTH`-1:0] ctrl_pilot_wr_addr_raw = ctrl_rb_idx_int[`SRAM_ADDR_WIDTH`-1:0];
        pass
    else:
        _shift_bits = math.ceil(math.log2(RB_PARALLELISM))
        #/ wire [`SRAM_ADDR_WIDTH`-1:0] ctrl_pilot_wr_addr_raw = ctrl_rb_idx_int[`SRAM_ADDR_WIDTH + _shift_bits - 1`:`_shift_bits`];
        pass

    # ---- Occasion index counter ----
    if max_occasions > 1:
        # Reset to all-ones so the first increment wraps to 0.
        # The counter increments at each l'=0 (double) or pilot (single) sym_switch,
        # which fires BEFORE the corresponding write. This pre-increment means
        # the first write uses (all-ones + 1) = 0 (correct occasion index).
        # Works for any max_occasions regardless of power-of-2.
        _max_occ_val = max_occasions - 1
        #/ // ========== Occasion Index Counter ==========
        #/ reg [`OCC_SEL_WIDTH`-1:0] ctrl_occ_idx_raw;
        #/ always @(posedge clk or negedge rst_n) begin
        #/     if (!rst_n) begin
        #/         ctrl_occ_idx_raw <= {`OCC_SEL_WIDTH`{1'b1}};
        #/     end else if (!ctrl_ctr_en_int) begin
        #/         ctrl_occ_idx_raw <= {`OCC_SEL_WIDTH`{1'b1}};
        #/     end else if (ctrl_slot_boundary_int) begin
        #/         ctrl_occ_idx_raw <= {`OCC_SEL_WIDTH`{1'b1}};
        if is_double_dmrs == True:
            #/ end else if (ctrl_sym_switch_int && ctrl_is_pilot_int && ~ctrl_l_prime_int) begin
            #/     ctrl_occ_idx_raw <= ctrl_occ_idx_raw + 1'b1;
            pass
        elif is_double_dmrs == False:
            #/ end else if (ctrl_sym_switch_int && ctrl_is_pilot_int) begin
            #/     ctrl_occ_idx_raw <= ctrl_occ_idx_raw + 1'b1;
            pass
        elif is_double_dmrs == "Hybrid":
            #/ end else if (ctrl_sym_switch_int && ctrl_is_pilot_int && (~ctrl_l_prime_int | ~cfg_is_double_dmrs)) begin
            #/     ctrl_occ_idx_raw <= ctrl_occ_idx_raw + 1'b1;
            pass
        #/ end else begin
        #/     ctrl_occ_idx_raw <= ctrl_occ_idx_raw;
        #/ end
        #/ end
        pass

    if has_pre_fi_buf and max_occasions > 1:
        if is_double_dmrs == True:
            #/ assign ctrl_ybuf_occ_tag = (ctrl_sym_switch_int && ctrl_is_pilot_int && ~ctrl_l_prime_int) ? (ctrl_occ_idx_raw + 1'b1) : ctrl_occ_idx_raw;
            pass
        elif is_double_dmrs == False:
            #/ assign ctrl_ybuf_occ_tag = (ctrl_sym_switch_int && ctrl_is_pilot_int) ? (ctrl_occ_idx_raw + 1'b1) : ctrl_occ_idx_raw;
            pass
        elif is_double_dmrs == "Hybrid":
            #/ assign ctrl_ybuf_occ_tag = (ctrl_sym_switch_int && ctrl_is_pilot_int && (~ctrl_l_prime_int | ~cfg_is_double_dmrs)) ? (ctrl_occ_idx_raw + 1'b1) : ctrl_occ_idx_raw;
            pass

    # ---- Auto-derived delay chains via ControlSignalGraph ----
    #/ // ========== LS Control Signal Delays (auto-derived, LS_DRAIN=`LS_DRAIN_CYCLES` clk) ==========
    _needs_dbl_gate = (is_double_dmrs is True or is_double_dmrs == 'Hybrid')
    # Signals already declared as output ports — skip wire declaration for these
    # When double-DMRS gating is active, the delay chain produces ctrl_pilot_wr_en_pre
    # (not the output port), so ctrl_pilot_wr_en_raw stays in _output_ports for the
    # final gated assign; ctrl_pilot_wr_en_pre gets an auto-declared wire.
    _output_ports = {
        'ctrl_pilot_wr_en_raw', 'ctrl_pilot_wr_addr',
    }
    if _needs_rb_boundary and not has_pre_fi_buf:
        _output_ports.add('ctrl_first_rb_d')
        _output_ports.add('ctrl_last_rb_d')
        if RB_PARALLELISM > 1:
            _output_ports.add('ctrl_lane_last_d')
    if max_occasions > 1:
        _output_ports.add('ctrl_occ_idx')
    if freq_interp_method == 'lmmse':
        _output_ports.add('ctrl_freq_interp_en')

    for _sig_name, _sig_info in ls_ctrl_graph.build_delay_table().items():
        _dst = _sig_info['dst']
        _src = _sig_info['src']
        _n_clk = _sig_info['delay']
        _dwt = _sig_info['width']
        if _dst not in _output_ports:
            #/ wire [`_dwt`-1:0] `_dst`;
            pass
        ModuleDelay(DWT=_dwt, IF_RST_N=False, N_CLK=_n_clk,
                    PORTS=_delay_ports(_src, _dst))  # type: ignore

    # Note: no tie-off is needed for ctrl_first_rb_d / ctrl_last_rb_d in pre-FI
    # mode any more. The ports are only declared when the LS control graph
    # actually drives them (see _needs_rb_boundary above), so there is nothing
    # left to tie off.

    # ---- Double-DMRS write gating ----
    # Suppress PILOT_SRAM_BANK write on first symbol of double-DMRS pair.
    # ctrl_pilot_wr_en_pre is the ungated delayed LS enable.
    # ctrl_l_prime_d is l_prime delayed to align with LS pipeline output.
    if _needs_dbl_gate:
        #/ // ========== Double-DMRS SRAM write gating ==========
        if is_double_dmrs is True:
            #/ assign ctrl_pilot_wr_en_raw = ctrl_pilot_wr_en_pre & ctrl_l_prime_d;
            pass
        else:  # 'Hybrid'
            #/ assign ctrl_pilot_wr_en_raw = ctrl_pilot_wr_en_pre & (ctrl_l_prime_d | ~cfg_is_double_dmrs);
            pass

    # ---- Output assignments ----
    #/ // ========== Output assignments ==========
    #/ assign ctrl_ctr_en    = ctrl_ctr_en_int;
    #/ assign ctrl_ls_en     = ctrl_ls_en_int;
    #/ assign ctrl_ti_en         = ctrl_ti_en_int;
    #/ assign cfg_latch_en      = ctrl_slot_boundary_int || !ctrl_ctr_en_int;
    #/ assign ctrl_rb_idx        = ctrl_rb_idx_int;
    #/ assign ctrl_rb_idx_r      = ctrl_rb_idx_r_int;
    #/ assign ctrl_sym_idx       = ctrl_sym_idx_int;
    #/ assign ctrl_sym_idx_next  = ctrl_sym_idx_next_int;
    #/ assign ctrl_is_pilot      = ctrl_is_pilot_int;
    #/ assign ctrl_l_prime       = ctrl_l_prime_int;
    #/ assign ctrl_is_last_dmrs  = ctrl_is_last_dmrs_int;
    #/ assign ctrl_c_init_strb   = ctrl_c_init_strb_int;
    #/ assign ctrl_ti_done       = ctrl_ti_done_int;



    #/ endmodule
