from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

from typing import Literal, Any, List

import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from basic_modules import ModuleDelay
from delay_budget import DelayBudget, cost_adder, COST_MUX, DEFAULT_BUDGET


def occ_pipeline_depth(is_double_dmrs: bool | str = False) -> int:
    """Minimum pipeline depth for OCC (callable without instantiation).

    OCC is purely combinational (2-bit XOR + QPSK MUX, negligible cost).
    If is_double_dmrs is Hybrid, a runtime MUX selects w_t.
    Returns 1 (output register only).
    """
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    if is_double_dmrs == "Hybrid":
        budget.add_comb(COST_MUX, tag="hybrid_wt_mux")
    return max(budget.pipeline_depth + 1, 1)


def port_needs_time_flip(port: int, dmrs_type: int) -> int:
    """Return 1 if `port` takes the -1 branch of the time-domain OCC, else 0.

    Type 1: drawer split on bit 2  →  ports 4-7, 12-15 flip.
    Type 2: drawer split on (port // 6) % 2  →  ports 6-11, 18-23 flip.
    Type 3 is passed in as dmrs_type=2 by the PCDMU layer: its drawer split
    (port % 12) >= 6 is identical to Type 2's for ports 0-23.
    """
    return ((port >> 2) & 1) if dmrs_type == 1 else ((port // 6) % 2)


def occ_needs_l_quote(
    antenna_ports: List[int],
    dmrs_Type: int | Literal["Hybrid"],
    is_double_dmrs,
) -> bool:
    """Whether an OCC instance for these ports declares the `l_quote` input.

    If no port in the instance flips, every w_t is the constant 1'b0 and
    l_quote would dangle. Both ModuleOCC and its parent must agree on this,
    so the predicate lives here rather than being duplicated at each site.
    """
    if not (is_double_dmrs == True or is_double_dmrs == "Hybrid"):
        return False
    if dmrs_Type == "Hybrid":
        return any(
            port_needs_time_flip(p, 1) or port_needs_time_flip(p, 2)
            for p in antenna_ports
        )
    return any(port_needs_time_flip(p, dmrs_Type) for p in antenna_ports)


def occ_needs_dmrs_type(
    antenna_ports: List[int],
    dmrs_Type: int | Literal["Hybrid"],
    is_double_dmrs,
) -> bool:
    """Whether Hybrid OCC needs its runtime DMRS drawer selector."""
    if dmrs_Type != "Hybrid" or not (
        is_double_dmrs is True or is_double_dmrs == "Hybrid"
    ):
        return False
    return any(
        port_needs_time_flip(p, 1) != port_needs_time_flip(p, 2)
        for p in antenna_ports
    )


@convert
def ModuleOCC(N_CLK: int, dmrs_Type: int | Literal["Hybrid"], is_double_dmrs: bool | Literal["Hybrid"], antenna_ports: List[int]) -> None:
    """
    Orthogonal Cover Code (OCC) processing module for DMRS pilot generation.

    This module applies the Whittle factor w_f × (-1)^w_t to the input DMRS
    base sequence via multiplier-free QPSK complex multiplication. The
    frequency-domain factor w_f is pre-calculated by W_F_CALC (power-of-j
    encoding) and passed as input; w_t is derived internally for time-domain
    orthogonalization across double-symbol DMRS occasions.

    **Architecture Note**:
    This module is instantiated per PCDMU (Physical CDM Unit). Fixed-type
    PCDMUs elaborate a static drawer rule; Hybrid PCDMUs use the runtime DMRS
    type only when a configured port's Type-1 and Type-2 drawer rules differ.

    Mathematical Operation:
        out = in × w_f × (-1)^w_t         (the effective pilot φ, no conjugate)

    The conjugate required for LS (h_ls = Y × conj(φ)) is performed downstream
    by LS_ROT — see v_ls_rot.py. Keeping the conjugate in LS_ROT makes the
    canonical formula visible at the LS boundary and reduces bit-manipulation
    cost in this module.

    Signal Encoding:
    ```
    Input `in` and output `out_p{port}` — DMRS {±1±j} constellation
        encoding {bit[1]=imag_sign, bit[0]=real_sign}, 0=positive, 1=negative:
         1 + j → 00    -1 + j → 01     1 - j → 10    -1 - j → 11

    Input `w_f_p{port}` — power-of-j factor:
        00 → +1    01 → +j    10 → -1    11 → -j

    Input `l_quote` (if present) combines with port-specific flip bits to
    derive w_t ∈ {0, 1} where w_t=1 means "multiply by -1".
    ```

    Whittle Factor Computation:
    ```
    whid = w_f × (-1)^w_t  in power-of-j encoding:
        whid[1] = w_f[1] ^ w_t     (XOR w_t flips bit[1] ⇔ multiplies by -1)
        whid[0] = w_f[0]           (unchanged)
    ```

    QPSK Complex Multiplication (multiplier-free):
    ```
    whid    Factor    Operation on input `in`
    ──────────────────────────────────────────────
     00      +1       Identity: out = in
     01      +j       90° rotation:  (x+jy)·j     = -y + jx
     10      -1       180° rotation: -in
     11      -j       -90° rotation: (x+jy)·(-j)  =  y - jx
    ```

    Parameters:
    :param N_CLK: 1
        Number of pipeline stages. If > 0, output is registered.
    :param dmrs_Type: 1 
        Fixed DMRS type for this OCC instance. Must be 1 or 2 (not "Hybrid").
        Type selection is handled at PCDMU level.
    :param is_double_dmrs: "Hybrid"
        Whether to support double-symbol DMRS (time-domain OCC).
        "Hybrid" mode adds runtime control via input port.
    :param antenna_ports: [8, 9, 10, 11]
        List of antenna port indices to support in this OCC instance.
    """
    if dmrs_Type not in [1, 2, "Hybrid"]:
        raise ValueError("ModuleOCC requires dmrs_Type to be 1, 2, or 'Hybrid'")

    # =========================================================================
    # DelayBudget analysis — compute minimum pipeline depth for OCC
    # =========================================================================
    # Internal combinational logic:
    #   XOR (whid computation): cost 0 (2-bit bitwise)
    #   QPSK MUX (4-way): cost 0 (2-bit mux, negligible)
    # OCC is purely combinational with trivial bit-width, so min N_CLK = 1
    # (just the output register).
    budget = DelayBudget(max_comb_cost=DEFAULT_BUDGET)
    # No significant combinational cost to add
    OCC_MIN_PIPELINE_DEPTH = 1  # output register only

    if N_CLK < OCC_MIN_PIPELINE_DEPTH:
        raise ValueError(
            f"OCC: N_CLK={N_CLK} is below the minimum pipeline depth "
            f"{OCC_MIN_PIPELINE_DEPTH} required by DelayBudget analysis.\n"
            f"{budget.summary()}"
        )

    #/ `timescale 1ns / 1ps
    #/ module OCC(
    if N_CLK > 0:
        #/ input clk,
        #/ input rst_n,
        pass
    # Runtime Controllers
    if is_double_dmrs == "Hybrid":
        #/ input is_double_dmrs,
        pass
    _has_dmrs_type = occ_needs_dmrs_type(
        antenna_ports, dmrs_Type, is_double_dmrs,
    )
    if _has_dmrs_type:
        #/ input dmrs_type,
        pass

    # Pre-calculated w_f inputs for each antenna port
    for port in antenna_ports:
        w_f = f"w_f_p{port}"
        #/ input [1:0] `w_f`,
        pass

    # Output signals for each antenna port
    for port in antenna_ports:
        out_name = f"out_p{port}"
        #/ output [1:0] `out_name`,
        pass

    # Time-domain OCC signal. Declared only when some port in this instance
    # actually flips; otherwise every w_t below is a constant 1'b0 and the input
    # would dangle. Keep in sync via occ_needs_l_quote().
    _has_l_quote = occ_needs_l_quote(antenna_ports, dmrs_Type, is_double_dmrs)
    if _has_l_quote:
        #/ input l_quote,
        pass
    #/ input [1:0] in
    #/ );

    for port in antenna_ports:
        #/ // --------------- Port `port` --------------- //
        out_name_raw = f"out_p{port}_raw"
        out_name = f"out_p{port}"
        w_f = f"w_f_p{port}"
        w_t = f"w_t_p{port}"
        whid_name = f"whid_p{port}"

        #/ wire       `w_t`;
        #/ wire [1:0] `whid_name`;

        # Time-domain OCC factor (w_t) calculation. Hybrid type builds select
        # the drawer at runtime; applying Type 1's rule to a Type-2-only high
        # port such as p18 suppresses its required second-symbol sign flip.
        if dmrs_Type == "Hybrid":
            _flip_t1 = port_needs_time_flip(port, 1)
            _flip_t2 = port_needs_time_flip(port, 2)
            if _flip_t1 == _flip_t2:
                _flip_expr = "1'b1" if _flip_t1 else "1'b0"
            elif _flip_t2:
                _flip_expr = "dmrs_type"
            else:
                _flip_expr = "~dmrs_type"
        else:
            _flip_expr = "1'b1" if port_needs_time_flip(port, dmrs_Type) else "1'b0"

        if _flip_expr == "1'b0":
            #/ assign `w_t` = 1'b0;
            pass
        elif is_double_dmrs == True:
            #/ assign `w_t` = l_quote & (`_flip_expr`);
            pass
        
        elif is_double_dmrs == False:
            # Never use time-domain OCC
            #/ assign `w_t` = 1'b0;
            pass
        
        else:  # is_double_dmrs == "Hybrid"
            #/ assign `w_t` = is_double_dmrs ? (l_quote & (`_flip_expr`)) : 1'b0;
            pass

        # whid = w_f × (-1)^w_t in power-of-j encoding
        # (w_f input is power-of-j; w_t flips bit[1] to multiply by -1)
        #/ assign `whid_name`[1] = `w_f`[1] ^ `w_t`;
        #/ assign `whid_name`[0] = `w_f`[0];

        # Apply whittle factor to the input (QPSK complex multiplication).
        # Output is the effective pilot φ = in × w_f × (-1)^w_t, encoded on
        # the DMRS {±1±j} constellation. Downstream LS_ROT consumes φ and
        # computes Y × conj(φ) to produce the canonical LS estimate.
        #/ wire [1:0] `out_name_raw`;
        #/ assign `out_name_raw` =
        #/ (`whid_name` == 2'b00) ? in :                // +1: Identity
        #/ (`whid_name` == 2'b01) ? {in[0], ~in[1]} :   // +j: (x+jy)*j = -y+jx
        #/ (`whid_name` == 2'b10) ? ~in :               // -1: Negate both
        #/ {~in[0], in[1]};                             // -j: (x+jy)*(-j) = y-jx
        
        # Output delay (optional pipeline stages)
        if N_CLK > 0:
            ModuleDelay(DWT=2, N_CLK=N_CLK, IF_RST_N=True, PORTS={'i_clk': 'clk', 'i_rst_n': 'rst_n', 'i_data': out_name_raw, 'o_data': out_name})
        else:
            #/ assign `out_name` = `out_name_raw`;
            pass
    
    _min_depth = occ_pipeline_depth(is_double_dmrs)
    #/ // Timing budget: N_CLK=`N_CLK` (auto-min=`_min_depth`)
    #/ endmodule
