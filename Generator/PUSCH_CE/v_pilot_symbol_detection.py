from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from typing import Literal, List
import sys
from os.path import dirname
sys.path.append(dirname(__file__))
import math


# =============================================================================
# Static lookup table for DMRS symbol positions
# per TS 38.211 Tables 6.4.1.1.3-3 (single) / 6.4.1.1.3-4 (double)
# =============================================================================
# Key: (mapping_type, symbol_type, n_additional_dmrs)
# Value: list of (duration_range, position_pattern) tuples
# Position 0 in the pattern is a placeholder for l0 (front-loaded DMRS position)
DMRS_POSITION_MAP: dict[tuple[str, str, int], list[tuple[range, list[int]]]] = {
    # ========================================================================
    # Single-symbol Type A (TS 38.211 Table 6.4.1.1.3-3)
    # ========================================================================
    ('A', 'single', 0): [
        (range(4, 15), [0])  # All durations: l0 only
    ],
    ('A', 'single', 1): [
        (range(4, 8), [0]),        # Duration 4-7: l0
        (range(8, 10), [0, 7]),    # Duration 8-9: l0, 7
        (range(10, 13), [0, 9]),   # Duration 10-12: l0, 9
        (range(13, 15), [0, 11])   # Duration 13-14: l0, 11
    ],
    ('A', 'single', 2): [
        (range(4, 8), [0]),           # Duration 4-7: l0
        (range(8, 10), [0, 7]),       # Duration 8-9: l0, 7
        (range(10, 13), [0, 6, 9]),   # Duration 10-12: l0, 6, 9
        (range(13, 15), [0, 7, 11])   # Duration 13-14: l0, 7, 11
    ],
    ('A', 'single', 3): [
        (range(4, 8), [0]),             # Duration 4-7: l0
        (range(8, 10), [0, 7]),         # Duration 8-9: l0, 7
        (range(10, 12), [0, 6, 9]),     # Duration 10-11: l0, 6, 9
        (range(12, 15), [0, 5, 8, 11])  # Duration 12-14: l0, 5, 8, 11
    ],

    # ========================================================================
    # Double-symbol Type A (TS 38.211 Table 6.4.1.1.3-4)
    # ========================================================================
    ('A', 'double', 0): [
        (range(4, 15), [0])  # All durations: l0 only (double-symbol)
    ],
    ('A', 'double', 1): [
        (range(4, 10), [0]),        # Duration 4-9: l0
        (range(10, 13), [0, 8]),    # Duration 10-12: l0, 8
        (range(13, 15), [0, 10])    # Duration 13-14: l0, 10
    ],
    # Note: n_additional >= 2 not supported for double-symbol Type A
}


# =============================================================================
# Python helper: build bitmasks from the lookup table
# =============================================================================

def _resolve_positions(positions_raw: list[int], l0: int, is_double: bool) -> tuple[int, int, int]:
    """
    Given a raw position list (with 0 = l0 placeholder) and the actual l0 value,
    compute three 14-bit bitmasks:
      - pilot_mask:      bit[i] = 1 if symbol i is a DMRS pilot
      - l_quote_mask:    bit[i] = 1 if symbol i is the *second* symbol of a
                         double-DMRS pair (l' = 1)
      - last_dmrs_mask:  bit[i] = 1 if symbol i belongs to the *last* DMRS
                         occasion in this slot

    For single-symbol DMRS, each position occupies 1 symbol.
    For double-symbol DMRS, each position occupies 2 consecutive symbols
    (pos, pos+1).  The second symbol of each pair has l'=1.
    """
    pilot_mask = 0
    l_quote_mask = 0
    last_dmrs_mask = 0
    max_actual = -1
    for p in positions_raw:
        actual = l0 if p == 0 else p
        if actual < 14:
            pilot_mask |= (1 << actual)
            if actual > max_actual:
                max_actual = actual
        if is_double:
            second = actual + 1
            if second < 14:
                pilot_mask |= (1 << second)
                l_quote_mask |= (1 << second)
    # Mark last DMRS occasion symbols
    # For double DMRS, only mark the l'=1 (second) symbol of the last pair.
    # Marking l'=0 would trigger FSM drain before the second symbol is processed.
    if max_actual >= 0:
        if is_double and max_actual + 1 < 14:
            last_dmrs_mask |= (1 << (max_actual + 1))
        else:
            last_dmrs_mask |= (1 << max_actual)
    return pilot_mask, l_quote_mask, last_dmrs_mask


def build_bitmask_table(
    l0: int,
    is_double: bool,
    additional_DMRS_range: list[int],
    num_symbols_range: list[int],
) -> dict[tuple[int, int], tuple[int, int, int]]:
    """
    Build a dict mapping (n_additional, duration) -> (pilot_mask_14b, l_quote_mask_14b, last_dmrs_mask_14b).
    Only entries for supported durations and additional DMRS counts are generated.
    """
    symbol_type = 'double' if is_double else 'single'
    table: dict[tuple[int, int], tuple[int, int, int]] = {}

    for n_add in additional_DMRS_range:
        key = ('A', symbol_type, n_add)
        entries = DMRS_POSITION_MAP.get(key, [])
        for dur in num_symbols_range:
            # Find matching range
            for dur_range, pos_list in entries:
                if dur in dur_range:
                    pm, lm, ldm = _resolve_positions(pos_list, l0, is_double)
                    table[(n_add, dur)] = (pm, lm, ldm)
                    break
            else:
                # No matching entry -> only front-loaded DMRS
                pm, lm, ldm = _resolve_positions([0], l0, is_double)
                table[(n_add, dur)] = (pm, lm, ldm)
    return table


def _format_mask(val: int) -> str:
    """Format a 14-bit value as Verilog binary literal body (no width prefix)."""
    return f"{val:014b}"

# NOTE: Review has been done
@convert
def ModulePILOT_SYMBOL_DETECTION(max_pusch_symbols: int, dmrs_typeA_pos: str, is_double_dmrs: bool | Literal["Hybrid"], additional_DMRS_range: List[int], num_symbols_range: List[int]) -> None:
    """
    Pilot Symbol Detection -- combinational bitmask LUT.
    Latency = 0 clocks

    Uses pre-computed 14-bit bitmasks indexed by ``pusch_symbol_length``
    and ``n_additional_dmrs`` to detect all DMRS pilot symbol positions
    (front-loaded + additional) for PUSCH Mapping Type A.

    At elaboration time, the Python layer resolves the TS 38.211
    Tables 6.4.1.1.3-3/4 into per-configuration bitmasks.  At runtime
    a pair of nested ``case`` statements selects the correct bitmask,
    and ``current_symbol_idx`` simply indexes into it.

    Output signals:

      - ``is_pilot_symbol``: 1 when ``current_symbol_idx`` matches any
        DMRS symbol position (front-loaded or additional, first or second
        of a double-DMRS pair).
      - ``l_quote``: 1 for the second symbol of each double-DMRS pair,
        0 otherwise.  Only meaningful when ``is_pilot_symbol`` = 1.

    When ``dmrs_typeA_pos`` = "Hybrid", a runtime 1-bit ``dmrs_typeA_pos_sel``
    input selects between pos2 (sel=0) and pos3 (sel=1).

    When ``is_double_dmrs`` = "Hybrid", a runtime 1-bit ``is_double_dmrs``
    input selects between the single-symbol and double-symbol tables.

    :param max_pusch_symbols: 14
        Maximum PUSCH symbols per slot (determines symbol index bit width).
    :type max_pusch_symbols: int
    :param dmrs_typeA_pos: 'pos2'
        Front-loaded DMRS Type A position. 'pos2', 'pos3', or "Hybrid".
    :type dmrs_typeA_pos: str
    :param is_double_dmrs: "Hybrid"
        Double-symbol DMRS mode. True, False, or "Hybrid".
    :type is_double_dmrs: bool | Literal["Hybrid"]
    :param additional_DMRS_range: [0,1,2,3]
        Supported n_additional_dmrs values.
    :type additional_DMRS_range: List[int]
    :param num_symbols_range: [4,5,6,7,8,9,10,11,12,13,14]
        Supported PUSCH durations (pusch_symbol_length values).
    :type num_symbols_range: List[int]
    """
    if max_pusch_symbols <= 0:
        raise ValueError("max_pusch_symbols must be positive")
    if dmrs_typeA_pos not in ('pos2', 'pos3', 'Hybrid'):
        raise ValueError(f"Invalid dmrs_typeA_pos: {dmrs_typeA_pos}")

    symbol_width = math.ceil(math.log2(max_pusch_symbols)) if max_pusch_symbols > 1 else 1
    duration_width = symbol_width  # pusch_symbol_length shares the same bit width
    n_add_max = max(additional_DMRS_range)
    n_add_width = math.ceil(math.log2(n_add_max + 1)) if n_add_max > 0 else 1

    needs_typeA_pos_sel = (dmrs_typeA_pos == "Hybrid")
    needs_double_dmrs_sel = (is_double_dmrs == "Hybrid")
    needs_n_additional = (len(additional_DMRS_range) > 1)

    # ========================================================================
    # Pre-compute bitmask tables at elaboration time
    # ========================================================================
    if dmrs_typeA_pos == "Hybrid":
        l0_options = [2, 3]  # pos2 -> l0=2, pos3 -> l0=3
    elif dmrs_typeA_pos == 'pos2':
        l0_options = [2]
    else:
        l0_options = [3]

    if is_double_dmrs == "Hybrid":
        double_options = [False, True]
    elif is_double_dmrs:
        double_options = [True]
    else:
        double_options = [False]

    # bitmask_tables[l0][is_double][(n_add, dur)] = (pilot_mask, l_quote_mask, last_dmrs_mask)
    bitmask_tables: dict[int, dict[bool, dict[tuple[int, int], tuple[int, int, int]]]] = {}
    for l0 in l0_options:
        bitmask_tables[l0] = {}
        for is_dbl in double_options:
            bitmask_tables[l0][is_dbl] = build_bitmask_table(
                l0, is_dbl, additional_DMRS_range, num_symbols_range
            )

    # ========================================================================
    # Module port declaration
    # ========================================================================
    #/ `timescale 1ns / 1ps
    #/ module PILOT_SYMBOL_DETECTION(
    #/     input [`symbol_width`-1:0]   ctrl_sym_idx,
    #/     input [`symbol_width`-1:0]   ctrl_sym_idx_next,
    #/     input                        ctrl_sym_switch,
    #/     input [`duration_width`-1:0] pusch_symbol_length,

    if needs_n_additional:
        #/ input [`n_add_width`-1:0] n_additional_dmrs,
        pass

    if needs_typeA_pos_sel:
        #/ input dmrs_typeA_pos_sel,
        pass

    if needs_double_dmrs_sel:
        #/ input is_double_dmrs,
        pass

    #/ output ctrl_is_pilot,
    #/ output ctrl_l_prime,
    #/ output ctrl_is_last_dmrs
    #/ );

    # ========================================================================
    # Bitmask selection logic
    # ========================================================================
    # Strategy:
    #   Outermost: dmrs_typeA_pos_sel (if Hybrid) -- selects l0
    #   Next: is_double_dmrs (if Hybrid) -- selects single/double table
    #   Inner: n_additional_dmrs x pusch_symbol_length -> 14-bit bitmask
    #
    #   is_pilot_symbol = pilot_mask[current_symbol_idx]
    #   l_quote         = l_quote_mask[current_symbol_idx]

    # ------------------------------------------------------------------
    # Detect compile-time constant masks (no runtime selectors at all).
    # When masks are constant, use wire assignments instead of
    # reg + always @(*) to avoid Verilator's empty-sensitivity issue.
    # ------------------------------------------------------------------
    _masks_are_constant = False
    if (not needs_typeA_pos_sel and not needs_double_dmrs_sel
            and not needs_n_additional):
        _l0_chk = l0_options[0]
        _dbl_chk = double_options[0]
        _tbl_chk = bitmask_tables[_l0_chk][_dbl_chk]
        # Check ALL entries across all n_additional values and durations
        _all_masks = set(_tbl_chk.values())
        if len(_all_masks) == 1:
            _masks_are_constant = True
            _const_pm, _const_lm, _const_ldm = _all_masks.pop()

    if _masks_are_constant:
        # Pure compile-time constants → wire declarations (no always block)
        PM_STR = _format_mask(_const_pm)
        LM_STR = _format_mask(_const_lm)
        LDM_STR = _format_mask(_const_ldm)
        #/ wire [13:0] pilot_mask = 14'b`PM_STR`;
        #/ wire [13:0] l_quote_mask = 14'b`LM_STR`;
        #/ wire [13:0] last_dmrs_mask = 14'b`LDM_STR`;
        pass
    else:
        #/ reg [13:0] pilot_mask;
        #/ reg [13:0] l_quote_mask;
        #/ reg [13:0] last_dmrs_mask;
        pass

    # ------------------------------------------------------------------
    # Helper: emit case body for one (l0, is_double) table
    # ------------------------------------------------------------------
    def _emit_duration_case(tbl: dict[tuple[int, int], tuple[int, int, int]],
                            n_add_val: int) -> None:
        """Emit case(pusch_symbol_length) for a single n_additional value."""
        entries = {dur: masks for (na, dur), masks in tbl.items() if na == n_add_val}
        unique_masks = set(entries.values())
        if len(unique_masks) == 1:
            pm, lm, ldm = unique_masks.pop()
            PM_STR = _format_mask(pm)
            LM_STR = _format_mask(lm)
            LDM_STR = _format_mask(ldm)
            #/ pilot_mask     = 14'b`PM_STR`;
            #/ l_quote_mask   = 14'b`LM_STR`;
            #/ last_dmrs_mask = 14'b`LDM_STR`;
            pass
        else:
            #/ case (pusch_symbol_length)
            pass
            for dur in num_symbols_range:
                if dur in entries:
                    pm, lm, ldm = entries[dur]
                    DUR = dur
                    PM_STR = _format_mask(pm)
                    LM_STR = _format_mask(lm)
                    LDM_STR = _format_mask(ldm)
                    #/ `duration_width`'d`DUR`: begin pilot_mask = 14'b`PM_STR`; l_quote_mask = 14'b`LM_STR`; last_dmrs_mask = 14'b`LDM_STR`; end
                    pass
            #/ default: begin pilot_mask = 14'b0; l_quote_mask = 14'b0; last_dmrs_mask = 14'b0; end
            #/ endcase
            pass

    def _emit_inner_logic(tbl: dict[tuple[int, int], tuple[int, int, int]]) -> None:
        """Emit the n_additional_dmrs x pusch_symbol_length selection for one table."""
        if needs_n_additional:
            #/ case (n_additional_dmrs)
            pass
            for n_add in additional_DMRS_range:
                NA = n_add
                #/ `n_add_width`'d`NA`: begin
                pass
                _emit_duration_case(tbl, n_add)
                #/ end
                pass
            #/ default: begin pilot_mask = 14'b0; l_quote_mask = 14'b0; last_dmrs_mask = 14'b0; end
            #/ endcase
            pass
        else:
            _emit_duration_case(tbl, additional_DMRS_range[0])

    # ---- Main always block (only when masks need runtime selection) ----
    if not _masks_are_constant:
        #/ always @(*) begin
        pass

        if not needs_typeA_pos_sel and not needs_double_dmrs_sel:
            # Single l0, single symbol_type
            l0 = l0_options[0]
            dbl = double_options[0]
            _emit_inner_logic(bitmask_tables[l0][dbl])

        elif needs_typeA_pos_sel and not needs_double_dmrs_sel:
            dbl = double_options[0]
            #/ case (dmrs_typeA_pos_sel)
            pass
            for sel_val, l0 in enumerate([2, 3]):
                SEL = sel_val
                #/ // TypeA_pos = `SEL`
                #/ 1'd`SEL`: begin
                pass
                _emit_inner_logic(bitmask_tables[l0][dbl])
                #/ end
                pass
            #/ endcase
            pass

        elif not needs_typeA_pos_sel and needs_double_dmrs_sel:
            l0 = l0_options[0]
            #/ case (is_double_dmrs)
            pass
            for dbl_val, is_dbl in [(0, False), (1, True)]:
                DBL = dbl_val
                #/ // is_double_dmrs = `DBL`
                #/ 1'd`DBL`: begin
                pass
                _emit_inner_logic(bitmask_tables[l0][is_dbl])
                #/ end
                pass
            #/ endcase
            pass

        else:
            # Both Hybrid
            #/ case (dmrs_typeA_pos_sel)
            pass
            for sel_val, l0 in enumerate([2, 3]):
                SEL = sel_val
                #/ 1'd`SEL`: begin
                #/     case (is_double_dmrs)
                pass
                for dbl_val, is_dbl in [(0, False), (1, True)]:
                    DBL = dbl_val
                    #/ 1'd`DBL`: begin
                    pass
                    _emit_inner_logic(bitmask_tables[l0][is_dbl])
                    #/ end
                    pass
                #/ endcase
                #/ end
                pass
            #/ endcase
            pass

        #/ end
        pass

    # ========================================================================
    # Output: index into the selected bitmask
    # ========================================================================
    #/ // Use ctrl_sym_idx_next on ctrl_sym_switch to eliminate 1-clock pilot detection delay
    #/ wire [`symbol_width`-1:0] effective_symbol_idx = ctrl_sym_switch ? ctrl_sym_idx_next : ctrl_sym_idx;
    #/ assign ctrl_is_pilot     = pilot_mask[effective_symbol_idx];
    #/ assign ctrl_l_prime      = l_quote_mask[effective_symbol_idx];
    #/ assign ctrl_is_last_dmrs = last_dmrs_mask[effective_symbol_idx];

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    ModulePILOT_SYMBOL_DETECTION(
        max_pusch_symbols=14,
        dmrs_typeA_pos='pos2',
        is_double_dmrs=False,
        additional_DMRS_range=[0],
        num_symbols_range=list(range(4, 15)),
    )
