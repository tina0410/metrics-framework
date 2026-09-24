from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import Dict, Literal, List, Any, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from analyze_timing import ControlSignalGraph
from basic_modules import QuType, QuMode, OfMode, ModuleAdd, ModuleDelay, ModuleFxMatch, ModuleSub
# Unified DMRS configuration layer (single source of truth)
from dmrs_config import (
    get_cdm_group_for_port, get_port_type_category,
    get_pilot_re_for_port_unified,
    InterpTopology, PortInterpInfo,
    PILOT_RE_TYPE1, PILOT_RE_TYPE2,
)
import math
from v_core_nn_interp import ModuleCORE_NN_INTERP
from v_core_lin_interp import ModuleCORE_LIN_INTERP
from v_core_lmmse_interp import ModuleCORE_LMMSE_INTERP
from v_coeff_sram import ModuleCOEFF_SRAM


# ===========================================================================
# Module: RB-wise Frequency Interpolation (NN / Linear / LMMSE)
#
# Refactored architecture for Hybrid DMRS Type:
#   OLD: Two separate CORE instances (t1 + t2) → output MUX.
#        Wastes 2× multipliers/adders/registers.
#   NEW: Single shared CORE instance receiving the **union** pilot RE set.
#        - NN/Linear: core receives all 8 union pilots + runtime dmrs_type;
#          the core internally handles topology switching per type.
#        - LMMSE:     core receives all 8 union pilots; the W-coefficient
#          ROM stores two banks (Type1/Type2), with zero-padded columns for
#          the unused pilots of each type.  Runtime dmrs_type selects the
#          ROM bank.  MAC array hardware is fully shared.
# ===========================================================================

@convert
def ModuleFREQ_INTERP(IF_RST_N: bool, RB_parallelism: int, Qu_H_LS: QuType, Qu_H: QuType, antenna_port: int, RE_INDEX_LIST: List[int], method: Literal["nn"] | Literal["linear"] | Literal["lmmse"], dmrs_Type: int | Literal["Hybrid"], LMMSE_P: int = 4, Qu_COEFF: QuType = QuType(12, 10, True), REAL_COEFF: bool = True, tau_rms: float = 3.0, snr_linear: float = 100.0, COEFF_SOURCE: Literal['ROM', 'SRAM'] = 'ROM', channel_model: Optional[str] = 'TDL-C', delay_spread: float = 200e-9, scs: float = 30e3, COEFF_SRAM_SHARED: bool = False, pilot_re_compact: Optional[List[int]] = None, compact_t2_slots: Optional[List[int]] = None, compact_zero_slots: Optional[List[int]] = None, pilot_re_t1: Optional[List[int]] = None, pilot_re_t2: Optional[List[int]] = None, FI_RE_PARALLELISM: int = 12, has_pre_fi_buf: bool = False, fi_core_graph: Optional['ControlSignalGraph'] = None, production_observation_layout:Optional[Dict]=None):
    """
    RB-wise Nearest-neighbor / Linear / LMMSE interpolation in frequency direction.
    
    This module is instantiated **per antenna port**. It receives pilot-position
    H_LS estimates and produces full-RB (12 RE) interpolated channel estimates.
    
    Architecture rationale for per-port (not per-PCDMU) instantiation:
    - All ports in the same CDM group share identical pilot RE positions.
    - Interpolation has NO cross-port data dependency (pure per-port operation).
    - Per-port keeps data flow clean and avoids unnecessary signal mixing.
    
    For Hybrid DMRS Type ports that appear in both Type 1 and Type 2:
    - RE_INDEX_LIST is the sorted union of both types' pilot positions (up to 8 RE).
    - A runtime dmrs_type signal selects the active interpolation topology.
    - Only one type is active at any clock cycle (protocol guarantee).
    - **Single shared core** is instantiated with the union pilot set.
      The core receives dmrs_type and handles internal topology switching:
        * NN/Linear: runtime mux on interpolation assignments per RE.
        * LMMSE: shared MAC array, dual-bank ROM coefficients (zero-padded
          columns for inactive pilots of each type).
    
    Boundary handling (first_RB / last_RB):
    - For the lowest pilot RE, interpolation to RE indices below it requires
      the highest pilot from the *previous* RB group (registered).
    - For the highest pilot RE, interpolation to RE indices above it requires
      the lowest pilot from the *next* RB group.
    - At first_RB: no previous RB exists → extrapolate from current pilots.
    - At last_RB: no next RB exists → extrapolate from current pilots.
    
    :param IF_RST_N: False
        Whether to include reset port.
    :type IF_RST_N: bool
    :param RB_parallelism: 1
        Number of RBs processed in parallel per clock cycle.
    :type RB_parallelism: int
    :param Qu_H_LS: QuType(12, 4, True)
        Quantization type of input LS channel estimates.
    :type Qu_H_LS: QuType
    :param Qu_H: QuType(12, 4, True)
        Quantization type of interpolated channel estimates (output).
    :type Qu_H: QuType
    :param antenna_port: 0
        The antenna port this instance handles.
    :type antenna_port: int
    :param RE_INDEX_LIST: [0, 2, 4, 6, 8, 10]
        Pilot RE positions within one RB (elements in [0,11]).
        Length is 6 for Type 1, 4 for Type 2, or up to 8 for Hybrid union.
    :type RE_INDEX_LIST: List[int]
    :param method: "linear"
        Interpolation method: "nn" for nearest-neighbor, "linear" for linear,
        "lmmse" for LMMSE batch interpolation (requires external matrix interface).
    :type method: Literal["nn"] | Literal["linear"] | Literal["lmmse"]
    :param dmrs_Type: 1
        DMRS type: 1, 2, or "Hybrid".
    :type dmrs_Type: int | Literal["Hybrid"]
    :param LMMSE_P: 4
        Number of RBs in one LMMSE interpolation window (only used when method='lmmse').
    :type LMMSE_P: int
    :param Qu_COEFF: QuType(12, 10, True)
        QuType for LMMSE coefficients. DWT = bit-width, FRAC = fractional bits.
    :type Qu_COEFF: QuType
    :param REAL_COEFF: True
        Whether LMMSE coefficients are real-only (sinc model).
    :type REAL_COEFF: bool
    :param tau_rms: 3.0
        RMS delay spread in subcarrier spacings for LMMSE.
    :type tau_rms: float
    :param snr_linear: 100.0
        Linear SNR for LMMSE regularisation.
    :type snr_linear: float
    """
    
    # Derive raw widths from QuType
    COEFF_DWT = Qu_COEFF.DWT
    COEFF_FRAC = Qu_COEFF.FRAC

    # =========================================================================
    # Step 0: Parameter Validation
    # =========================================================================

    if method not in ("nn", "linear", "lmmse"):
        raise ValueError(f"Invalid interpolation method: {method!r}. Must be 'nn', 'linear', or 'lmmse'.")

    re_index_list_sorted = sorted(RE_INDEX_LIST)
    num_pilots = len(re_index_list_sorted)
    descriptor_metadata = None
    if production_observation_layout is not None:
        from production_observation import (
            frequency_window_observations,
            local_centroid_positions,
            local_lane_centroids,
            local_lane_representatives,
            metadata_from_canonical_dict,
        )

        descriptor_payload = {
            key: value
            for key, value in production_observation_layout.items()
            if key != "case_id"
        }
        descriptor_metadata = metadata_from_canonical_dict(descriptor_payload)
        if descriptor_metadata.antenna_port != antenna_port:
            raise ValueError("frequency interpolation observation port mismatch")
        if descriptor_metadata.dmrs_type != dmrs_Type:
            raise ValueError("frequency interpolation observation type mismatch")
        descriptor_re = sorted(
            {value % 12 for value in descriptor_metadata.required_physical_subcarriers}
        )
        if descriptor_re != re_index_list_sorted:
            raise ValueError("frequency interpolation input geometry differs from descriptor")
        descriptor_pilot_re = list(local_lane_representatives(descriptor_metadata))
        if not descriptor_pilot_re:
            raise ValueError("frequency interpolation descriptor has no unique lanes")
        if any(value not in re_index_list_sorted for value in descriptor_pilot_re):
            raise ValueError("descriptor lane representative is absent from the physical input bus")
        descriptor_centroids = list(local_lane_centroids(descriptor_metadata))
    else:
        descriptor_pilot_re = None
        descriptor_centroids = None

    if dmrs_Type == "Hybrid":
        if num_pilots not in (4, 6, 8):
            raise ValueError(
                f"RE_INDEX_LIST length ({num_pilots}) invalid for Hybrid mode. "
                f"Expected 4 (Type2-only port), 6 (Type1-only port), or 8 (dual-type port)."
            )
    elif dmrs_Type == 1:
        if num_pilots != 6:
            raise ValueError(f"RE_INDEX_LIST length ({num_pilots}) must be 6 for DMRS Type 1.")
    elif dmrs_Type == 2:
        if num_pilots != 4:
            raise ValueError(f"RE_INDEX_LIST length ({num_pilots}) must be 4 for DMRS Type 2.")
    elif dmrs_Type == 3:
        if num_pilots != 2:
            raise ValueError(f"RE_INDEX_LIST length ({num_pilots}) must be 2 for DMRS Type 3.")
    else:
        raise ValueError(f"Invalid DMRS Type: {dmrs_Type}")
    
    # Validate all elements are in [0, 11]
    for re_val in re_index_list_sorted:
        if re_val < 0 or re_val > 11:
            raise ValueError(f"RE_INDEX_LIST element {re_val} out of range [0, 11].")

    # Determine if this is a dual-type port (needs runtime dmrs_type switching)
    is_dual_type = (dmrs_Type == "Hybrid" and num_pilots == 8)
    _use_compact = is_dual_type and pilot_re_compact is not None

    # For dual-type ports, pre-compute the two sub-lists (used for comments/validation)
    if is_dual_type:
        port_type_cat = get_port_type_category(antenna_port)
        if port_type_cat != 0:
            raise ValueError(
                f"RE_INDEX_LIST has 8 elements but port {antenna_port} is not a dual-type port."
            )
        grp1 = get_cdm_group_for_port(antenna_port, 1)
        grp2 = get_cdm_group_for_port(antenna_port, 2)
        re_list_type1 = PILOT_RE_TYPE1[grp1]
        re_list_type2 = PILOT_RE_TYPE2[grp2]

    # Compact pilot list for core instantiation
    if descriptor_pilot_re is not None:
        compact_re_sorted = sorted(descriptor_pilot_re)
    elif _use_compact:
        compact_re_sorted = sorted(pilot_re_compact)
    else:
        compact_re_sorted = re_index_list_sorted

    # =========================================================================
    # Step 1: Module Port Declaration
    # =========================================================================
    
    #/ `timescale 1ns / 1ps
    #/ module FREQ_INTERP(

    #/ input clk,
    if IF_RST_N:
        #/ input rst_n,
        pass
    
    # Input: H_LS pilot estimates — union pilot set for Hybrid dual-type
    if not has_pre_fi_buf:
        for i in range(RB_parallelism):
            for j in re_index_list_sorted:
                name = f"h_ls_port{antenna_port}_rb{i}_re{j}_complex"
                #/ input [`2*Qu_H_LS.DWT`-1:0] `name`,
                pass
    
    # Output: full-RB interpolated channel, 12 RE per RB.
    # Streaming drain: LMMSE core outputs RB_parallelism RBs per clock (same as NN/linear).
    # NOTE: the outputs are declared LAST in the port list (see below) because they
    # are the only group that is present for every configuration, so they can carry
    # the comma-free final entry. Previously `last_RB` played that role, which forced
    # first_RB/last_RB to be declared even for LMMSE, where nothing consumes them —
    # leaving two dangling inputs per FI instance.
    out_rbs = RB_parallelism

    # Runtime DMRS type selection (only for dual-type ports with 8 RE)
    if is_dual_type:
        #/ input dmrs_type,
        pass
    
    # SRAM-related dimensions (computed early for port declarations in shared mode)
    # Time-multiplexed: CORE processes FI_RE_PARALLELISM*LMMSE_P outputs per group
    _srN_PILOTS_PER_RB = len(compact_re_sorted) if method == 'lmmse' else 0
    _srOUTPUT_GROUPS = (12 // FI_RE_PARALLELISM) if method == 'lmmse' else 1
    _srFILL_BEATS_ORIG = max(LMMSE_P // max(RB_parallelism, 1), 1) if method == 'lmmse' else 0
    _srFILL_BEATS = _srFILL_BEATS_ORIG * _srOUTPUT_GROUPS
    _srN_PILOTS_PER_BEAT = _srN_PILOTS_PER_RB * RB_parallelism
    _srN_OUTPUT = FI_RE_PARALLELISM * LMMSE_P if method == 'lmmse' else 0
    _srN_PILOTS = _srN_PILOTS_PER_RB * LMMSE_P if method == 'lmmse' else 0
    _srCOEFF_PER_BEAT = _srN_OUTPUT * _srN_PILOTS_PER_BEAT
    _srCOEFF_DWT = Qu_COEFF.DWT
    _srCOEFF_BEAT_DWT = _srCOEFF_PER_BEAT * _srCOEFF_DWT if REAL_COEFF else _srCOEFF_PER_BEAT * 2 * _srCOEFF_DWT
    _srBEAT_IDX_W = max(math.ceil(math.log2(_srFILL_BEATS)), 1) if _srFILL_BEATS > 0 else 1

    # Boundary control signals. Only NN and Linear cores consume them (they
    # extrapolate at the slot edges); the LMMSE core handles edges through its
    # coefficient set, so declaring them there would just dangle.
    if method in ('nn', 'linear'):
        #/ input first_RB,
        #/ input last_RB,
        if method in ('nn', 'linear') and RB_parallelism > 1:
            #/ input [`RB_parallelism`-1:0] lane_last,
            pass
        pass
    if method == 'lmmse' or has_pre_fi_buf:
        #/ input  enable,
        #/ output drain_valid,
        if has_pre_fi_buf:
            if method == 'lmmse':
                _lbDATA_W = _srN_PILOTS_PER_BEAT * 2 * Qu_H_LS.DWT
                _lbBEAT_W = max(math.ceil(math.log2(_srFILL_BEATS_ORIG)), 1)
            else:
                _lbN_PILOTS = len(compact_re_sorted)
                _lbDATA_W = _lbN_PILOTS * RB_parallelism * 2 * Qu_H_LS.DWT
                _lbBEAT_W = 1
            #/ input [`_lbDATA_W`-1:0] ls_buf_rd_data,
            #/ output ls_buf_rd_en,
            #/ output [`_lbBEAT_W`-1:0] ls_buf_rd_beat,
            pass
        if COEFF_SOURCE == 'SRAM' and not COEFF_SRAM_SHARED:
            N_PILOTS_PER_RB_ = len(re_index_list_sorted)
            N_OUTPUT_ = FI_RE_PARALLELISM * LMMSE_P
            N_PILOTS_ = N_PILOTS_PER_RB_ * LMMSE_P
            TOTAL_ENTRIES_ = N_OUTPUT_ * N_PILOTS_
            ADDR_W_ = max(math.ceil(math.log2(TOTAL_ENTRIES_)), 1)
            #/ // Coefficient SRAM write interface
            #/ input                   coeff_wr_en,
            #/ input [`ADDR_W_`-1:0]   coeff_wr_addr,
            #/ input [`COEFF_DWT`-1:0] coeff_wr_data,
            pass
        elif COEFF_SOURCE == 'SRAM' and COEFF_SRAM_SHARED:
            _srd_idx_hi = _srBEAT_IDX_W - 1
            _srd_data_hi = _srCOEFF_BEAT_DWT - 1
            #/ // Shared Coefficient SRAM read interface -- SRAM instantiated externally
            #/ output [`_srd_idx_hi`:0]     coeff_rd_idx,
            #/ input  [`_srd_data_hi`:0] coeff_rd_data,
            pass
        pass

    # Interpolated outputs -- always present, so the last one terminates the
    # port list without a trailing comma.
    _n_out = 12 * out_rbs
    for i in range(_n_out):
        name = f"h_{method}_port{antenna_port}_rb{i // 12}_re{i % 12}_complex"
        if i == _n_out - 1:
            #/ output [`2*Qu_H.DWT`-1:0] `name`
            pass
        else:
            #/ output [`2*Qu_H.DWT`-1:0] `name`,
            pass
    #/ );
    
    # =========================================================================
    # Step 2: Compact pilot MUX (8→6 for Hybrid dual-type)
    # =========================================================================
    if _use_compact and not has_pre_fi_buf:
        CPLX_DWT = 2 * Qu_H_LS.DWT
        _t1_sorted = sorted(re_list_type1)
        _t2_sorted = sorted(re_list_type2)
        #/ // ========== 8-to-6 Compact Pilot MUX ==========
        for rb in range(RB_parallelism):
            for slot_idx, compact_re_val in enumerate(compact_re_sorted):
                compact_wire = f"compact_rb{rb}_re{compact_re_val}"
                t1_re = _t1_sorted[slot_idx]
                t1_src = f"h_ls_port{antenna_port}_rb{rb}_re{t1_re}_complex"
                if slot_idx in compact_zero_slots:
                    #/ wire [`CPLX_DWT`-1:0] `compact_wire` = dmrs_type ? `CPLX_DWT`'d0 : `t1_src`;
                    pass
                elif slot_idx in compact_t2_slots:
                    t2_idx = compact_t2_slots.index(slot_idx)
                    t2_re = _t2_sorted[t2_idx]
                    t2_src = f"h_ls_port{antenna_port}_rb{rb}_re{t2_re}_complex"
                    if t1_re == t2_re:
                        #/ wire [`CPLX_DWT`-1:0] `compact_wire` = `t1_src`;
                        pass
                    else:
                        #/ wire [`CPLX_DWT`-1:0] `compact_wire` = dmrs_type ? `t2_src` : `t1_src`;
                        pass
        #/
    
    # =========================================================================
    # Step 3: Cross-RB Boundary Pipeline Register
    # =========================================================================
    # CORE_NN_INTERP and CORE_LIN_INTERP manage cross-RB registers internally.
    
    # =========================================================================
    # Step 4: Per-RB Interpolation Logic — SINGLE SHARED CORE
    # =========================================================================
    # For all methods (NN / Linear / LMMSE), only ONE core instance is created.
    # Dual-type Hybrid ports pass dmrs_type to the core for internal switching.
    #
    # Resource sharing strategy:
    #   - NN:     Core receives union pilot set. Internally selects between
    #             Type1 and Type2 NN assignment maps via dmrs_type mux.
    #   - Linear: Core receives union pilot set. Internally generates both
    #             gap-2 (Type1) and gap-5 (Type2) datapaths where needed,
    #             with dmrs_type mux on outputs.
    #   - LMMSE:  Core receives union pilot set (8 inputs). Shared MAC array
    #             with 8 multipliers per output RE. Two ROM banks store
    #             Type1 coefficients (zero-padded for non-Type1 pilots) and
    #             Type2 coefficients (zero-padded for non-Type2 pilots).
    #             Runtime dmrs_type selects coefficients. Multiplier hardware
    #             is 100% shared — zero coefficients produce zero products.
    
    #/ // ========== Per-RB Interpolation ==========

    # Need FxMatch when Qu_H_LS ≠ Qu_H (hybrid configs)
    need_fxmatch = (Qu_H_LS.DWT != Qu_H.DWT or Qu_H_LS.FRAC != Qu_H.FRAC)

    # Pre-FI mode: unpack ls_buf_rd_data into pilot wires, drive rd_en/rd_beat
    if has_pre_fi_buf and method in ('nn', 'linear'):
        _CPLX_DWT = 2 * Qu_H_LS.DWT
        if method == 'nn':
            from v_core_nn_interp import nn_freq_pipeline_depth
            _fi_latency = nn_freq_pipeline_depth()
        else:
            from v_core_lin_interp import lin_freq_pipeline_depth
            _fi_latency = lin_freq_pipeline_depth(Qu_H_LS.DWT)
        _drain_delay = 2 + _fi_latency  # 1 prefetch + 1 SRAM read + FI pipeline
        # LS_BUF uses the Type-1 compact frame for Hybrid dual-type ports.
        # Type-2's physical boundary pilots are not necessarily stored in the
        # first/last compact slots (for example, port 6 maps its lowest Type-2
        # pilot to slot 1).  Select the boundary slot for the active runtime
        # topology rather than assuming the compact-frame endpoints.
        _lowest_idx_t1 = 0
        _highest_idx_t1 = len(compact_re_sorted) - 1
        if _use_compact:
            assert compact_t2_slots is not None
            _lowest_idx_t2 = compact_t2_slots[0]
            _highest_idx_t2 = compact_t2_slots[-1]
        else:
            _lowest_idx_t2 = _lowest_idx_t1
            _highest_idx_t2 = _highest_idx_t1
        _lowest_bit_offset_t1 = _lowest_idx_t1 * _CPLX_DWT
        _lowest_bit_offset_t2 = _lowest_idx_t2 * _CPLX_DWT
        #/ // ========== Pre-FI: LS_BUF read control (2-beat prefetch) ==========
        #/ reg fi_rd_phase;
        #/ reg [`_CPLX_DWT`-1:0] next_l_prefetch;
        #/ always @(posedge clk) begin
        #/     if (enable) begin
        #/         fi_rd_phase <= 1'b1;
        #/     end else begin
        #/         fi_rd_phase <= 1'b0;
        #/     end
        #/ end
        #/ assign ls_buf_rd_en = enable | fi_rd_phase;
        #/ assign ls_buf_rd_beat = enable ? `_lbBEAT_W`'d1 : `_lbBEAT_W`'d0;
        #/
        #/ // Capture next RB's lowest pilot from prefetch read (arrives 1 clk after enable)
        #/ always @(posedge clk) begin
        #/     if (fi_rd_phase) begin
        if _use_compact:
            #/         next_l_prefetch <= dmrs_type ? ls_buf_rd_data[`_lowest_bit_offset_t2 + _CPLX_DWT - 1`:`_lowest_bit_offset_t2`] : ls_buf_rd_data[`_lowest_bit_offset_t1 + _CPLX_DWT - 1`:`_lowest_bit_offset_t1`];
            pass
        else:
            #/         next_l_prefetch <= ls_buf_rd_data[`_lowest_bit_offset_t1 + _CPLX_DWT - 1`:`_lowest_bit_offset_t1`];
            pass
        #/     end
        #/ end
        #/
        #/ // Capture prev RB's highest pilot via double-buffer (valid 1 clk after fi_rd_phase)
        # ls_buf_rd_data packs every RB in the beat.  The value carried into
        # the next window must come from the final packed RB, not RB0; otherwise
        # the first RE of each following beat interpolates across the wrong
        # physical boundary when RB_PARALLELISM > 1.
        _highest_bit_offset_t1 = (
            (RB_parallelism - 1) * len(compact_re_sorted) + _highest_idx_t1
        ) * _CPLX_DWT
        _highest_bit_offset_t2 = (
            (RB_parallelism - 1) * len(compact_re_sorted) + _highest_idx_t2
        ) * _CPLX_DWT
        #/ reg fi_data_valid;
        #/ always @(posedge clk) fi_data_valid <= fi_rd_phase;
        #/ reg [`_CPLX_DWT`-1:0] prev_h_capture;
        #/ reg [`_CPLX_DWT`-1:0] prev_h_hold;
        #/ always @(posedge clk) begin
        #/     if (fi_data_valid) begin
        #/         prev_h_hold <= prev_h_capture;
        if _use_compact:
            #/         prev_h_capture <= dmrs_type ? ls_buf_rd_data[`_highest_bit_offset_t2 + _CPLX_DWT - 1`:`_highest_bit_offset_t2`] : ls_buf_rd_data[`_highest_bit_offset_t1 + _CPLX_DWT - 1`:`_highest_bit_offset_t1`];
            pass
        else:
            #/         prev_h_capture <= ls_buf_rd_data[`_highest_bit_offset_t1 + _CPLX_DWT - 1`:`_highest_bit_offset_t1`];
            pass
        #/     end
        #/ end
        #/
        if method == 'nn':
            _prev_h_wire = 'prev_h_hold'
        else:
            _prev_h_wire = 'prev_h_capture'
        #/ // ========== Pre-FI: drain_valid delay chain ==========
        if _drain_delay == 1:
            #/ reg drain_valid_r;
            #/ always @(posedge clk) drain_valid_r <= enable;
            #/ assign drain_valid = drain_valid_r;
            pass
        else:
            #/ reg [`_drain_delay`-1:0] drain_valid_sr;
            #/ always @(posedge clk) drain_valid_sr <= {drain_valid_sr[`_drain_delay - 2`:0], enable};
            #/ assign drain_valid = drain_valid_sr[`_drain_delay - 1`];
            pass
        #/
        #/ // ========== Pre-FI: Unpack ls_buf_rd_data into pilot wires ==========
        for rb in range(RB_parallelism):
            for idx, re_k in enumerate(compact_re_sorted):
                bit_offset = (rb * len(compact_re_sorted) + idx) * _CPLX_DWT
                wire_name = f"lsbuf_pilot_rb{rb}_re{re_k}"
                #/ wire [`_CPLX_DWT`-1:0] `wire_name` = ls_buf_rd_data[`bit_offset + _CPLX_DWT - 1`:`bit_offset`];
                pass
        #/

    if method == "nn":
        # ---------------------------------------------------------------
        # NN mode: single CORE_NN_INTERP instance
        # For dual-type: core receives union pilots + dmrs_type for
        # internal topology switching.
        # ---------------------------------------------------------------
        ports_nn = {
            'clk': 'clk',
            'first_RB': 'first_RB',
            'last_RB': 'last_RB',
        }
        if IF_RST_N:
            ports_nn['rst_n'] = 'rst_n'
        if RB_parallelism > 1:
            ports_nn['lane_last'] = 'lane_last'
        if is_dual_type:
            ports_nn['dmrs_type'] = 'dmrs_type'
        
        for rb in range(RB_parallelism):
            for re_k in compact_re_sorted:
                if has_pre_fi_buf:
                    in_name = f"lsbuf_pilot_rb{rb}_re{re_k}"
                elif _use_compact:
                    in_name = f"compact_rb{rb}_re{re_k}"
                else:
                    in_name = f"h_ls_port{antenna_port}_rb{rb}_re{re_k}_complex"
                ports_nn[f"pilot_rb{rb}_re{re_k}"] = in_name
            for re_k in range(12):
                if need_fxmatch:
                    core_out = f"h_nn_core_port{antenna_port}_rb{rb}_re{re_k}"
                    #/ wire [`2*Qu_H_LS.DWT`-1:0] `core_out`;
                    ports_nn[f"h_nn_rb{rb}_re{re_k}"] = core_out
                else:
                    out_name = f"h_{method}_port{antenna_port}_rb{rb}_re{re_k}_complex"
                    ports_nn[f"h_nn_rb{rb}_re{re_k}"] = out_name

        if has_pre_fi_buf:
            ports_nn['next_rb_lowest'] = 'next_l_prefetch'
            ports_nn['prev_rb_highest'] = _prev_h_wire

        ModuleCORE_NN_INTERP(IF_RST_N=IF_RST_N, RB_PARALLELISM=RB_parallelism, Qu_H=Qu_H_LS, pilot_re=compact_re_sorted, dmrs_Type=dmrs_Type, pilot_re_t1=pilot_re_t1, pilot_re_t2=pilot_re_t2, compact_t2_slots=compact_t2_slots, sample_positions=descriptor_centroids, has_next_rb_lowest=has_pre_fi_buf, has_prev_rb_highest=has_pre_fi_buf, PORTS=ports_nn)

        # final FxMatch to output phase
        if need_fxmatch:
            #/ // ========== FxMatch: Qu_H_LS → Qu_H per component (TRN::TCPL / SAT::TCPL) ==========
            for rb in range(RB_parallelism):
                for re_k in range(12):
                    core_out = f"h_nn_core_port{antenna_port}_rb{rb}_re{re_k}"
                    final_out = f"h_{method}_port{antenna_port}_rb{rb}_re{re_k}_complex"
                    # Split packed complex into real/imag
                    core_r = f"{core_out}_r"
                    core_i = f"{core_out}_i"
                    out_r = f"{core_out}_fxm_r"
                    out_i = f"{core_out}_fxm_i"
                    #/ wire [`Qu_H_LS.DWT`-1:0] `core_r` = `core_out`[`Qu_H_LS.DWT`-1:0];
                    #/ wire [`Qu_H_LS.DWT`-1:0] `core_i` = `core_out`[`2*Qu_H_LS.DWT`-1:`Qu_H_LS.DWT`];
                    #/ wire [`Qu_H.DWT`-1:0] `out_r`;
                    #/ wire [`Qu_H.DWT`-1:0] `out_i`;
                    ModuleFxMatch(QU_IN=Qu_H_LS, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': core_r, 'o_data': out_r})
                    ModuleFxMatch(QU_IN=Qu_H_LS, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': core_i, 'o_data': out_i})
                    #/ assign `final_out` = {`out_i`, `out_r`};
    
    elif method == "linear":
        # ---------------------------------------------------------------
        # Linear mode: single CORE_LIN_INTERP instance
        # For dual-type: core receives union pilots + dmrs_type for
        # internal topology switching between gap-2 and gap-5 paths.
        # ---------------------------------------------------------------
        ports_lin = {
            'clk': 'clk',
            'first_RB': 'first_RB',
            'last_RB': 'last_RB',
        }
        if IF_RST_N:
            ports_lin['rst_n'] = 'rst_n'
        if is_dual_type:
            ports_lin['dmrs_type'] = 'dmrs_type'
        if RB_parallelism > 1:
            ports_lin['lane_last'] = 'lane_last'
        
        for rb in range(RB_parallelism):
            for re_k in compact_re_sorted:
                if has_pre_fi_buf:
                    in_name = f"lsbuf_pilot_rb{rb}_re{re_k}"
                elif _use_compact:
                    in_name = f"compact_rb{rb}_re{re_k}"
                else:
                    in_name = f"h_ls_port{antenna_port}_rb{rb}_re{re_k}_complex"
                ports_lin[f"pilot_rb{rb}_re{re_k}"] = in_name
            for re_k in range(12):
                if need_fxmatch:
                    core_out = f"h_lin_core_port{antenna_port}_rb{rb}_re{re_k}"
                    #/ wire [`2*Qu_H_LS.DWT`-1:0] `core_out`;
                    ports_lin[f"h_lin_rb{rb}_re{re_k}"] = core_out
                else:
                    out_name = f"h_{method}_port{antenna_port}_rb{rb}_re{re_k}_complex"
                    ports_lin[f"h_lin_rb{rb}_re{re_k}"] = out_name

        if has_pre_fi_buf:
            ports_lin['next_rb_lowest'] = 'next_l_prefetch'
            ports_lin['prev_rb_highest'] = _prev_h_wire

        ModuleCORE_LIN_INTERP(IF_RST_N=IF_RST_N, RB_PARALLELISM=RB_parallelism, Qu_H=Qu_H_LS, pilot_re=compact_re_sorted, dmrs_Type=dmrs_Type, pilot_re_t1=pilot_re_t1, pilot_re_t2=pilot_re_t2, compact_t2_slots=compact_t2_slots, sample_positions=descriptor_centroids, has_next_rb_lowest=has_pre_fi_buf, has_prev_rb_highest=has_pre_fi_buf, PORTS=ports_lin)

        if need_fxmatch:
            #/ // ========== FxMatch: Qu_H_LS → Qu_H per component (TRN::TCPL / SAT::TCPL) ==========
            for rb in range(RB_parallelism):
                for re_k in range(12):
                    core_out = f"h_lin_core_port{antenna_port}_rb{rb}_re{re_k}"
                    final_out = f"h_{method}_port{antenna_port}_rb{rb}_re{re_k}_complex"
                    # Split packed complex into real/imag
                    core_r = f"{core_out}_r"
                    core_i = f"{core_out}_i"
                    out_r = f"{core_out}_fxm_r"
                    out_i = f"{core_out}_fxm_i"
                    #/ wire [`Qu_H_LS.DWT`-1:0] `core_r` = `core_out`[`Qu_H_LS.DWT`-1:0];
                    #/ wire [`Qu_H_LS.DWT`-1:0] `core_i` = `core_out`[`2*Qu_H_LS.DWT`-1:`Qu_H_LS.DWT`];
                    #/ wire [`Qu_H.DWT`-1:0] `out_r`;
                    #/ wire [`Qu_H.DWT`-1:0] `out_i`;
                    ModuleFxMatch(QU_IN=Qu_H_LS, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': core_r, 'o_data': out_r})
                    ModuleFxMatch(QU_IN=Qu_H_LS, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': core_i, 'o_data': out_i})
                    #/ assign `final_out` = {`out_i`, `out_r`};

    elif method == "lmmse":
        # ---------------------------------------------------------------
        # LMMSE mode: single CORE_LMMSE_INTERP instance
        # For dual-type: core receives all 8 union pilots. Internally
        # uses dual-bank ROM with zero-padded coefficients to share the
        # MAC array. Runtime dmrs_type selects the active ROM bank.
        # In SRAM mode: COEFF_SRAM provides coefficients via a wide bus.
        # ---------------------------------------------------------------

        # Compute SRAM-related dimensions (needed for both modes for port calc)
        # Time-multiplexed: CORE processes FI_RE_PARALLELISM*LMMSE_P outputs per group
        _N_PILOTS_PER_RB = len(compact_re_sorted)
        _OUTPUT_GROUPS = 12 // FI_RE_PARALLELISM
        _FILL_BEATS_ORIG = max(LMMSE_P // max(RB_parallelism, 1), 1)
        _FILL_BEATS = _FILL_BEATS_ORIG * _OUTPUT_GROUPS
        _N_PILOTS_PER_BEAT = _N_PILOTS_PER_RB * RB_parallelism
        _N_OUTPUT = FI_RE_PARALLELISM * LMMSE_P
        _N_PILOTS = _N_PILOTS_PER_RB * LMMSE_P
        _COEFF_PER_BEAT = _N_OUTPUT * _N_PILOTS_PER_BEAT
        _COEFF_BEAT_DWT = _COEFF_PER_BEAT * COEFF_DWT if REAL_COEFF else _COEFF_PER_BEAT * 2 * COEFF_DWT
        _BEAT_IDX_W = max(math.ceil(math.log2(_FILL_BEATS)), 1)

        if COEFF_SOURCE == 'SRAM' and not COEFF_SRAM_SHARED:
            # Instantiate COEFF_SRAM and declare internal wires
            #/ // ===== Coefficient SRAM =====
            #/ wire [`_BEAT_IDX_W`-1:0]     coeff_rd_idx_w;
            #/ wire [`_COEFF_BEAT_DWT`-1:0] coeff_rd_data_w;

            sram_ports = {
                'clk': 'clk',
                'rst_n': 'rst_n' if IF_RST_N else 'clk',  # rst_n always present on COEFF_SRAM
                'wr_en': 'coeff_wr_en',
                'wr_addr': 'coeff_wr_addr',
                'wr_data': 'coeff_wr_data',
                'rd_beat_idx': 'coeff_rd_idx_w',
                'rd_data': 'coeff_rd_data_w',
            }
            if not IF_RST_N:
                # COEFF_SRAM always has rst_n; tie high if wrapper doesn't expose it
                #/ wire coeff_sram_rst_n = 1'b1;
                sram_ports['rst_n'] = 'coeff_sram_rst_n'

            ModuleCOEFF_SRAM(N_OUTPUT=_N_OUTPUT, N_PILOTS=_N_PILOTS, Qu_COEFF=Qu_COEFF, COEFF_STORAGE='SRAM', is_hybrid=False, rom_data_bank0=None, rom_data_bank1=None, BEAT_MODE=True, N_PILOTS_PER_BEAT=_N_PILOTS_PER_BEAT, FILL_BEATS=_FILL_BEATS, PORTS=sram_ports)
        elif COEFF_SOURCE == 'SRAM' and COEFF_SRAM_SHARED:
            # Shared COEFF_SRAM mode: coeff_rd_idx/coeff_rd_data are external ports
            # supplied by the parent (v_top), which instantiates one COEFF_SRAM
            # per CDM group shared across all ports in that group.
            #/ // Shared COEFF_SRAM mode: external coeff_rd_idx / coeff_rd_data ports
            pass

        ports_lmmse = {
            'clk': 'clk',
            'enable': 'enable',
        }
        if IF_RST_N:
            ports_lmmse['rst_n'] = 'rst_n'
        if is_dual_type and COEFF_SOURCE == 'ROM':
            ports_lmmse['dmrs_type'] = 'dmrs_type'

        if has_pre_fi_buf:
            ports_lmmse['ls_buf_rd_data'] = 'ls_buf_rd_data'
            ports_lmmse['ls_buf_rd_en'] = 'ls_buf_rd_en'
            ports_lmmse['ls_buf_rd_beat'] = 'ls_buf_rd_beat'
        else:
            for rb in range(RB_parallelism):
                for re_k in compact_re_sorted:
                    if _use_compact:
                        in_name = f"compact_rb{rb}_re{re_k}"
                    else:
                        in_name = f"h_ls_port{antenna_port}_rb{rb}_re{re_k}_complex"
                    ports_lmmse[f"h_ls_rb{rb}_re{re_k}"] = in_name

        for rb in range(RB_parallelism):
            for re_k in range(12):
                out_name = f"h_{method}_port{antenna_port}_rb{rb}_re{re_k}_complex"
                ports_lmmse[f"h_out_rb{rb}_re{re_k}"] = out_name

        ports_lmmse['drain_valid'] = 'drain_valid'

        if COEFF_SOURCE == 'SRAM':
            if COEFF_SRAM_SHARED:
                ports_lmmse['coeff_rd_idx'] = 'coeff_rd_idx'
                ports_lmmse['coeff_rd_data'] = 'coeff_rd_data'
            else:
                ports_lmmse['coeff_rd_idx'] = 'coeff_rd_idx_w'
                ports_lmmse['coeff_rd_data'] = 'coeff_rd_data_w'

        descriptor_W = None
        if descriptor_metadata is not None and COEFF_SOURCE == 'ROM':
            from lmmse_matrix_gen import (
                compute_freq_covariance,
                compute_freq_lmmse_W_from_observations,
            )

            window_start = (
                min(descriptor_metadata.required_physical_subcarriers) // 12
            ) * 12
            observations = frequency_window_observations(
                descriptor_metadata,
                start_subcarrier=window_start,
                num_subcarriers=12 * LMMSE_P,
            )
            if len(observations) != len(compact_re_sorted) * LMMSE_P:
                raise ValueError(
                    "descriptor LMMSE window does not match unique-lane geometry"
                )
            descriptor_W = compute_freq_lmmse_W_from_observations(
                observations,
                list(range(12 * LMMSE_P)),
                12 * LMMSE_P,
                tau_rms=tau_rms,
                snr_linear=snr_linear,
                R_freq=(
                    None
                    if channel_model is None
                    else compute_freq_covariance(
                        12 * LMMSE_P,
                        model=channel_model,
                        scs=scs,
                        delay_spread=delay_spread,
                    )
                ),
                grid_start_subcarrier=window_start,
                inter_stage_gain_policy="none",
            )

        ModuleCORE_LMMSE_INTERP(IF_RST_N=IF_RST_N, LMMSE_P=LMMSE_P, RB_PARALLELISM=RB_parallelism, Qu_H_LS=Qu_H_LS, Qu_H=Qu_H, pilot_re=compact_re_sorted, output_re=list(range(12)), dmrs_Type=dmrs_Type, Qu_COEFF=Qu_COEFF, REAL_COEFF=REAL_COEFF, W_matrix_override=descriptor_W, tau_rms=tau_rms, snr_linear=snr_linear, COEFF_SOURCE=COEFF_SOURCE, channel_model=channel_model, delay_spread=delay_spread, scs=scs, pilot_re_t1=pilot_re_t1, pilot_re_t2=pilot_re_t2, compact_t2_slots=compact_t2_slots, compact_zero_slots=compact_zero_slots, FI_RE_PARALLELISM=FI_RE_PARALLELISM, has_pre_fi_buf=has_pre_fi_buf, fi_core_graph=fi_core_graph, PORTS=ports_lmmse)

    #/ endmodule
