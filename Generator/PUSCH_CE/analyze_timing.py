import math
from typing import Dict, List, Optional

from basic_modules.PyTU import QuType
from delay_budget import COST_ADDER_8B, COST_MUL_8B, DEFAULT_BUDGET, DelayBudget
from v_averaging import averaging_pipeline_depth
from v_core_lin_interp import lin_freq_pipeline_depth
from v_core_nn_interp import nn_freq_pipeline_depth
from v_core_time_lin_interp import time_lin_pipeline_depth
from v_core_time_lmmse_interp import time_lmmse_pipeline_depth
from v_core_time_nn_interp import time_nn_pipeline_depth
from v_ls_rot import ls_rot_pipeline_depth
from v_occ import occ_pipeline_depth
from v_y_pre import y_pre_pipeline_depth


# =============================================================================
# Control Signal Dependency Graph (event-relative)
# =============================================================================

class ControlSignalGraph:
    """
    Event-relative control signal dependency graph.

    Signals are anchored to named **events** with clock-cycle offsets.
    Events can be related to each other via ``relate_events()``.
    Delay chains are auto-computed: ``latency = dst.abs_delay - src.abs_delay``.

    Usage
    -----
    1. ``define_event(name)`` — create a root timing event (abs_offset=0).
    2. ``relate_events(src, dst, offset=N)`` — declare dst = src + N clocks.
    3. ``define_signal(name, event=E, offset=K)`` — anchor signal at E + K.
    4. ``connect(src, dst, target_event=E, target_offset=K)`` — create delay
       chain so dst arrives at E + K.  Latency = (E+K) - src.abs_delay.
    5. ``validate()`` — check all constraints.
    6. ``build_delay_table()`` — return dict for ModuleDelay instantiation.

    Design principle
    ----------------
    Absolute delays propagate transitively through event relationships.
    A pipeline depth change only requires updating ``relate_events()``
    or ``target_event/offset``; all downstream latencies recompute.
    """

    def __init__(self) -> None:
        self._events: Dict[str, dict] = {}       # name -> {abs_offset, description, is_root}
        self._signals: Dict[str, dict] = {}       # name -> {event, offset, abs_delay, width, wire, desc}
        self._edges: List[dict] = []              # delay chain entries
        self._alignment_groups: Dict[str, list] = {}  # group_name -> [signal_names]

    # ------------------------------------------------------------------
    # Event API
    # ------------------------------------------------------------------

    def define_event(self, name: str, *, description: str = "") -> None:
        """Define a root timing event with abs_offset=0."""
        if name in self._events:
            raise ValueError(f"ControlSignalGraph: event '{name}' already defined.")
        self._events[name] = {
            'abs_offset': 0,
            'description': description,
            'is_root': True,
        }

    def relate_events(self, src: str, dst: str, *, offset: int,
                      description: str = "") -> None:
        """
        Declare ``dst.abs_offset = src.abs_offset + offset``.

        *src* must already be defined (root or derived).
        """
        if src not in self._events:
            raise ValueError(
                f"ControlSignalGraph.relate_events: source event '{src}' "
                "not defined. Call define_event() first."
            )
        if dst in self._events:
            existing = self._events[dst]['abs_offset']
            expected = self._events[src]['abs_offset'] + offset
            if existing != expected:
                raise ValueError(
                    f"ControlSignalGraph: event '{dst}' timing conflict: "
                    f"existing={existing}, computed from '{src}' + {offset} = {expected}."
                )
            return  # already consistent
        self._events[dst] = {
            'abs_offset': self._events[src]['abs_offset'] + offset,
            'description': description,
            'is_root': False,
        }

    # ------------------------------------------------------------------
    # Signal API
    # ------------------------------------------------------------------

    def define_signal(self, name: str, *, event: str, offset: int = 0,
                      width: int = 1, wire: Optional[str] = None,
                      description: str = "") -> None:
        """
        Anchor *name* to *event* + *offset* clocks.

        ``abs_delay = event.abs_offset + offset``

        Parameters
        ----------
        wire : Verilog wire name (defaults to *name*).
        """
        if event not in self._events:
            raise ValueError(
                f"ControlSignalGraph.define_signal: event '{event}' not defined."
            )
        abs_delay = self._events[event]['abs_offset'] + offset
        if name in self._signals:
            if self._signals[name]['abs_delay'] != abs_delay:
                raise ValueError(
                    f"ControlSignalGraph: signal '{name}' timing conflict: "
                    f"existing={self._signals[name]['abs_delay']}, "
                    f"computed from event '{event}' + {offset} = {abs_delay}."
                )
            return
        self._signals[name] = {
            'event': event,
            'offset': offset,
            'abs_delay': abs_delay,
            'width': width,
            'wire': wire if wire is not None else name,
            'description': description,
        }

    def connect(
        self,
        src: str,
        dst: str,
        *,
        target_event: str,
        target_offset: int = 0,
        width: Optional[int] = None,
        src_wire: Optional[str] = None,
        dst_wire: Optional[str] = None,
        description: str = "",
    ) -> None:
        """
        Create delay chain *src* -> *dst* aligned to *target_event* + *target_offset*.

        ``dst.abs_delay = target_event.abs_offset + target_offset``
        ``latency = dst.abs_delay - src.abs_delay``

        Raises ValueError if latency < 0.
        """
        if src not in self._signals:
            raise ValueError(
                f"ControlSignalGraph.connect: source signal '{src}' not defined."
            )
        if target_event not in self._events:
            raise ValueError(
                f"ControlSignalGraph.connect: target event '{target_event}' not defined."
            )
        src_info = self._signals[src]
        dst_abs = self._events[target_event]['abs_offset'] + target_offset
        latency = dst_abs - src_info['abs_delay']

        if latency < 0:
            raise ValueError(
                f"ControlSignalGraph.connect: negative latency for "
                f"'{src}' (T={src_info['abs_delay']}) -> '{dst}' (T={dst_abs}): "
                f"latency={latency}. Source is already past target."
            )

        dst_width = width if width is not None else src_info['width']
        _src_wire = src_wire if src_wire is not None else src_info['wire']
        _dst_wire = dst_wire if dst_wire is not None else dst

        # Register destination signal
        if dst in self._signals:
            if self._signals[dst]['abs_delay'] != dst_abs:
                raise ValueError(
                    f"ControlSignalGraph: signal '{dst}' timing conflict: "
                    f"existing={self._signals[dst]['abs_delay']}, "
                    f"target={dst_abs}."
                )
        else:
            self._signals[dst] = {
                'event': target_event,
                'offset': target_offset,
                'abs_delay': dst_abs,
                'width': dst_width,
                'wire': _dst_wire,
                'description': description,
            }

        # Record delay chain entry (only if latency > 0)
        if latency > 0:
            self._edges.append({
                'src': _src_wire,
                'dst': _dst_wire,
                'delay': latency,
                'width': dst_width,
                'note': description or f"{src} -> {dst} (latency={latency})",
            })

    # ------------------------------------------------------------------
    # Alignment groups (for validation)
    # ------------------------------------------------------------------

    def add_alignment_group(self, group_name: str, signals: list) -> None:
        """Declare that all *signals* must have the same abs_delay."""
        self._alignment_groups[group_name] = list(signals)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def abs_delay_of(self, name: str) -> int:
        """Return the absolute pipeline position of signal *name*."""
        if name not in self._signals:
            raise ValueError(f"ControlSignalGraph: signal '{name}' not in graph.")
        return self._signals[name]['abs_delay']

    def delay_to_align(self, src: str, target: str) -> int:
        """Extra cycles to bring *src* to same absolute position as *target*."""
        for name in (src, target):
            if name not in self._signals:
                raise ValueError(f"ControlSignalGraph: signal '{name}' not in graph.")
        return self._signals[target]['abs_delay'] - self._signals[src]['abs_delay']

    def event_abs_offset(self, event_name: str) -> int:
        """Return the absolute offset of an event."""
        if event_name not in self._events:
            raise ValueError(f"ControlSignalGraph: event '{event_name}' not defined.")
        return self._events[event_name]['abs_offset']

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Run consistency assertions:
        1. All signals in each alignment group have the same abs_delay.
        2. All delay chain latencies are >= 0.
        3. All referenced events exist.
        """
        errors = []

        # Check alignment groups
        for group_name, sig_names in self._alignment_groups.items():
            delays = {}
            for s in sig_names:
                if s in self._signals:
                    delays[s] = self._signals[s]['abs_delay']
            if delays:
                expected = next(iter(delays.values()))
                for s, d in delays.items():
                    if d != expected:
                        errors.append(
                            f"Alignment group '{group_name}': signal '{s}' has "
                            f"abs_delay={d}, expected {expected} "
                            f"(from '{next(iter(delays))}')"
                        )

        # Check all edges have non-negative latency
        for edge in self._edges:
            if edge['delay'] < 0:
                errors.append(
                    f"Negative delay: {edge['src']} -> {edge['dst']} = {edge['delay']}"
                )

        if errors:
            raise ValueError(
                "ControlSignalGraph validation failed:\n  " +
                "\n  ".join(errors)
            )

    # ------------------------------------------------------------------
    # Delay table output
    # ------------------------------------------------------------------

    def build_delay_table(self) -> Dict[str, dict]:
        """
        Return the complete delay table for ModuleDelay instantiation.

        Only edges with latency > 0 are included.

        Returns
        -------
        dict  keyed by destination wire name:
            {
                'delay': int,   # N_CLK for ModuleDelay
                'width': int,   # DWT for ModuleDelay
                'src':   str,   # source Verilog wire name
                'dst':   str,   # destination Verilog wire name
                'note':  str,   # human-readable description
            }
        """
        return {
            edge['dst']: {
                'delay': edge['delay'],
                'width': edge['width'],
                'src':   edge['src'],
                'dst':   edge['dst'],
                'note':  edge['note'],
            }
            for edge in self._edges
        }


# =============================================================================
# Graph builder: LS control path
# =============================================================================

def build_ls_ctrl_graph(
    *,
    ls_timing: dict,
    counter_width: int,
    SRAM_ADDR_WIDTH: int,
    RB_PARALLELISM: int,
    freq_interp_method: str,
    max_occasions: int = 1,
    is_double_dmrs=False,
    has_pre_fi_buf: bool = False,
) -> ControlSignalGraph:
    """
    Build the LS-phase control signal dependency graph.

    Reference frame
    ---------------
    T=0 = ``rb_beat_start``: posedge where rb_counter=0 and
    ctrl_sym_switch=1 (first Y beat of a DMRS symbol).

    Event timeline::

        rb_beat_start (T=0)
          ctrl_rb_idx, ctrl_ls_en, ctrl_sym_switch, ctrl_is_pilot (comb, T=0)
        registered_update (T=1)
          ctrl_rb_idx_r, ctrl_first_rb, ctrl_last_rb,
          ctrl_pilot_wr_addr_raw, ctrl_occ_idx_raw (reg/comb, T=1)
        ls_data_out (T=LS_DRAIN)
          ctrl_pilot_wr_en_raw, ctrl_pilot_wr_addr,
          ctrl_first_rb_d, ctrl_last_rb_d, ctrl_occ_idx

    Parameters
    ----------
    ls_timing          : dict from ``analyze_ls_timing()``
    counter_width      : bit width of the RB counter
    SRAM_ADDR_WIDTH    : bit width of the pilot SRAM address
    RB_PARALLELISM     : input RB parallelism
    freq_interp_method : 'nn' / 'linear' / 'lmmse'
    max_occasions      : DMRS occasions (1 + max additional DMRS).
    is_double_dmrs     : False, True, or 'Hybrid' — controls l_prime gating.
    """
    g = ControlSignalGraph()
    if has_pre_fi_buf:
        LS_DRAIN = ls_timing['pre_fi_pipeline_depth']
    else:
        LS_DRAIN = ls_timing['total_pipeline_depth']
    N_CLK_FREQ = ls_timing['N_CLK_FREQ']

    OCC_SEL_WIDTH = max(math.ceil(math.log2(max_occasions)), 1) if max_occasions > 1 else 1

    # ---- Events ----
    g.define_event('rb_beat_start',
        description='posedge: rb_counter=0, ctrl_sym_switch=1')
    g.relate_events('rb_beat_start', 'registered_update', offset=1,
        description='Next posedge: ctrl_rb_idx_r, ctrl_sym_idx settle')
    g.relate_events('rb_beat_start', 'ls_data_out', offset=LS_DRAIN,
        description='LS pipeline output: FREQ_INTERP data valid')

    # ---- T=0 signals (combinational at rb_beat_start) ----
    g.define_signal('ctrl_rb_idx',      event='rb_beat_start', offset=0,
                    width=counter_width,
                    description='Raw RB counter (comb from rb_counter)')
    g.define_signal('ctrl_ls_en',       event='rb_beat_start', offset=0,
                    width=1,
                    description='LS enable: (S_RUN) & is_pilot (comb from FSM)')
    g.define_signal('ctrl_sym_switch',  event='rb_beat_start', offset=0,
                    width=1,
                    description='Symbol boundary strobe (reg, same posedge as rb=0)')

    # ---- T=0 boundary signals (from ctrl_rb_idx, combinational) ----
    # These use ctrl_rb_idx (T=0) not ctrl_rb_idx_r (T=1) to avoid stale
    # values on the first beat of each symbol where ctrl_rb_idx_r still
    # holds the last RB index from the previous symbol.
    g.define_signal('ctrl_first_rb',          event='rb_beat_start', offset=0,
                    width=1,
                    description='First-RB flag: (ctrl_rb_idx == 0) [comb from T=0 counter]')
    g.define_signal('ctrl_last_rb',           event='rb_beat_start', offset=0,
                    width=1,
                    description='Last-RB flag: (ctrl_rb_idx + PAR >= num_RBs) [comb from T=0 counter]')
    if RB_PARALLELISM > 1:
        g.define_signal('ctrl_lane_last_raw',  event='rb_beat_start', offset=0,
                        width=RB_PARALLELISM, wire='ctrl_lane_last_raw',
                        description='Per-lane logical-last-RB flags (beat_base + lane == num_RBs-1)')
    g.define_signal('ctrl_pilot_wr_addr_raw', event='rb_beat_start', offset=0,
                    width=SRAM_ADDR_WIDTH,
                    wire='ctrl_pilot_wr_addr_raw',
                    description='SRAM write address source (comb from ctrl_rb_idx, T=0)')

    # ---- T=1 signals (at registered_update) ----
    g.define_signal('ctrl_rb_idx_r',          event='registered_update', offset=0,
                    width=counter_width,
                    description='RB counter +1clk (Delay inside RB_COUNTER)')
    if max_occasions > 1:
        g.define_signal('ctrl_occ_idx_raw',   event='registered_update', offset=0,
                        width=OCC_SEL_WIDTH,
                        description='Occasion index register (updates on sym_switch & is_pilot)')

    # ---- Freq interp input event (only for post-FI buffering) ----
    # When pre-FI, FI runs during S_TI (not S_RUN), so no FI signals in this graph.
    if not has_pre_fi_buf:
        g.relate_events('rb_beat_start', 'freq_interp_input',
            offset=LS_DRAIN - N_CLK_FREQ,
            description='Data arrives at FREQ_INTERP input')

    # ---- Delay chains -> ls_data_out (T=LS_DRAIN) ----
    # Latency is auto-computed: target_abs - src.abs_delay

    _needs_dbl_gate = (is_double_dmrs is True or is_double_dmrs == 'Hybrid')
    g.connect('ctrl_ls_en', 'ctrl_pilot_wr_en',
        target_event='ls_data_out', target_offset=0,
        width=1, dst_wire='ctrl_pilot_wr_en_pre' if _needs_dbl_gate else 'ctrl_pilot_wr_en_raw',
        description='LS enable -> pilot SRAM write strobe')

    # Double-DMRS l_prime delay chain: suppress first-symbol write to PILOT_SRAM_BANK
    if _needs_dbl_gate:
        g.define_signal('ctrl_l_prime_int', event='rb_beat_start', offset=0,
                        width=1,
                        description='Double-DMRS second-symbol indicator (comb, T=0)')
        g.connect('ctrl_l_prime_int', 'ctrl_l_prime_d',
            target_event='ls_data_out', target_offset=0,
            width=1,
            description='l_prime delayed to align with LS pipeline output')

    g.connect('ctrl_pilot_wr_addr_raw', 'ctrl_pilot_wr_addr',
        target_event='ls_data_out', target_offset=0,
        width=SRAM_ADDR_WIDTH,
        description='SRAM write address aligned with LS data')

    # first_RB / last_RB: only needed during S_RUN for post-FI buffering
    # (FI core receives them at its data input). Pre-FI: FI runs in S_TI.
    # Only the NN and Linear cores consume the flags -- LMMSE handles slot edges
    # through its coefficient set -- so skip the delay chain entirely otherwise,
    # rather than building registers whose output nothing reads.
    if not has_pre_fi_buf and freq_interp_method in ('nn', 'linear'):
        g.connect('ctrl_first_rb', 'ctrl_first_rb_d',
            target_event='freq_interp_input', target_offset=0,
            width=1,
            description='First-RB flag at FREQ_INTERP input (core delays internally)')

        g.connect('ctrl_last_rb', 'ctrl_last_rb_d',
            target_event='freq_interp_input', target_offset=0,
            width=1,
            description='Last-RB flag at FREQ_INTERP input (core delays internally)')

        if RB_PARALLELISM > 1:
            g.connect('ctrl_lane_last_raw', 'ctrl_lane_last_d',
                target_event='freq_interp_input', target_offset=0,
                width=RB_PARALLELISM,
                src_wire='ctrl_lane_last_raw',
                description='Per-lane logical-last-RB flags at FREQ_INTERP input')

    if max_occasions > 1:
        g.connect('ctrl_occ_idx_raw', 'ctrl_occ_idx',
            target_event='ls_data_out', target_offset=0,
            width=OCC_SEL_WIDTH,
            description='Occasion index aligned with pilot SRAM write')

    if freq_interp_method == 'lmmse' and not has_pre_fi_buf:
        g.connect('ctrl_ls_en', 'ctrl_freq_interp_en',
            target_event='freq_interp_input', target_offset=0,
            width=1,
            description='LMMSE freq-interp accumulation enable')

    # ---- Alignment validation ----
    # ctrl_first_rb_d / ctrl_last_rb_d target freq_interp_input (consumed at
    # core input, not SRAM write domain), so they are NOT in this group.
    sram_write_signals = [
        'ctrl_pilot_wr_en', 'ctrl_pilot_wr_addr',
    ]
    if _needs_dbl_gate:
        sram_write_signals.append('ctrl_l_prime_d')
    if max_occasions > 1:
        sram_write_signals.append('ctrl_occ_idx')
    g.add_alignment_group('sram_write_domain', sram_write_signals)
    g.validate()

    return g


# =============================================================================
# Graph builder: LMMSE freq-interp core pipeline
# =============================================================================

def build_fi_core_graph(
    *,
    N_PILOTS_PER_RB: int,
    LMMSE_P: int,
    RB_PARALLELISM: int,
    H_DWT: int,
    COEFF_DWT: int,
    REAL_COEFF: bool = False,
    FI_RE_PARALLELISM: int = 12,
    has_pre_fi_buf: bool = False,
) -> tuple:
    """
    Build timing graph for the LMMSE CORE_LMMSE_INTERP internal pipeline.

    Returns ``(graph, info)`` where *info* is a dict with:

    - ``PIPE_DELAY``: multiplier pipeline depth (budget.pipeline_depth)
    - ``REG_COEFF``: whether coefficient ROM output is registered
    - ``FILL_BEATS``: total fill beats (FILL_BEATS_ORIG * OUTPUT_GROUPS)
    - ``FILL_BEATS_ORIG``: pilot accumulation beats per window
    - ``total_depth``: safe controller wait through the externally visible
      output register; ``PIPE_DELAY + 2`` for a one-beat direct path, otherwise
      ``FILL_BEATS + PIPE_DELAY + extra``
    - ``FILL_CNT_W``: bit width of fill counter
    """
    from delay_budget import COST_MUX, cost_mul
    from v_core_lmmse_interp import fi_lmmse_multiplier_latency

    MUL_LATENCY = fi_lmmse_multiplier_latency()

    FILL_BEATS_ORIG = max(LMMSE_P // max(RB_PARALLELISM, 1), 1)
    OUTPUT_GROUPS = 12 // FI_RE_PARALLELISM
    FILL_BEATS = FILL_BEATS_ORIG * OUTPUT_GROUPS
    N_PILOTS_PER_BEAT = N_PILOTS_PER_RB * min(RB_PARALLELISM, LMMSE_P)
    TREE_DEPTH = math.ceil(math.log2(max(N_PILOTS_PER_BEAT, 1))) if N_PILOTS_PER_BEAT > 1 else 0
    extra = 1 if FILL_BEATS > 1 else 0
    FILL_CNT_W = max(math.ceil(math.log2(FILL_BEATS)), 1)

    REG_POST_CMUL = not REAL_COEFF and MUL_LATENCY > 0 and TREE_DEPTH > 0

    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    if FILL_BEATS > 1:
        budget.add_comb(COST_MUX, tag="coeff_rom_mux")
    REG_COEFF = budget.need_register_before(cost_mul(H_DWT, COEFF_DWT))
    if has_pre_fi_buf:
        REG_COEFF = True
    if REG_COEFF:
        budget.flush(tag="coeff_register")
    budget.add_comb(cost_mul(H_DWT, COEFF_DWT), tag="multiplier")
    budget.add_register(MUL_LATENCY, tag="mul_pipe")
    if REG_POST_CMUL:
        budget.add_register(1, tag="post_cmul_reg")
        budget.add_register(TREE_DEPTH - 1, tag="adder_tree")
    else:
        budget.add_register(TREE_DEPTH, tag="adder_tree")

    PIPE_DELAY = budget.pipeline_depth

    # ---- Build graph ----
    g = ControlSignalGraph()

    g.define_event('fill_start',
        description='enable HIGH, fill_cnt=0')
    g.relate_events('fill_start', 'mul_output', offset=PIPE_DELAY,
        description='Multiplier/tree outputs valid')
    g.relate_events('fill_start', 'acc_snapshot', offset=PIPE_DELAY + 1,
        description='Accumulator snapshot into out_buf')

    g.define_signal('fill_cnt', event='fill_start', offset=0,
                    width=FILL_CNT_W,
                    description='Fill beat counter (0..FILL_BEATS-1)')

    if FILL_BEATS > 1:
        g.connect('fill_cnt', 'fill_cnt_d',
            target_event='mul_output', target_offset=0,
            width=FILL_CNT_W,
            description='fill_cnt delayed to MUL output (accumulator load/add select)')
        g.connect('fill_cnt', 'fill_cnt_dd',
            target_event='acc_snapshot', target_offset=0,
            width=FILL_CNT_W,
            description='fill_cnt delayed to acc_snapshot (acc_done detection)')

    if REG_COEFF:
        g.define_signal('enable_raw', event='fill_start', offset=0,
                        width=1, description='Core enable (raw)')
        g.relate_events('fill_start', 'coeff_registered', offset=1,
            description='Coefficient ROM registered output valid')
        g.connect('enable_raw', 'enable_gated',
            target_event='coeff_registered', target_offset=0,
            width=1,
            description='Enable delayed to match registered coefficient ROM')

    # A one-beat core has no accumulator/drain FSM, but its externally safe
    # result still crosses both the enable-gated input register and reg_out.
    # Keep this equal to the direct_valid delay emitted by
    # v_core_lmmse_interp; TI_CTRL must retain the current occasion tag until
    # that pulse has written TIME_INTERP.  The previous FILL_BEATS+PIPE_DELAY
    # estimate was one cycle short and rotated occasion banks whenever a
    # Hybrid port used a deeper (for example 12-input) adder tree alongside a
    # shorter static port.
    total_depth = (
        PIPE_DELAY + 2
        if FILL_BEATS == 1
        else FILL_BEATS + PIPE_DELAY + extra
    )

    info = {
        'PIPE_DELAY': PIPE_DELAY,
        'REG_COEFF': REG_COEFF,
        'FILL_BEATS': FILL_BEATS,
        'FILL_BEATS_ORIG': FILL_BEATS_ORIG,
        'OUTPUT_GROUPS': OUTPUT_GROUPS,
        'FILL_CNT_W': FILL_CNT_W,
        'total_depth': total_depth,
    }

    return g, info


# =============================================================================
# Graph builder: TI control path (reference T=0 = TI_CTRL begins sweep)
# =============================================================================

def build_ti_ctrl_graph(
    *,
    ti_pipeline_depth: int,
    SRAM_ADDR_WIDTH: int,
    RE_GROUP_WIDTH: int,
    has_pre_fi_buf: bool = False,
    N_BANKS: int = 1,
    BANK_SEL_W: int = 1,
) -> ControlSignalGraph:
    """
    Build the TI-phase control signal dependency graph.

    Reference frame: T=0 = first SRAM read strobe of the TI sweep.

    ``ctrl_ti_valid`` arrives VALID_DELAY = 1 + ti_pipeline_depth cycles
    after the SRAM read (1 cycle SRAM latency + core pipeline depth).

    When ``has_pre_fi_buf`` and ``N_BANKS > 1``, the graph also manages
    the occasion register bank-select delay (1 cycle to align with the
    registered read output).
    """
    g = ControlSignalGraph()
    VALID_DELAY = 1 + ti_pipeline_depth

    # ---- Events ----
    g.define_event('ti_read_start',
        description='First SRAM read strobe of TI sweep')
    g.relate_events('ti_read_start', 'occ_reg_output', offset=1,
        description='Registered SRAM/occasion-register read output valid')
    g.relate_events('ti_read_start', 'ti_output_valid', offset=VALID_DELAY,
        description='TI output valid (1 SRAM latency + core pipeline)')

    # ---- T=0 anchor signals ----
    g.define_signal('ctrl_ti_sram_rd_en', event='ti_read_start', offset=0,
                    width=1, description='TI SRAM read strobe')
    g.define_signal('ctrl_ti_rb_addr',    event='ti_read_start', offset=0,
                    width=SRAM_ADDR_WIDTH, description='TI SRAM RB beat address')
    g.define_signal('ctrl_ti_re_group',   event='ti_read_start', offset=0,
                    width=RE_GROUP_WIDTH, description='TI RE group index')

    # ---- Valid output domain ----
    g.define_signal('ctrl_ti_valid',      event='ti_output_valid', offset=0,
                    width=1, description='TI output valid')

    # ---- Pre-FI occasion register bank-select alignment ----
    if has_pre_fi_buf and N_BANKS > 1:
        g.define_signal('occ_bank_sel_raw', event='ti_read_start', offset=0,
                        width=BANK_SEL_W,
                        description='Occasion register bank selector (comb from re_group/rb_within)')
        g.connect('occ_bank_sel_raw', 'occ_bank_sel',
            target_event='occ_reg_output', target_offset=0,
            width=BANK_SEL_W,
            description='Bank selector aligned with registered occasion read output')

    return g




def analyze_cinit_timing(
    *,
    min_num_RBs: int,
    RB_PARALLELISM: int,
    is_ECP,                       # True, False, or 'Hybrid'
    N_CLK_CINIT: int,
) -> dict:
    """
    C_INIT Generation timing check.

    With the bypass approach c_init values are computed on-the-fly each
    symbol.  The constraint is simply:

        sym_duration_min  >=  D_intrinsic

    where D_intrinsic is the pipeline depth of C_INIT_GENERATION and
    sym_duration_min = ceil(min_num_RBs / RB_PARALLELISM).

    Pipeline depth model:
    | stage | process                               | clk |
    | 1     | ECP/NCP select + add path          | auto |
    | 2     | add + pipe                         | 1+ |
    | 3     | mul + 2 regs                       | 3 |
    | 4     | output reg                         | N_CLK_CINIT |
    """
    # --- Step 1: Compute intrinsic pipeline depth D ---
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)

    # Stage 1: is_ECP=True → 1 adder; is_ECP=False → 2 adders; "Hybrid" → 2 adders + mux + 1 reg
    if is_ECP == "Hybrid":
        budget.add_comb(2 * COST_ADDER_8B, tag="stage1_hybrid")
        budget.add_register(1, tag="stage1_hybrid_mux_reg")
    elif is_ECP == True:
        budget.add_comb(COST_ADDER_8B, tag="stage1_ecp")
    else:
        budget.add_comb(2 * COST_ADDER_8B, tag="stage1_ncp")

    # Stage 2: 1 adder + explicit pipeline register
    budget.add_comb(COST_ADDER_8B, tag="stage2_add")
    budget.flush(tag="stage2_pipe")

    # Stage 3: multiplier (cost=3) + 2 pipeline registers
    budget.add_comb(COST_MUL_8B, tag="stage3_mul")
    budget.add_register(2, tag="stage3_mul_pipe")

    # Stage 4: output register
    budget.add_register(N_CLK_CINIT, tag="stage4_output_reg")

    D_intrinsic = budget.pipeline_depth

    # --- Step 2: Bypass feasibility ---
    sym_duration_min = math.ceil(min_num_RBs / RB_PARALLELISM)
    bypass_feasible = sym_duration_min >= D_intrinsic

    return {
        'D_intrinsic': D_intrinsic,
        'sym_duration_min': sym_duration_min,
        'bypass_feasible': bypass_feasible,
    }


def analyze_interp_timing(
    *,
    freq_interp_method: str,
    time_interp_method: str,
    Qu_H_DWT: int,
    additional_DMRS_range: List[int],
    FI_LMMSE_COEFF_DWT: int = 12,
    FI_LMMSE_P: int = 4,
    FI_RB_PARALLELISM: int = 1,
    FI_LMMSE_REAL_COEFF: bool = False,
    FI_RE_PARALLELISM: int = 12,
    has_pre_fi_buf: bool = False,
) -> dict:
    """
    Interpolation pipeline depth summary.

    Timing model:
    | path | depth source |
    | freq | nn / linear / lmmse exported depth |
    | time | nn / linear / lmmse exported depth |
    """
    from v_core_lmmse_interp import _pipeline_depth_lmmse_freq

    # Frequency interpolation depth
    if freq_interp_method == 'nn':
        freq_depth = nn_freq_pipeline_depth()
    elif freq_interp_method == 'linear':
        freq_depth = lin_freq_pipeline_depth(Qu_H_DWT)
    elif freq_interp_method == 'lmmse':
        freq_depth = _pipeline_depth_lmmse_freq(
            N_PILOTS_PER_RB=6,
            LMMSE_P=FI_LMMSE_P, RB_PARALLELISM=FI_RB_PARALLELISM,
            H_DWT=Qu_H_DWT, COEFF_DWT=FI_LMMSE_COEFF_DWT,
            REAL_COEFF=FI_LMMSE_REAL_COEFF,
            FI_RE_PARALLELISM=FI_RE_PARALLELISM,
            has_pre_fi_buf=has_pre_fi_buf,
        )
    else:
        freq_depth = 1

    # Time interpolation depth
    max_occ = 1 + max(additional_DMRS_range)
    if time_interp_method == 'nn':
        ti_depth = time_nn_pipeline_depth()
    elif time_interp_method == 'linear':
        ti_depth = time_lin_pipeline_depth()
    elif time_interp_method == 'lmmse':
        ti_depth = time_lmmse_pipeline_depth(max_occ)
    else:
        ti_depth = 1

    return {
        'freq_method': freq_interp_method,
        'freq_depth': freq_depth,
        'time_method': time_interp_method,
        'time_depth': ti_depth,
        'max_occasions': max_occ,
    }


# =============================================================================
# Helper: LS Pipeline Timing Analysis (auto-compute N_CLK_* values)
# =============================================================================

def analyze_ls_timing(
    *,
    Qu_Y: QuType,
    QU_H_LS: QuType,
    MAX_CDM_GROUPS: int,
    DMRS_PARALLELISM: int,
    dmrs_Type,
    is_double_dmrs,
    cdm_group_configs: List[dict],
    RB_PARALLELISM: int,
    freq_interp_method: str,
    Qu_H_DWT: int,
    additional_DMRS_range: List[int],
    LMMSE_P: int = 4,
    COEFF_DWT_LMMSE: int = 12,
    REAL_COEFF_LMMSE: bool = False,
    FI_RE_PARALLELISM: int = 12,
) -> dict:
    """
    LS timing budget and drain analysis.

    Timing model:
    | path A | Y_PRE ------------------------- |
    | path B | DMRS_SEQ -> OCC -------------- |
    | merge  | path A == path B at LS_ROT in |
    | tail   | LS_ROT -> AVERAGING -> FREQ   |

    Alignment rule:
    | N_CLK_Y_PRE == N_CLK_DMRS_SEQ + N_CLK_OCC |

    Drain rule:
    | LS_DRAIN = N_CLK_Y_PRE + N_CLK_LS_ROT + N_CLK_AVG + N_CLK_FREQ |
    """

    # ---- Stage min depths ----
    min_y_pre = y_pre_pipeline_depth(Qu_Y, QU_H_LS, MAX_CDM_GROUPS)
    min_dmrs_seq = 1
    min_occ = occ_pipeline_depth(is_double_dmrs)
    min_ls_rot = ls_rot_pipeline_depth(QU_H_LS)

    # ---- Align parallel Y and DMRS paths ----
    # Constraint: N_CLK_Y_PRE == N_CLK_DMRS_SEQ + N_CLK_OCC
    min_dmrs_path = min_dmrs_seq + min_occ
    if min_y_pre >= min_dmrs_path:
        N_CLK_Y_PRE = min_y_pre
        N_CLK_DMRS_SEQ = min_y_pre - min_occ
    else:
        N_CLK_DMRS_SEQ = min_dmrs_seq
        N_CLK_Y_PRE = min_dmrs_seq + min_occ
    N_CLK_OCC = min_occ

    N_CLK_LS_ROT = min_ls_rot

    # ---- Worst-case AVERAGING depth across all CDM groups ----
    N_CLK_AVG = 0
    avg_details = []
    for cfg in cdm_group_configs:
        depth = averaging_pipeline_depth(
            Qu_IN_DWT=QU_H_LS.DWT,
            dmrs_Type=cfg['avg_dmrs_type'],
            cdm_group=cfg['group_idx'],
            fdCDM=cfg['fdCDM'],
            tdCDM=cfg['tdCDM'],
            RB_PARALLELISM=RB_PARALLELISM,
        )
        avg_details.append({'group_idx': cfg['group_idx'], 'depth': depth})
        N_CLK_AVG = max(N_CLK_AVG, depth)
    if N_CLK_AVG == 0:
        N_CLK_AVG = 1  # at least 1 clock for output register

    # ---- Frequency interpolation depth ----
    if freq_interp_method == 'nn':
        N_CLK_FREQ = nn_freq_pipeline_depth()
    elif freq_interp_method == 'linear':
        N_CLK_FREQ = lin_freq_pipeline_depth(Qu_H_DWT)
    elif freq_interp_method == 'lmmse':
        from v_core_lmmse_interp import _pipeline_depth_lmmse_freq
        _n_pilots_per_rb = 6 if dmrs_Type in (1, 'Hybrid') else 4
        N_CLK_FREQ = _pipeline_depth_lmmse_freq(
            N_PILOTS_PER_RB=_n_pilots_per_rb,
            LMMSE_P=LMMSE_P,
            RB_PARALLELISM=RB_PARALLELISM,
            H_DWT=QU_H_LS.DWT,
            COEFF_DWT=COEFF_DWT_LMMSE,
            REAL_COEFF=REAL_COEFF_LMMSE,
            FI_RE_PARALLELISM=FI_RE_PARALLELISM,
        )
    else:
        N_CLK_FREQ = 1

    # ---- Total LS drain latency ----
    total_pipeline_depth = N_CLK_Y_PRE + N_CLK_LS_ROT + N_CLK_AVG + N_CLK_FREQ
    pre_fi_pipeline_depth = N_CLK_Y_PRE + N_CLK_LS_ROT + N_CLK_AVG

    return {
        'N_CLK_Y_PRE': N_CLK_Y_PRE,
        'N_CLK_DMRS_SEQ': N_CLK_DMRS_SEQ,
        'N_CLK_OCC': N_CLK_OCC,
        'N_CLK_LS_ROT': N_CLK_LS_ROT,
        'N_CLK_AVG': N_CLK_AVG,
        'N_CLK_FREQ': N_CLK_FREQ,
        'total_pipeline_depth': total_pipeline_depth,
        'pre_fi_pipeline_depth': pre_fi_pipeline_depth,
        'alignment': {
            'y_pre_min': min_y_pre,
            'dmrs_seq_min': min_dmrs_seq,
            'occ_min': min_occ,
            'dmrs_path_min': min_dmrs_path,
            'y_pre_padded': N_CLK_Y_PRE > min_y_pre,
            'dmrs_seq_padded': N_CLK_DMRS_SEQ > min_dmrs_seq,
        },
        'avg_details': avg_details,
    }


# =============================================================================
# Control Signal Delay Table
# =============================================================================

def build_ctrl_signal_delay_table(
    *,
    ls_timing: dict,
    SRAM_ADDR_WIDTH: int,
) -> Dict[str, dict]:
    """
    Build control signal delay table for TOP-level pipeline alignment.

    Signals derived from ``current_RB_idx`` (which tracks the *input* RB)
    must be delayed by ``LS_DRAIN_CYCLES`` to align with the LS pipeline
    output (AVERAGING -> FREQ_INTERP -> PILOT_SRAM write).

    Returns
    -------
    dict mapping signal name -> {
        'delay': required delay clocks,
        'width': signal bit-width,
        'src':   undelayed source wire name,
        'dst':   delayed destination wire name,
        'note':  human-readable description,
    }
    """
    LS_DRAIN = ls_timing['total_pipeline_depth']

    return {
        'first_RB': {
            'delay': LS_DRAIN,
            'width': 1,
            'src': 'first_RB',
            'dst': 'first_RB_delayed',
            'note': 'RB boundary indicator for FREQ_INTERP left edge',
        },
        'last_RB': {
            'delay': LS_DRAIN,
            'width': 1,
            'src': 'last_RB',
            'dst': 'last_RB_delayed',
            'note': 'RB boundary indicator for FREQ_INTERP right edge',
        },
        'pilot_wr_addr': {
            'delay': LS_DRAIN,
            'width': SRAM_ADDR_WIDTH,
            'src': 'pilot_wr_addr_raw',
            'dst': 'pilot_wr_addr',
            'note': 'Pilot SRAM write address aligned with pilot_wr_en',
        },
    }
