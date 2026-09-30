# CORE_LMMSE_INTERP — Streaming accumulate frequency-domain LMMSE interpolation
# Computes H_out = W × H_pilot for one LMMSE_P-RB window
# Architecture: Pilot-fold MAC with per-RB-beat coefficient case-ROM
# After accumulation, drains one-RB-per-clock to match input rate
# Dependencies: Mul, AdderTree, FxMatch, Delay, Add
import math
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from typing import List, Literal, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from analyze_timing import ControlSignalGraph
from basic_modules import (
    QuType, QuMode, OfMode,
    ModuleComplexMul, ModuleAdd, ModuleDelay, ModuleFxMatch, ModuleMul,
)
from basic_modules.AdderTree import ModuleAdderTree
from basic_modules.Sub import ModuleSub
from delay_budget import DelayBudget, COST_MUL_8B, COST_ADDER_8B, cost_mul, cost_adder, DEFAULT_BUDGET
from lmmse_matrix_gen import (
    compute_freq_lmmse_W,
    compute_freq_lmmse_W_from_observations,
    compute_freq_covariance,
    quantise_complex,
    quantise_real,
)
from dmrs_config import compact_pad_lmmse_matrix


FI_LMMSE_MULTIPLIER_LATENCY = 1


def fi_lmmse_multiplier_latency() -> int:
    """Return the intrinsic latency of the concrete FI multiplier datapath."""

    return FI_LMMSE_MULTIPLIER_LATENCY


def _pipeline_depth_lmmse_freq(
    N_PILOTS_PER_RB: int,
    LMMSE_P: int = 1,
    RB_PARALLELISM: int = 1,
    H_DWT: int = 12,
    COEFF_DWT: int = 12,
    REAL_COEFF: bool = False,
    FI_RE_PARALLELISM: int = 12,
    has_pre_fi_buf: bool = False,
) -> int:
    """Total pipeline depth from first input to first valid output.

    Delegates to ``build_fi_core_graph()`` in analyze_timing for the
    canonical pipeline model (single source of truth).
    """
    from analyze_timing import build_fi_core_graph
    _, info = build_fi_core_graph(
        N_PILOTS_PER_RB=N_PILOTS_PER_RB,
        LMMSE_P=LMMSE_P,
        RB_PARALLELISM=RB_PARALLELISM,
        H_DWT=H_DWT,
        COEFF_DWT=COEFF_DWT,
        REAL_COEFF=REAL_COEFF,
        FI_RE_PARALLELISM=FI_RE_PARALLELISM,
        has_pre_fi_buf=has_pre_fi_buf,
    )
    return info['total_depth']


@convert
def ModuleCORE_LMMSE_INTERP(IF_RST_N: bool, LMMSE_P: int, RB_PARALLELISM: int, Qu_H_LS: QuType, Qu_H: QuType, pilot_re: List[int], output_re: List[int], dmrs_Type: int | Literal["Hybrid"], Qu_COEFF: QuType, REAL_COEFF: bool, W_matrix_override: Optional[list], tau_rms: float, snr_linear: float, COEFF_SOURCE: Literal['ROM', 'SRAM'] = 'ROM', channel_model: Optional[str] = 'TDL-C', delay_spread: float = 200e-9, scs: float = 30e3, pilot_re_t1: Optional[List[int]] = None, pilot_re_t2: Optional[List[int]] = None, compact_t2_slots: Optional[List[int]] = None, compact_zero_slots: Optional[List[int]] = None, FI_RE_PARALLELISM: int = 12, has_pre_fi_buf: bool = False, fi_core_graph: Optional['ControlSignalGraph'] = None):
    """Frequency-domain LMMSE interpolation core (streaming accumulate).

    Processes N_PILOTS_PER_RB * RB_PARALLELISM pilots per clock beat,
    accumulates over FILL_BEATS = LMMSE_P / RB_PARALLELISM beats.
    After accumulation, drains one RB-group per clock to match input rate.

    Pipeline: coeff case-ROM -> MUL -> AdderTree -> accumulator -> FxMatch -> drain mux.

    Two coefficient modes (selected by COEFF_SOURCE):
      'ROM':  Coefficients hardwired at elaborate-time (default, existing behaviour).
      'SRAM': Coefficients supplied via an external port (coeff_rd_data) indexed
              by coeff_rd_idx. The wrapper (FREQ_INTERP) instantiates COEFF_SRAM
              and connects it to these ports.

    :param IF_RST_N: True
    :param LMMSE_P: 4
    :param RB_PARALLELISM: 1
    :param Qu_H_LS: QuType(12, 4, True)
    :param Qu_H: QuType(12, 4, True)
    :param pilot_re: [0, 2, 4, 6, 8, 10]
    :param output_re: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    :param dmrs_Type: 1
    :param Qu_COEFF: QuType(12, 10, True)
        QuType for LMMSE coefficients. COEFF_DWT = Qu_COEFF.DWT, COEFF_FRAC = Qu_COEFF.FRAC.
    :param REAL_COEFF: True
    :param W_matrix_override: None
    :param tau_rms: 3.0
    :param snr_linear: 100.0
    :param COEFF_SOURCE: 'ROM'
    :param channel_model: 'TDL-C'
        TDL channel model for covariance (overrides tau_rms sinc model). Set None to use sinc.
    :param delay_spread: 200e-9
        RMS delay spread in seconds (used with channel_model).
    :param scs: 30e3
        Subcarrier spacing in Hz (used with channel_model).
        'ROM' for hardwired coefficients, 'SRAM' for external port input.
    """

    # Derive raw widths from QuType
    COEFF_DWT = Qu_COEFF.DWT
    COEFF_FRAC = Qu_COEFF.FRAC

    MUL_LATENCY = fi_lmmse_multiplier_latency()

    # =========================================================================
    # Step 0: Compute W matrix at elaborate-time (ROM mode only)
    # =========================================================================
    N_PILOTS_PER_RB = len(pilot_re)
    N_OUTPUT_PER_RB = len(output_re)
    N_PILOTS = N_PILOTS_PER_RB * LMMSE_P
    N_OUTPUT = N_OUTPUT_PER_RB * LMMSE_P

    # Output-group time-multiplexing: reduce MAC array, cycle through groups
    OUTPUT_GROUPS = 12 // FI_RE_PARALLELISM
    N_OUTPUT_ACTIVE = FI_RE_PARALLELISM * LMMSE_P  # MACs instantiated (12 for fire3)

    # Only dual-type Hybrid ports need compact/double-bank handling.
    # Hybrid type-specific ports should elaborate as a single fixed topology.
    is_hybrid = (dmrs_Type == "Hybrid" and pilot_re_t1 is not None and pilot_re_t2 is not None)

    # In SRAM mode, Hybrid bank selection is handled by the external COEFF_SRAM
    # module (rd_bank_sel), so the core itself does not need dual-bank ROM logic.
    if COEFF_SOURCE == 'SRAM':
        is_hybrid = False

    # Pre-compute R_freq if channel_model is specified (overrides sinc/tau_rms)
    _R_freq = None
    if channel_model is not None:
        K_total = LMMSE_P * 12
        _R_freq = compute_freq_covariance(K_total, model=channel_model,
                                          scs=scs, delay_spread=delay_spread)

    _use_compact = is_hybrid and compact_t2_slots is not None

    if COEFF_SOURCE == 'ROM':
        if is_hybrid:
            assert pilot_re_t1 is not None and pilot_re_t2 is not None
            _re_t1 = pilot_re_t1
            _re_t2 = pilot_re_t2

        if is_hybrid:
            if _R_freq is not None:
                W_t1_native = compute_freq_lmmse_W(_re_t1, output_re, LMMSE_P, snr_linear=snr_linear, R_freq=_R_freq)
                W_t2_native = compute_freq_lmmse_W(_re_t2, output_re, LMMSE_P, snr_linear=snr_linear, R_freq=_R_freq)
            else:
                W_t1_native = compute_freq_lmmse_W(_re_t1, output_re, LMMSE_P, tau_rms=tau_rms, snr_linear=snr_linear)
                W_t2_native = compute_freq_lmmse_W(_re_t2, output_re, LMMSE_P, tau_rms=tau_rms, snr_linear=snr_linear)
            assert _use_compact, "Hybrid LMMSE requires compact pilot layout"
            W_t1_padded = W_t1_native
            W_t2_padded = compact_pad_lmmse_matrix(
                W_t2_native,
                compact_t2_slots,
                N_PILOTS_PER_RB,
                N_OUTPUT,
                LMMSE_P,
            )
        else:
            if W_matrix_override is not None:
                W_single = W_matrix_override
            else:
                if _R_freq is not None:
                    W_single = compute_freq_lmmse_W(pilot_re, output_re, LMMSE_P, snr_linear=snr_linear, R_freq=_R_freq)
                else:
                    W_single = compute_freq_lmmse_W(pilot_re, output_re, LMMSE_P, tau_rms=tau_rms, snr_linear=snr_linear)

        # Quantise coefficients
        if REAL_COEFF:
            if is_hybrid:
                W_q_t1 = [[quantise_real(W_t1_padded[k][j].real if isinstance(W_t1_padded[k][j], complex) else W_t1_padded[k][j], COEFF_FRAC, COEFF_DWT)
                            for j in range(N_PILOTS)] for k in range(N_OUTPUT)]
                W_q_t2 = [[quantise_real(W_t2_padded[k][j].real if isinstance(W_t2_padded[k][j], complex) else W_t2_padded[k][j], COEFF_FRAC, COEFF_DWT)
                            for j in range(N_PILOTS)] for k in range(N_OUTPUT)]
            else:
                W_q_single = [[quantise_real(W_single[k][j].real, COEFF_FRAC, COEFF_DWT)
                               for j in range(N_PILOTS)] for k in range(N_OUTPUT)]
        else:
            if is_hybrid:
                W_q_t1 = [[quantise_complex(W_t1_padded[k][j], COEFF_FRAC, COEFF_DWT)
                            for j in range(N_PILOTS)] for k in range(N_OUTPUT)]
                W_q_t2 = [[quantise_complex(W_t2_padded[k][j], COEFF_FRAC, COEFF_DWT)
                            for j in range(N_PILOTS)] for k in range(N_OUTPUT)]
            else:
                W_q_single = [[quantise_complex(W_single[k][j], COEFF_FRAC, COEFF_DWT)
                               for j in range(N_PILOTS)] for k in range(N_OUTPUT)]

    # =========================================================================
    # Step 0b: Reshape W to [N_OUTPUT][FILL_BEATS][N_PILOTS_PER_BEAT]
    # =========================================================================
    assert LMMSE_P >= RB_PARALLELISM, f"LMMSE_P ({LMMSE_P}) must be >= RB_PARALLELISM ({RB_PARALLELISM})"
    assert LMMSE_P % RB_PARALLELISM == 0, f"LMMSE_P ({LMMSE_P}) must be divisible by RB_PARALLELISM ({RB_PARALLELISM})"

    FILL_BEATS_ORIG = LMMSE_P // RB_PARALLELISM
    FILL_BEATS = FILL_BEATS_ORIG * OUTPUT_GROUPS
    N_PILOTS_PER_BEAT = N_PILOTS_PER_RB * RB_PARALLELISM

    if COEFF_SOURCE == 'ROM':
        # Reshape: W_q[k_full][j] → W_reshaped[k_active][beat_total][q]
        # beat_total = group * FILL_BEATS_ORIG + beat_local
        # k_full = group * N_OUTPUT_ACTIVE + k_active
        # j = beat_local * N_PILOTS_PER_BEAT + q
        if is_hybrid:
            W_r_t1 = [[[W_q_t1[g * N_OUTPUT_ACTIVE + k][b_local * N_PILOTS_PER_BEAT + q]
                         for q in range(N_PILOTS_PER_BEAT)]
                        for g in range(OUTPUT_GROUPS)
                        for b_local in range(FILL_BEATS_ORIG)]
                       for k in range(N_OUTPUT_ACTIVE)]
            W_r_t2 = [[[W_q_t2[g * N_OUTPUT_ACTIVE + k][b_local * N_PILOTS_PER_BEAT + q]
                         for q in range(N_PILOTS_PER_BEAT)]
                        for g in range(OUTPUT_GROUPS)
                        for b_local in range(FILL_BEATS_ORIG)]
                       for k in range(N_OUTPUT_ACTIVE)]
        else:
            W_r = [[[W_q_single[g * N_OUTPUT_ACTIVE + k][b_local * N_PILOTS_PER_BEAT + q]
                      for q in range(N_PILOTS_PER_BEAT)]
                     for g in range(OUTPUT_GROUPS)
                     for b_local in range(FILL_BEATS_ORIG)]
                    for k in range(N_OUTPUT_ACTIVE)]

    # SRAM mode: coefficient data width for the external port
    # Each beat needs N_OUTPUT_ACTIVE * N_PILOTS_PER_BEAT coefficients simultaneously.
    # The port delivers all coefficients for one beat as a wide bus.
    COEFF_PER_BEAT = N_OUTPUT_ACTIVE * N_PILOTS_PER_BEAT
    COEFF_BEAT_DWT = COEFF_PER_BEAT * COEFF_DWT if REAL_COEFF else COEFF_PER_BEAT * 2 * COEFF_DWT
    BEAT_IDX_W = max(math.ceil(math.log2(FILL_BEATS)), 1)

    # =========================================================================
    # Step 1: Derived parameters
    # =========================================================================
    COMP_DWT_IN = Qu_H_LS.DWT
    COMP_DWT_OUT = Qu_H.DWT
    CPLX_DWT_IN = 2 * COMP_DWT_IN
    CPLX_DWT_OUT = 2 * COMP_DWT_OUT

    PROD_DWT = COMP_DWT_IN + COEFF_DWT
    PROD_FRAC = Qu_H_LS.FRAC + COEFF_FRAC

    # Uniform MAC policy: retain the full multiplier product through the tree.
    QU_PROD = QuType(PROD_DWT, PROD_FRAC, True)
    QU_TREE_IN = QU_PROD

    # Tree guard bits (adder tree of N_PILOTS_PER_BEAT inputs)
    ACC_GUARD_TREE = math.ceil(math.log2(max(N_PILOTS_PER_BEAT, 1))) if N_PILOTS_PER_BEAT > 1 else 0
    # Accumulation guard bits (summing FILL_BEATS_ORIG partial sums per group)
    ACC_GUARD_BEATS = math.ceil(math.log2(FILL_BEATS_ORIG)) if FILL_BEATS_ORIG > 1 else 0

    TREE_OUT_DWT = QU_TREE_IN.DWT + ACC_GUARD_TREE
    ACC_DWT = TREE_OUT_DWT + ACC_GUARD_BEATS
    ACC_FRAC = QU_TREE_IN.FRAC

    QU_TREE_OUT = QuType(TREE_OUT_DWT, QU_TREE_IN.FRAC, True)
    QU_ACC = QuType(ACC_DWT, ACC_FRAC, True)

    TREE_DEPTH = math.ceil(math.log2(max(N_PILOTS_PER_BEAT, 1))) if N_PILOTS_PER_BEAT > 1 else 0

    # ---- DelayBudget: determine register insertion before multiplier ----
    from delay_budget import COST_MUX
    _budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    if FILL_BEATS > 1:
        _budget.add_comb(COST_MUX, tag="coeff_rom_mux")
    REG_COEFF = _budget.need_register_before(cost_mul(COMP_DWT_IN, COEFF_DWT))
    # Pre-FI mode: LS_BUF has 1-cycle synchronous read latency, so ls_pilot_{q}
    # arrives at the MAC 1 cycle behind fill_cnt. Force REG_COEFF=True so the
    # coefficient ROM is also 1 cycle behind, keeping pilot and coeff aligned
    # on the same beat. With this, Step 4b pilot delay must be SKIPPED for
    # ls_pilot_{q} (otherwise it would be delayed twice) -- see Step 4b below.
    if has_pre_fi_buf:
        REG_COEFF = True
    if REG_COEFF:
        _budget.flush(tag="coeff_register")
    _budget.add_comb(cost_mul(COMP_DWT_IN, COEFF_DWT), tag="multiplier")
    _budget.add_register(MUL_LATENCY, tag="mul_pipe")
    REG_POST_CMUL = not REAL_COEFF and MUL_LATENCY > 0 and TREE_DEPTH > 0
    if REG_POST_CMUL:
        _budget.add_register(1, tag="post_cmul_reg")
        _budget.add_register(TREE_DEPTH - 1, tag="adder_tree")
    else:
        _budget.add_register(TREE_DEPTH, tag="adder_tree")
    PIPE_DELAY = _budget.pipeline_depth

    FILL_CNT_W = max(math.ceil(math.log2(FILL_BEATS)), 1)

    QU_COEFF = Qu_COEFF

    # Sign-extension width for tree output -> accumulator
    SEXT_BITS_ACC = ACC_DWT - TREE_OUT_DWT

    # LS buffer dimensions (pre-FI buffer mode)
    # ls_buf_rd_beat cycles 0..FILL_BEATS_ORIG-1 (pilots repeat per output group)
    LS_BUF_DATA_W = N_PILOTS_PER_BEAT * CPLX_DWT_IN
    LS_BUF_BEAT_W = max(math.ceil(math.log2(FILL_BEATS_ORIG)), 1) if FILL_BEATS_ORIG > 0 else 1

    # Build flat list of pilot input signal names
    pilot_signals = []
    if has_pre_fi_buf:
        for q in range(N_PILOTS_PER_BEAT):
            pilot_signals.append(f"ls_pilot_{q}")
    else:
        for rb in range(RB_PARALLELISM):
            for re_k in pilot_re:
                pilot_signals.append(f"h_ls_rb{rb}_re{re_k}")

    # =========================================================================
    # Step 2: Module declaration
    # =========================================================================
    #/ `timescale 1ns / 1ps
    #/ module CORE_LMMSE_INTERP (
    #/     input clk,
    if IF_RST_N:
        #/ input rst_n,
        pass

    if has_pre_fi_buf:
        #/ input  [`LS_BUF_DATA_W`-1:0] ls_buf_rd_data,
        #/ output                       ls_buf_rd_en,
        #/ output [`LS_BUF_BEAT_W`-1:0] ls_buf_rd_beat,
        pass
    else:
        for rb in range(RB_PARALLELISM):
            for re_k in pilot_re:
                #/ input [`CPLX_DWT_IN`-1:0] `f"h_ls_rb{rb}_re{re_k}"`,
                pass

    if is_hybrid:
        #/ input dmrs_type,
        pass

    #/ input enable,

    if COEFF_SOURCE == 'SRAM':
        #/ // Coefficient SRAM interface
        #/ output [`BEAT_IDX_W`-1:0]     coeff_rd_idx,
        #/ input  [`COEFF_BEAT_DWT`-1:0] coeff_rd_data,
        pass

    for rb in range(RB_PARALLELISM):
        for re_k in output_re:
            #/ output [`CPLX_DWT_OUT`-1:0] `f"h_out_rb{rb}_re{re_k}"`,
            pass

    #/ output drain_valid
    #/ );
    #/

    # =========================================================================
    # Step 2b: Clock gating — gate datapath clock when module is idle
    # =========================================================================
    _FLUSH_DEPTH = PIPE_DELAY + 1
    _FLUSH_W = max(math.ceil(math.log2(_FLUSH_DEPTH + 1)), 1)
    #/ // ===== ICG: gate datapath clock when idle =====
    if FILL_BEATS > 1:
        #/ reg draining;
        pass
    #/ reg [`_FLUSH_W`-1:0] pipe_flush;
    #/ always @(posedge clk) begin
    #/     if (enable) begin
    #/         pipe_flush <= `_FLUSH_W`'d`_FLUSH_DEPTH`;
    #/     end else if (pipe_flush != `_FLUSH_W`'d0) begin
    #/         pipe_flush <= pipe_flush - 1'b1;
    #/     end else begin
    #/         pipe_flush <= `_FLUSH_W`'d0;
    #/     end
    #/ end
    if FILL_BEATS > 1:
        #/ wire pipe_active = enable | draining | (pipe_flush != `_FLUSH_W`'d0);
        pass
    else:
        # The direct path has no drain phase, so there is no draining state to
        # keep alive.  Its clock remains active only for input and pipe flush.
        #/ wire pipe_active = enable | (pipe_flush != `_FLUSH_W`'d0);
        pass
    #/ reg pipe_active_latched;
    #/ always @(clk or pipe_active)
    #/     if (!clk) pipe_active_latched <= pipe_active;
    #/ wire clk_g = clk & pipe_active_latched;
    #/

    # =========================================================================
    # Step 3: Internal fill counter
    # =========================================================================
    if FILL_BEATS > 1:
        #/ // ===== Fill counter (gated by enable) =====
        #/ reg [`FILL_CNT_W`-1:0] fill_cnt;
        #/ always @(posedge clk) begin
        if IF_RST_N:
            #/ if (!rst_n) begin
            #/     fill_cnt <= `FILL_CNT_W`'d0;
            #/ end else begin
            pass
        #/ if (!enable) begin
        #/     fill_cnt <= `FILL_CNT_W`'d0;
        #/ end else if (fill_cnt == `FILL_CNT_W`'d`FILL_BEATS - 1`) begin
        #/     fill_cnt <= `FILL_CNT_W`'d0;
        #/ end else begin
        #/     fill_cnt <= fill_cnt + 1'b1;
        #/ end
        if IF_RST_N:
            #/ end
            pass
        #/ end
        #/
        pass

    # =========================================================================
    # Step 3b: LS buffer interface (pre-FI buffer mode)
    # =========================================================================
    if has_pre_fi_buf:
        #/ // ===== LS buffer read interface =====
        #/ assign ls_buf_rd_en = enable;
        if FILL_BEATS > 1:
            if OUTPUT_GROUPS > 1:
                FILL_BEATS_ORIG_W = max(math.ceil(math.log2(FILL_BEATS_ORIG)), 1)
                if FILL_BEATS_ORIG > 1:
                    #/ assign ls_buf_rd_beat = fill_cnt[`FILL_BEATS_ORIG_W - 1`:0];
                    pass
                else:
                    # A one-beat pilot window must replay SRAM address zero for
                    # every output group.  Using fill_cnt[0] here addresses an
                    # uninitialised second row when group 1 is issued.
                    #/ assign ls_buf_rd_beat = `LS_BUF_BEAT_W`'d0;
                    pass
            else:
                #/ assign ls_buf_rd_beat = fill_cnt;
                pass
        else:
            #/ assign ls_buf_rd_beat = `LS_BUF_BEAT_W`'d0;
            pass
        for q in range(N_PILOTS_PER_BEAT):
            _lo = q * CPLX_DWT_IN
            _hi = _lo + CPLX_DWT_IN - 1
            #/ wire [`CPLX_DWT_IN`-1:0] `f"ls_pilot_{q}"` = ls_buf_rd_data[`_hi`:`_lo`];
            pass
        #/ 
        pass

    # =========================================================================
    # Step 4: Coefficient source (ROM or SRAM)
    # =========================================================================
    if COEFF_SOURCE == 'SRAM':
        # --- SRAM mode: drive coeff_rd_idx = fill_cnt, unpack coeff_rd_data ---
        #/ // ===== Coefficient SRAM Interface =====
        if FILL_BEATS > 1:
            #/ assign coeff_rd_idx = fill_cnt;
            pass
        else:
            #/ assign coeff_rd_idx = `BEAT_IDX_W`'d0;
            pass
        _COEFF_BEAT_DWT = N_OUTPUT_ACTIVE * N_PILOTS_PER_BEAT * (COEFF_DWT if REAL_COEFF else 2 * COEFF_DWT)
        if REG_COEFF:
            #/ reg [`_COEFF_BEAT_DWT`-1:0] coeff_rd_data_r;
            #/ always @(posedge clk_g) coeff_rd_data_r <= coeff_rd_data;
            _coeff_src = 'coeff_rd_data_r'
        else:
            _coeff_src = 'coeff_rd_data'
        # Unpack: coeff_rd_data layout (MSB first):
        #   { w[N_OUTPUT_ACTIVE-1][N_PILOTS_PER_BEAT-1], ..., w[N_OUTPUT_ACTIVE-1][0],
        #     ...,
        #     w[0][N_PILOTS_PER_BEAT-1], ..., w[0][0] }
        # Bit position for w[k][q]: (k * N_PILOTS_PER_BEAT + q) * COEFF_DWT
        _UNIT = COEFF_DWT if REAL_COEFF else (2 * COEFF_DWT)
        for k in range(N_OUTPUT_ACTIVE):
            for q in range(N_PILOTS_PER_BEAT):
                flat_idx = k * N_PILOTS_PER_BEAT + q
                lo = flat_idx * _UNIT
                hi = lo + _UNIT - 1
                #/ wire [`_UNIT`-1:0] `f"w_{k}_{q}"` = `_coeff_src`[`hi`:`lo`];
                pass

    else:
        # --- ROM mode: hardwired case-ROM ---
        # When REG_COEFF is True (determined by DelayBudget), the case-ROM
        # output is registered (always @(posedge clk)) instead of combinational
        # (always @(*)).  This breaks the critical path between the LS output
        # and the multiplier input.
        _rom_sensitivity = "posedge clk_g" if REG_COEFF else "*"
        #/ // ===== Coefficient ROM (registered=`'yes' if REG_COEFF else 'no'`) =====
        for k in range(N_OUTPUT_ACTIVE):
            for q in range(N_PILOTS_PER_BEAT):
                if REAL_COEFF:
                    if FILL_BEATS == 1 and not is_hybrid:
                        val = W_r[k][0][q]
                        val_u = val & ((1 << COEFF_DWT) - 1)
                        #/ wire [`COEFF_DWT`-1:0] `f"w_{k}_{q}"` = `COEFF_DWT`'d`val_u`;
                        pass
                    elif FILL_BEATS == 1 and is_hybrid:
                        val_t1 = W_r_t1[k][0][q] & ((1 << COEFF_DWT) - 1)
                        val_t2 = W_r_t2[k][0][q] & ((1 << COEFF_DWT) - 1)
                        #/ wire [`COEFF_DWT`-1:0] `f"w_t1_{k}_{q}"` = `COEFF_DWT`'d`val_t1`;
                        #/ wire [`COEFF_DWT`-1:0] `f"w_t2_{k}_{q}"` = `COEFF_DWT`'d`val_t2`;
                        #/ wire [`COEFF_DWT`-1:0] `f"w_{k}_{q}"` = dmrs_type ? `f"w_t2_{k}_{q}"` : `f"w_t1_{k}_{q}"`;
                        pass
                    elif FILL_BEATS > 1 and not is_hybrid:
                        #/ reg [`COEFF_DWT`-1:0] `f"w_{k}_{q}"`;
                        #/ always @(`_rom_sensitivity`) begin
                        #/     case (fill_cnt)
                        for beat in range(FILL_BEATS):
                            val = W_r[k][beat][q] & ((1 << COEFF_DWT) - 1)
                            #/ `FILL_CNT_W`'d`beat`: `f"w_{k}_{q}"` = `COEFF_DWT`'d`val`;
                            pass
                        #/ default: `f"w_{k}_{q}"` = `COEFF_DWT`'d0;
                        #/ endcase
                        #/ end
                        pass
                    else:
                        CASE_W = 1 + FILL_CNT_W
                        #/ reg [`COEFF_DWT`-1:0] `f"w_{k}_{q}"`;
                        #/ always @(`_rom_sensitivity`) begin
                        #/     case ({dmrs_type, fill_cnt})
                        for dtype in range(2):
                            for beat in range(FILL_BEATS):
                                W_use = W_r_t1 if dtype == 0 else W_r_t2
                                val = W_use[k][beat][q] & ((1 << COEFF_DWT) - 1)
                                case_val = dtype * (1 << FILL_CNT_W) + beat
                                #/ `CASE_W`'d`case_val`: `f"w_{k}_{q}"` = `COEFF_DWT`'d`val`;
                                pass
                        #/ default: `f"w_{k}_{q}"` = `COEFF_DWT`'d0;
                        #/ endcase
                        #/ end
                        pass
                else:
                    if FILL_BEATS == 1 and not is_hybrid:
                        w_re, w_im = W_r[k][0][q]
                        #/ wire [`2*COEFF_DWT`-1:0] `f"w_{k}_{q}"` = {`COEFF_DWT`'d`w_im & ((1 << COEFF_DWT) - 1)`, `COEFF_DWT`'d`w_re & ((1 << COEFF_DWT) - 1)`};
                        pass
                    elif FILL_BEATS == 1 and is_hybrid:
                        w_re_t1, w_im_t1 = W_r_t1[k][0][q]
                        w_re_t2, w_im_t2 = W_r_t2[k][0][q]
                        #/ wire [`2*COEFF_DWT`-1:0] `f"w_t1_{k}_{q}"` = {`COEFF_DWT`'d`w_im_t1 & ((1 << COEFF_DWT) - 1)`, `COEFF_DWT`'d`w_re_t1 & ((1 << COEFF_DWT) - 1)`};
                        #/ wire [`2*COEFF_DWT`-1:0] `f"w_t2_{k}_{q}"` = {`COEFF_DWT`'d`w_im_t2 & ((1 << COEFF_DWT) - 1)`, `COEFF_DWT`'d`w_re_t2 & ((1 << COEFF_DWT) - 1)`};
                        #/ wire [`2*COEFF_DWT`-1:0] `f"w_{k}_{q}"` = dmrs_type ? `f"w_t2_{k}_{q}"` : `f"w_t1_{k}_{q}"`;
                        pass
                    elif FILL_BEATS > 1 and not is_hybrid:
                        #/ reg [`2*COEFF_DWT`-1:0] `f"w_{k}_{q}"`;
                        #/ always @(`_rom_sensitivity`) begin
                        #/     case (fill_cnt)
                        for beat in range(FILL_BEATS):
                            w_re, w_im = W_r[k][beat][q]
                            packed = ((w_im & ((1 << COEFF_DWT) - 1)) << COEFF_DWT) | (w_re & ((1 << COEFF_DWT) - 1))
                            #/ `FILL_CNT_W`'d`beat`: `f"w_{k}_{q}"` = `2*COEFF_DWT`'d`packed`;
                            pass
                        #/ default: `f"w_{k}_{q}"` = `2*COEFF_DWT`'d0;
                        #/ endcase
                        #/ end
                        pass
                    else:
                        CASE_W = 1 + FILL_CNT_W
                        #/ reg [`2*COEFF_DWT`-1:0] `f"w_{k}_{q}"`;
                        #/ always @(`_rom_sensitivity`) begin
                        #/     case ({dmrs_type, fill_cnt})
                        for dtype in range(2):
                            for beat in range(FILL_BEATS):
                                W_use = W_r_t1 if dtype == 0 else W_r_t2
                                w_re, w_im = W_use[k][beat][q]
                                packed = ((w_im & ((1 << COEFF_DWT) - 1)) << COEFF_DWT) | (w_re & ((1 << COEFF_DWT) - 1))
                                case_val = dtype * (1 << FILL_CNT_W) + beat
                                #/ `CASE_W`'d`case_val`: `f"w_{k}_{q}"` = `2*COEFF_DWT`'d`packed`;
                                pass
                        #/ default: `f"w_{k}_{q}"` = `2*COEFF_DWT`'d0;
                        #/ endcase
                        #/ end
                        #/ 

    # =========================================================================
    # Step 4b: Pilot input delay (when coefficient ROM is registered)
    # Pre-FI mode: ls_pilot_{q} is already 1 cycle behind fill_cnt via LS_BUF's
    # synchronous read, so the registered coefficient ROM alone provides perfect
    # alignment. Skip the extra delay that non-pre-FI configs need.
    # =========================================================================
    if REG_COEFF and not has_pre_fi_buf:
        #/ // ===== Pilot input delay (align with registered coefficient ROM) =====
        for q in range(N_PILOTS_PER_BEAT):
            orig = pilot_signals[q]
            delayed = f"{orig}_d"
            #/ wire [`CPLX_DWT_IN`-1:0] `delayed`;
            _pd_ports = {'i_clk': 'clk_g', 'i_data': orig, 'o_data': delayed}
            if IF_RST_N:
                _pd_ports['i_rst_n'] = 'rst_n'
            ModuleDelay(DWT=CPLX_DWT_IN, IF_RST_N=IF_RST_N, N_CLK=1, PORTS=_pd_ports)
            pilot_signals[q] = delayed
        #/ 

    # =========================================================================
    # Step 4c: Operand isolation (gate pilot inputs when enable=0)
    # When REG_COEFF is True, pilot data is delayed by 1 clock in Step 4b.
    # The enable signal must also be delayed to match, otherwise the last
    # pilot of the last window is zeroed out (enable drops 1 cycle early).
    # =========================================================================
    if REG_COEFF:
        #/ // ===== Enable delay (align with registered pilot delay) =====
        #/ wire enable_gated;
        _en_delay = fi_core_graph.build_delay_table()['enable_gated']['delay']
        _en_ports = {'i_clk': 'clk', 'i_data': 'enable', 'o_data': 'enable_gated'}
        if IF_RST_N:
            _en_ports['i_rst_n'] = 'rst_n'
        ModuleDelay(DWT=1, IF_RST_N=IF_RST_N, N_CLK=_en_delay, PORTS=_en_ports)
        gate_enable = 'enable_gated'
    else:
        gate_enable = 'enable'
    pass

    #/ // ===== Operand isolation (zero pilot data when idle to reduce switching) =====
    for q in range(N_PILOTS_PER_BEAT):
        orig = pilot_signals[q]
        gated = f"{orig}_g"
        #/ wire [`CPLX_DWT_IN`-1:0] `gated` = `gate_enable` ? `orig` : `CPLX_DWT_IN`'d0;
        pilot_signals[q] = gated
    #/ 

    # =========================================================================
    # Step 5: Multiplier array
    # =========================================================================
    #/ // ===== Multiplier Array =====
    for k in range(N_OUTPUT_ACTIVE):
        for q in range(N_PILOTS_PER_BEAT):
            pilot_sig = pilot_signals[q]
            if REAL_COEFF:
                pilot_re_sig = f"pilot_re_{k}_{q}"
                pilot_im_sig = f"pilot_im_{k}_{q}"
                #/ wire [`COMP_DWT_IN`-1:0] `pilot_re_sig` = `pilot_sig`[`COMP_DWT_IN`-1:0];
                #/ wire [`COMP_DWT_IN`-1:0] `pilot_im_sig` = `pilot_sig`[`CPLX_DWT_IN`-1:`COMP_DWT_IN`];

                prod_re_name = f"prod_re_{k}_{q}"
                prod_im_name = f"prod_im_{k}_{q}"
                #/ wire [`QU_PROD.DWT`-1:0] `prod_re_name`;
                #/ wire [`QU_PROD.DWT`-1:0] `prod_im_name`;

                mul_ports_re = {
                    'i_data_1': pilot_re_sig,
                    'i_data_2': f"w_{k}_{q}",
                    'o_data': prod_re_name,
                }
                mul_ports_im = {
                    'i_data_1': pilot_im_sig,
                    'i_data_2': f"w_{k}_{q}",
                    'o_data': prod_im_name,
                }
                if MUL_LATENCY > 0:
                    mul_ports_re['i_clk'] = 'clk_g'
                    mul_ports_im['i_clk'] = 'clk_g'
                    if IF_RST_N:
                        mul_ports_re['i_rst_n'] = 'rst_n'
                        mul_ports_im['i_rst_n'] = 'rst_n'

                ModuleMul(QU_IN_1=Qu_H_LS, QU_IN_2=QU_COEFF, QU_OUT=QU_PROD, N_CLK=MUL_LATENCY, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=IF_RST_N, PORTS=mul_ports_re)
                ModuleMul(QU_IN_1=Qu_H_LS, QU_IN_2=QU_COEFF, QU_OUT=QU_PROD, N_CLK=MUL_LATENCY, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=IF_RST_N, PORTS=mul_ports_im)
            else:
                prod_name = f"prod_{k}_{q}"
                #/ wire [`2*QU_PROD.DWT`-1:0] `prod_name`;
                QU_CPLX_COEFF = Qu_COEFF
                cmul_ports = {
                    'i_data_1': pilot_sig,
                    'i_data_2': f"w_{k}_{q}",
                    'o_data': prod_name,
                }
                if MUL_LATENCY > 0:
                    cmul_ports['i_clk'] = 'clk_g'
                    if IF_RST_N:
                        cmul_ports['i_rst_n'] = 'rst_n'

                ModuleComplexMul(QU_IN_1=Qu_H_LS, QU_IN_2=QU_CPLX_COEFF, QU_OUT=QU_PROD, N_CLK=MUL_LATENCY, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, IF_RST_N=IF_RST_N, METHOD='4mul', PORTS=cmul_ports)
    #/ 

    # =========================================================================
    # Step 5b: Post-ComplexMul pipeline register (break critical path)
    # Steals one pipeline stage from the adder tree so total depth is unchanged.
    # =========================================================================
    if REG_POST_CMUL:
        #/ // ===== Post-ComplexMul Pipeline Register =====
        for k in range(N_OUTPUT_ACTIVE):
            for q in range(N_PILOTS_PER_BEAT):
                prod_name = f"prod_{k}_{q}"
                prod_d_name = f"prod_{k}_{q}_d"
                #/ wire [`2*QU_PROD.DWT`-1:0] `prod_d_name`;
                _pcr_ports = {'i_clk': 'clk_g', 'i_data': prod_name, 'o_data': prod_d_name}
                if IF_RST_N:
                    _pcr_ports['i_rst_n'] = 'rst_n'
                ModuleDelay(DWT=2 * QU_PROD.DWT, IF_RST_N=IF_RST_N, N_CLK=1, PORTS=_pcr_ports)
        #/ 

    # =========================================================================
    # Step 6: Adder tree
    # =========================================================================
    #/ // ===== Adder Tree =====
    for k in range(N_OUTPUT_ACTIVE):
        if REAL_COEFF:
            if N_PILOTS_PER_BEAT == 1:
                #/ wire [`QU_PROD.DWT`-1:0] `f"sum_re_{k}"` = `f"prod_re_{k}_0"`;
                #/ wire [`QU_PROD.DWT`-1:0] `f"sum_im_{k}"` = `f"prod_im_{k}_0"`;
                pass
            else:
                re_parts = [f"prod_re_{k}_{q}" for q in range(N_PILOTS_PER_BEAT)]
                im_parts = [f"prod_im_{k}_{q}" for q in range(N_PILOTS_PER_BEAT)]
                re_concat = "{" + ", ".join(reversed(re_parts)) + "}"
                im_concat = "{" + ", ".join(reversed(im_parts)) + "}"
                #/ wire [`QU_TREE_IN.DWT * N_PILOTS_PER_BEAT`-1:0] `f"tree_re_in_{k}"` = `re_concat`;
                #/ wire [`QU_TREE_IN.DWT * N_PILOTS_PER_BEAT`-1:0] `f"tree_im_in_{k}"` = `im_concat`;

                sum_re_name = f"sum_re_{k}"
                sum_im_name = f"sum_im_{k}"
                #/ wire [`QU_TREE_OUT.DWT`-1:0] `sum_re_name`;
                #/ wire [`QU_TREE_OUT.DWT`-1:0] `sum_im_name`;

                tree_ports_re = {
                    'i_data': f"tree_re_in_{k}",
                    'o_data': sum_re_name,
                }
                tree_ports_im = {
                    'i_data': f"tree_im_in_{k}",
                    'o_data': sum_im_name,
                }
                if TREE_DEPTH > 0:
                    tree_ports_re['i_clk'] = 'clk_g'
                    tree_ports_im['i_clk'] = 'clk_g'
                    if IF_RST_N:
                        tree_ports_re['i_rst_n'] = 'rst_n'
                        tree_ports_im['i_rst_n'] = 'rst_n'

                ModuleAdderTree(QU_IN=QU_TREE_IN, QU_OUT=QU_TREE_OUT, N_PIPELINES=TREE_DEPTH, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=IF_RST_N, N_INPUTS=N_PILOTS_PER_BEAT, CONFIG_MODE='A', PORTS=tree_ports_re)
                ModuleAdderTree(QU_IN=QU_TREE_IN, QU_OUT=QU_TREE_OUT, N_PIPELINES=TREE_DEPTH, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=IF_RST_N, N_INPUTS=N_PILOTS_PER_BEAT, CONFIG_MODE='A', PORTS=tree_ports_im)
        else:
            _psuf = '_d' if REG_POST_CMUL else ''
            _tree_pipes = TREE_DEPTH - 1 if REG_POST_CMUL else TREE_DEPTH
            if N_PILOTS_PER_BEAT == 1:
                #/ wire [`QU_PROD.DWT`-1:0] `f"sum_re_{k}"` = `f"prod_{k}_0{_psuf}"`[`QU_PROD.DWT`-1:0];
                #/ wire [`QU_PROD.DWT`-1:0] `f"sum_im_{k}"` = `f"prod_{k}_0{_psuf}"`[`2*QU_PROD.DWT`-1:`QU_PROD.DWT`];
                pass
            else:
                for comp_tag in ['re', 'im']:
                    comp_parts = []
                    for q in range(N_PILOTS_PER_BEAT):
                        if comp_tag == 're':
                            comp_parts.append(f"prod_{k}_{q}{_psuf}[{QU_PROD.DWT}-1:0]")
                        else:
                            comp_parts.append(f"prod_{k}_{q}{_psuf}[{2*QU_PROD.DWT}-1:{QU_PROD.DWT}]")
                    comp_concat = "{" + ", ".join(reversed(comp_parts)) + "}"
                    #/ wire [`QU_PROD.DWT * N_PILOTS_PER_BEAT`-1:0] `f"tree_{comp_tag}_in_{k}"` = `comp_concat`;

                    sum_name = f"sum_{comp_tag}_{k}"
                    #/ wire [`QU_TREE_OUT.DWT`-1:0] `sum_name`;

                    tree_ports = {
                        'i_data': f"tree_{comp_tag}_in_{k}",
                        'o_data': sum_name,
                    }
                    if _tree_pipes > 0:
                        tree_ports['i_clk'] = 'clk_g'
                        if IF_RST_N:
                            tree_ports['i_rst_n'] = 'rst_n'

                    ModuleAdderTree(QU_IN=QU_TREE_IN, QU_OUT=QU_TREE_OUT, N_PIPELINES=_tree_pipes, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=IF_RST_N, N_INPUTS=N_PILOTS_PER_BEAT, CONFIG_MODE='A', PORTS=tree_ports)
    #/ 

    # =========================================================================
    # Output stage
    # =========================================================================
    if FILL_BEATS > 1:
        # =================================================================
        # Streaming accumulate path (with output-group time-multiplexing)
        # =================================================================
        FILL_BEATS_ORIG_W = max(math.ceil(math.log2(FILL_BEATS_ORIG)), 1)
        GROUP_CNT_W = max(math.ceil(math.log2(OUTPUT_GROUPS)), 1) if OUTPUT_GROUPS > 1 else 1

        # --- Step 7: Pipeline delay on fill_cnt (graph-driven) ---
        #/ // ===== Pipeline delay on fill_cnt =====
        _fi_delay_table = fi_core_graph.build_delay_table()
        for _dst in ('fill_cnt_d', 'fill_cnt_dd'):
            _sig_info = _fi_delay_table[_dst]
            _n_clk = _sig_info['delay']
            _dwt = _sig_info['width']
            #/ wire [`_dwt`-1:0] `_dst`;
            _dp = {'i_clk': 'clk', 'i_data': 'fill_cnt', 'o_data': _dst}
            if IF_RST_N:
                _dp['i_rst_n'] = 'rst_n'
            ModuleDelay(DWT=_dwt, IF_RST_N=IF_RST_N, N_CLK=_n_clk, PORTS=_dp)  # type: ignore

        if OUTPUT_GROUPS > 1:
            if FILL_BEATS_ORIG > 1:
                #/ wire [`FILL_BEATS_ORIG_W`-1:0] beat_in_group_dd = fill_cnt_dd[`FILL_BEATS_ORIG_W - 1`:0];
                #/ wire [`GROUP_CNT_W`-1:0]       group_cnt_dd = fill_cnt_dd[`FILL_CNT_W - 1`:`FILL_BEATS_ORIG_W`];
                #/ wire [`FILL_BEATS_ORIG_W`-1:0] beat_in_group_d = fill_cnt_d[`FILL_BEATS_ORIG_W - 1`:0];
                pass
            else:
                # With one pilot beat per group, fill_cnt contains only the
                # output-group index; selecting a nonexistent low beat field
                # would create a reversed/out-of-range part-select.
                #/ wire [`FILL_BEATS_ORIG_W`-1:0] beat_in_group_dd = `FILL_BEATS_ORIG_W`'d0;
                #/ wire [`GROUP_CNT_W`-1:0]       group_cnt_dd = fill_cnt_dd[`GROUP_CNT_W - 1`:0];
                #/ wire [`FILL_BEATS_ORIG_W`-1:0] beat_in_group_d = `FILL_BEATS_ORIG_W`'d0;
                pass
            #/ wire                           acc_done = (beat_in_group_dd == `FILL_BEATS_ORIG_W`'d`FILL_BEATS_ORIG - 1`);
            #/ wire                           all_groups_done = acc_done & (group_cnt_dd == `GROUP_CNT_W`'d`OUTPUT_GROUPS - 1`);
            pass
        else:
            #/ wire acc_done = (fill_cnt_dd == `FILL_CNT_W`'d`FILL_BEATS - 1`);
            #/ wire all_groups_done = acc_done;
            pass
        #/ 

        # --- Step 8: Accumulator ---
        #/ // ===== Accumulator =====
        QU_SUM_SRC = QU_TREE_OUT if N_PILOTS_PER_BEAT > 1 else QU_PROD
        SUM_SRC_DWT = QU_SUM_SRC.DWT

        for k in range(N_OUTPUT_ACTIVE):
            sum_re = f"sum_re_{k}" if N_PILOTS_PER_BEAT > 1 else f"prod_re_{k}_0"
            sum_im = f"sum_im_{k}" if N_PILOTS_PER_BEAT > 1 else f"prod_im_{k}_0"

            if SEXT_BITS_ACC > 0:
                #/ wire [`ACC_DWT`-1:0] `f"tree_ext_re_{k}"` = {{`SEXT_BITS_ACC`{`sum_re`[`SUM_SRC_DWT - 1`]}}, `sum_re`};
                #/ wire [`ACC_DWT`-1:0] `f"tree_ext_im_{k}"` = {{`SEXT_BITS_ACC`{`sum_im`[`SUM_SRC_DWT - 1`]}}, `sum_im`};
                pass

            #/ reg [`ACC_DWT`-1:0] `f"acc_re_{k}"`;
            #/ reg [`ACC_DWT`-1:0] `f"acc_im_{k}"`;

        # Accumulator reset condition: start of each group (beat_in_group_d == 0)
        _acc_reset_cond = f"beat_in_group_d == {FILL_BEATS_ORIG_W}'d0" if OUTPUT_GROUPS > 1 else f"fill_cnt_d == {FILL_CNT_W}'d0"

        if IF_RST_N:
            #/ always @(posedge clk_g or negedge rst_n) begin
            #/     if (!rst_n) begin
            for k in range(N_OUTPUT_ACTIVE):
                #/ `f"acc_re_{k}"` <= `ACC_DWT`'d0;
                #/ `f"acc_im_{k}"` <= `ACC_DWT`'d0;
                pass
            #/ end else begin
            pass
        else:
            #/ always @(posedge clk_g) begin
            pass
        #/ if (`_acc_reset_cond`) begin
        for k in range(N_OUTPUT_ACTIVE):
            ext_re = f"tree_ext_re_{k}" if SEXT_BITS_ACC > 0 else (f"sum_re_{k}" if N_PILOTS_PER_BEAT > 1 else f"prod_re_{k}_0")
            ext_im = f"tree_ext_im_{k}" if SEXT_BITS_ACC > 0 else (f"sum_im_{k}" if N_PILOTS_PER_BEAT > 1 else f"prod_im_{k}_0")
            #/ `f"acc_re_{k}"` <= `ext_re`;
            #/ `f"acc_im_{k}"` <= `ext_im`;
            pass
        #/ end else begin
        for k in range(N_OUTPUT_ACTIVE):
            ext_re = f"tree_ext_re_{k}" if SEXT_BITS_ACC > 0 else (f"sum_re_{k}" if N_PILOTS_PER_BEAT > 1 else f"prod_re_{k}_0")
            ext_im = f"tree_ext_im_{k}" if SEXT_BITS_ACC > 0 else (f"sum_im_{k}" if N_PILOTS_PER_BEAT > 1 else f"prod_im_{k}_0")
            #/ `f"acc_re_{k}"` <= `f"acc_re_{k}"` + `ext_re`;
            #/ `f"acc_im_{k}"` <= `f"acc_im_{k}"` + `ext_im`;
            pass
        #/ end
        if IF_RST_N:
            #/ end
            pass
        #/ end
        #/ 

        # --- Step 9: FxMatch + output buffer ---
        #/ // ===== FxMatch + Output Buffer =====
        for k in range(N_OUTPUT_ACTIVE):
            fxm_re = f"fxm_re_{k}"
            fxm_im = f"fxm_im_{k}"
            #/ wire [`COMP_DWT_OUT`-1:0] `fxm_re`;
            #/ wire [`COMP_DWT_OUT`-1:0] `fxm_im`;
            ModuleFxMatch(QU_IN=QU_ACC, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': f'acc_re_{k}', 'o_data': fxm_re})
            ModuleFxMatch(QU_IN=QU_ACC, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': f'acc_im_{k}', 'o_data': fxm_im})

        for k in range(N_OUTPUT):
            #/ reg [`CPLX_DWT_OUT`-1:0] `f"out_buf_{k}"`;
            pass

        #/ always @(posedge clk_g) begin
        if IF_RST_N:
            #/ if (!rst_n) begin
            for k in range(N_OUTPUT):
                #/ `f"out_buf_{k}"` <= `CPLX_DWT_OUT`'d0;
                pass
            #/ end else begin
            pass
        if OUTPUT_GROUPS > 1:
            #/ if (acc_done) begin
            for g in range(OUTPUT_GROUPS):
                if g == 0:
                    #/ if (group_cnt_dd == `GROUP_CNT_W`'d`g`) begin
                    pass
                else:
                    #/ end else if (group_cnt_dd == `GROUP_CNT_W`'d`g`) begin
                    pass
                for k in range(N_OUTPUT_ACTIVE):
                    buf_idx = g * N_OUTPUT_ACTIVE + k
                    #/ `f"out_buf_{buf_idx}"` <= {`f"fxm_im_{k}"`, `f"fxm_re_{k}"`};
                    pass
            #/ end
            #/ end
        else:
            #/ if (acc_done) begin
            for k in range(N_OUTPUT):
                #/ `f"out_buf_{k}"` <= {`f"fxm_im_{k}"`, `f"fxm_re_{k}"`};
                pass
            #/ end
        if IF_RST_N:
            #/ end
            pass
        #/ end
        #/ 

        # --- Step 10: Drain counter + mux ---
        # Drain outputs FILL_BEATS_ORIG RB-groups (one per clock) after all groups done
        DRAIN_BEATS = FILL_BEATS_ORIG
        DRAIN_CNT_W_ACT = max(math.ceil(math.log2(DRAIN_BEATS)), 1)
        #/ // ===== Drain counter + output mux =====
        #/ reg [`DRAIN_CNT_W_ACT`-1:0] drain_cnt;
        #/ always @(posedge clk) begin
        if IF_RST_N:
            #/ if (!rst_n) begin
            #/     drain_cnt <= `DRAIN_CNT_W_ACT`'d0;
            #/     draining <= 1'b0;
            #/ end else begin
            pass
        #/ if (all_groups_done) begin
        #/     drain_cnt <= `DRAIN_CNT_W_ACT`'d0;
        #/     draining <= 1'b1;
        #/ end else if (draining) begin
        #/     if (drain_cnt == `DRAIN_CNT_W_ACT`'d`DRAIN_BEATS - 1`) begin
        #/         draining <= 1'b0;
        #/     end else begin
        #/         drain_cnt <= drain_cnt + 1'b1;
        #/     end
        #/ end
        if IF_RST_N:
            #/ end
            pass
        #/ end
        #/ 

        # Drain mux: select which RB-group from out_buf to expose
        for rb in range(RB_PARALLELISM):
            for re_idx, re_k in enumerate(output_re):
                #/ reg [`CPLX_DWT_OUT`-1:0] `f"drain_rb{rb}_re{re_k}"`;
                pass

        #/ always @(*) begin
        #/     case (drain_cnt)
        for d in range(DRAIN_BEATS):
            #/ `DRAIN_CNT_W_ACT`'d`d`: begin
            for rb in range(RB_PARALLELISM):
                for re_idx, re_k in enumerate(output_re):
                    buf_k = (d * RB_PARALLELISM + rb) * N_OUTPUT_PER_RB + re_idx
                    #/ `f"drain_rb{rb}_re{re_k}"` = `f"out_buf_{buf_k}"`;
                    pass
            #/ end
            pass

        #/ default: begin
        for rb in range(RB_PARALLELISM):
            for re_idx, re_k in enumerate(output_re):
                #/ `f"drain_rb{rb}_re{re_k}"` = `CPLX_DWT_OUT`'d0;
                pass
        #/ end
        #/ endcase
        #/ end
        #/ 
        #/ // ===== Output Assignment =====
        for rb in range(RB_PARALLELISM):
            for re_k in output_re:
                #/ assign `f"h_out_rb{rb}_re{re_k}"` = `f"drain_rb{rb}_re{re_k}"`;
                pass

    else:
        # =================================================================
        # Direct path (FILL_BEATS == 1, no accumulation needed)
        # =================================================================
        #/ // ===== Direct Output =====
        QU_SUM = QU_TREE_OUT if N_PILOTS_PER_BEAT > 1 else QU_PROD

        for k in range(N_OUTPUT):
            rb_out = k // N_OUTPUT_PER_RB
            re_out = output_re[k % N_OUTPUT_PER_RB]

            sum_re = f"sum_re_{k}" if N_PILOTS_PER_BEAT > 1 else f"prod_re_{k}_0"
            sum_im = f"sum_im_{k}" if N_PILOTS_PER_BEAT > 1 else f"prod_im_{k}_0"

            out_re_name = f"out_re_{k}"
            out_im_name = f"out_im_{k}"
            #/ wire [`COMP_DWT_OUT`-1:0] `out_re_name`;
            #/ wire [`COMP_DWT_OUT`-1:0] `out_im_name`;

            if REAL_COEFF:
                ModuleFxMatch(QU_IN=QU_SUM, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': sum_re, 'o_data': out_re_name})
                ModuleFxMatch(QU_IN=QU_SUM, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': sum_im, 'o_data': out_im_name})
            else:
                ModuleFxMatch(QU_IN=QU_SUM, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': sum_re, 'o_data': out_re_name})
                ModuleFxMatch(QU_IN=QU_SUM, QU_OUT=Qu_H, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.SAT.TCPL, N_CLK=0, IF_RST_N=False, PORTS={'i_data': sum_im, 'o_data': out_im_name})

            reg_out_name = f"reg_out_{k}"
            #/ wire [`CPLX_DWT_OUT`-1:0] `reg_out_name`;
            delay_ports = {
                'i_data': "{" + out_im_name + ", " + out_re_name + "}",
                'o_data': reg_out_name,
                'i_clk': 'clk_g',
            }
            if IF_RST_N:
                delay_ports['i_rst_n'] = 'rst_n'

            ModuleDelay(DWT=CPLX_DWT_OUT, N_CLK=1, IF_RST_N=IF_RST_N, PORTS=delay_ports)

        # A one-beat window still has a real multiplier/tree/output-register
        # pipeline.  Its valid must be a pulse aligned with reg_out, not a
        # permanent assertion: in pre-FI TOP mode drain_valid is also the
        # occasion-register write enable, so a constant value overwrites the
        # first occasion while TI is sweeping later RB lanes.
        # PIPE_DELAY covers the multiplier/adder-tree pipeline only.  The
        # direct path also has the one-cycle enable_gated input stage and the
        # one-cycle reg_out stage.  Delay the pulse through both so the
        # downstream occasion register samples the completed reg_out value.
        _direct_valid_delay = PIPE_DELAY + 2
        #/ wire direct_valid;
        _valid_ports = {
            'i_clk': 'clk',
            'i_data': 'enable',
            'o_data': 'direct_valid',
        }
        if IF_RST_N:
            _valid_ports['i_rst_n'] = 'rst_n'
        ModuleDelay(DWT=1, N_CLK=_direct_valid_delay, IF_RST_N=IF_RST_N, PORTS=_valid_ports)

        #/ // ===== Output Assignment =====
        for k in range(N_OUTPUT):
            rb_out = k // N_OUTPUT_PER_RB
            re_out = output_re[k % N_OUTPUT_PER_RB]
            #/ assign `f"h_out_rb{rb_out}_re{re_out}"` = `f"reg_out_{k}"`;

    # =========================================================================
    # drain_valid output: HIGH when output data is valid
    # =========================================================================
    if FILL_BEATS > 1:
        #/ assign drain_valid = draining;
        pass
    else:
        #/ assign drain_valid = direct_valid;
        pass

    #/ 
    #/ endmodule
    pass


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    ModuleCORE_LMMSE_INTERP(
        IF_RST_N=True,
        LMMSE_P=4,
        RB_PARALLELISM=1,
        Qu_H_LS=QuType(12, 4, True),
        Qu_H=QuType(12, 4, True),
        pilot_re=[0, 2, 4, 6, 8, 10],
        output_re=list(range(12)),
        dmrs_Type=1,
        Qu_COEFF=QuType(12, 10, True),
        REAL_COEFF=True,
        W_matrix_override=None,
        tau_rms=3.0,
        snr_linear=100.0,
        channel_model='TDL-C',
        delay_spread=200e-9,
        scs=30e3,
    )

    # Test: SRAM mode
    ModuleCORE_LMMSE_INTERP(
        IF_RST_N=True,
        LMMSE_P=4,
        RB_PARALLELISM=1,
        Qu_H_LS=QuType(12, 4, True),
        Qu_H=QuType(12, 4, True),
        pilot_re=[0, 2, 4, 6, 8, 10],
        output_re=list(range(12)),
        dmrs_Type=1,
        Qu_COEFF=QuType(12, 10, True),
        REAL_COEFF=True,
        W_matrix_override=None,
        tau_rms=3.0,
        snr_linear=100.0,
        COEFF_SOURCE='SRAM',
        channel_model='TDL-C',
        delay_spread=200e-9,
        scs=30e3,
    )

    # Test: complex coefficients (REAL_COEFF=False) with post-cmul register
    ModuleCORE_LMMSE_INTERP(
        IF_RST_N=True,
        LMMSE_P=4,
        RB_PARALLELISM=1,
        Qu_H_LS=QuType(12, 4, True),
        Qu_H=QuType(12, 4, True),
        pilot_re=[0, 2, 4, 6, 8, 10],
        output_re=list(range(12)),
        dmrs_Type=1,
        Qu_COEFF=QuType(12, 10, True),
        REAL_COEFF=False,
        W_matrix_override=None,
        tau_rms=3.0,
        snr_linear=100.0,
        channel_model='TDL-C',
        delay_spread=200e-9,
        scs=30e3,
    )
