from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from typing import Literal, List, Tuple
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from dmrs_config import (
    DRAWERS_TYPE1, DRAWERS_TYPE2,
    CDM_GROUPS_TYPE1, CDM_GROUPS_TYPE2,
)


def get_drawer_port_indices(
    antenna_ports: List[int], dmrs_type: int, cdm_group: int
) -> Tuple[List[int], List[int]]:
    """
    Find indices into the antenna_ports list for drawer A and drawer B
    of a given (dmrs_type, cdm_group) combination.

    Returns (drawer_a_indices, drawer_b_indices) where each index
    refers to a bit position in the ports_enable vector.
    """
    drawer_table = DRAWERS_TYPE1 if dmrs_type == 1 else DRAWERS_TYPE2
    if cdm_group not in drawer_table:
        return [], []
    drawer_a_all, drawer_b_all = drawer_table[cdm_group]

    port_to_idx = {p: i for i, p in enumerate(antenna_ports)}

    drawer_a_idx = [port_to_idx[p] for p in antenna_ports if p in drawer_a_all]
    drawer_b_idx = [port_to_idx[p] for p in antenna_ports if p in drawer_b_all]

    return drawer_a_idx, drawer_b_idx


def gen_popcount_expr(bit_indices: List[int]) -> str:
    """
    Generate a Verilog expression for the popcount (sum) of selected
    bits from the ports_enable vector.  Result fits in 3 bits (max 4).
    """
    if not bit_indices:
        return "3'b000"
    elif len(bit_indices) == 1:
        return f"{{2'b00, ports_enable[{bit_indices[0]}]}}"
    else:
        terms = " + ".join(
            f"{{2'b00, ports_enable[{i}]}}" for i in bit_indices
        )
        return terms


@convert
def ModuleCDM_CTRL(antenna_ports: List[int], dmrs_Type: int | Literal["Hybrid"], has_ports_enable: bool = True) -> None:
    """
    CDM Control Signal Generator — computes fdCDM and tdCDM per CDM group.

    This module is pure combinational logic.  It counts the active ports in
    each drawer of each CDM group and derives the fdCDM and tdCDM control
    signals.

    When ``has_ports_enable=True`` (default), the module receives a runtime
    ``ports_enable`` bit-vector (from PORT_ENABLE) and dynamically computes
    the drawer populations.  When ``has_ports_enable=False``, all configured
    ``antenna_ports`` are assumed permanently active and the drawer populations
    are compile-time constants; the ``ports_enable`` port is omitted entirely.
    This mode is used when ``switchable_ports=False`` but ``dmrs_Type=Hybrid``
    so a runtime mux on ``dmrs_type`` is still needed.

    **fdCDM encoding (2-bit)**::

        2'b00 -> fdCDM = 1   (single-carrier CDM)
        2'b01 -> fdCDM = 2   (2-carrier CDM)
        2'b10 -> fdCDM = 4   (4-carrier CDM)

    **tdCDM encoding (1-bit)**::

        1'b0 -> tdCDM = 1   (single-symbol CDM)
        1'b1 -> tdCDM = 2   (dual-symbol CDM)

    **Algorithm per CDM group (per type):**

    1. Count active ports in drawer A and drawer B.
    2. fdCDM: any drawer count >= 3 -> 4; any count == 1 -> 1; else -> 2.
    3. tdCDM: both drawers non-empty -> 2; else -> 1.

    For Hybrid dmrs_Type mode, both Type 1 and Type 2 values are computed
    and a runtime MUX selects the active one (dmrs_type: 0 -> Type 1, 1 -> Type 2).

    :param antenna_ports: [0, 1, 4, 5, 8, 9, 12, 13]
        Maximal antenna port set (matches PORT_ENABLE module).
    :type antenna_ports: List[int]
    :param dmrs_Type: 1
        DMRS type. "Hybrid" enables runtime type muxing via dmrs_type input.
    :type dmrs_Type: int | Literal["Hybrid"]
    :param has_ports_enable: True
        When True, include a ``ports_enable`` input and compute drawer counts
        dynamically.  When False, drawer counts are constants derived from
        ``antenna_ports`` (all ports assumed always active).
    :type has_ports_enable: bool
    """
    N_PORTS = len(antenna_ports)
    needs_dmrs_type = (dmrs_Type == "Hybrid")

    # Determine which CDM groups are active for each type
    if dmrs_Type == 1:
        active_types = [1]
    elif dmrs_Type == 2:
        active_types = [2]
    else:
        active_types = [1, 2]

    # Determine which groups actually have ports from antenna_ports
    active_groups = set()
    for t in active_types:
        cdm_table = CDM_GROUPS_TYPE1 if t == 1 else CDM_GROUPS_TYPE2
        for gidx, port_list in cdm_table.items():
            if any(p in antenna_ports for p in port_list):
                active_groups.add(gidx)
    active_groups_sorted = sorted(active_groups)

    # ==== Module port declaration ====
    #/ `timescale 1ns / 1ps
    #/ module CDM_CTRL(

    # Output declarations (with trailing commas)
    for g in active_groups_sorted:
        fdCDM_port = f"fdCDM_cdm{g}"
        tdCDM_port = f"tdCDM_cdm{g}"
        #/ output [1:0] `fdCDM_port`,
        #/ output `tdCDM_port`,
        pass

    # Input port declarations — manage trailing commas carefully:
    #   outputs above all carry commas; the last input must have none.
    if needs_dmrs_type and has_ports_enable:
        #/ input                 dmrs_type,
        #/ input [`N_PORTS`-1:0] ports_enable
        pass
    elif needs_dmrs_type:  # not has_ports_enable
        #/ input dmrs_type
        pass
    elif has_ports_enable:  # not needs_dmrs_type
        #/ input [`N_PORTS`-1:0] ports_enable
        pass
    #/ );

    # ==== Per-type, per-group combinational logic ====
    for g in active_groups_sorted:
        #/ // ========== CDM Group `g` ==========

        # Track which types have logic for this group (for Hybrid muxing)
        type_wires = {}  # type -> (fdCDM_wire_name, tdCDM_wire_name)

        for t in active_types:
            cdm_table = CDM_GROUPS_TYPE1 if t == 1 else CDM_GROUPS_TYPE2
            if g not in cdm_table:
                continue

            # Check if this type has any matching ports in this group
            drawer_a_idx, drawer_b_idx = get_drawer_port_indices(antenna_ports, t, g)
            if not drawer_a_idx and not drawer_b_idx:
                continue

            suffix = f"_t{t}" if needs_dmrs_type else ""

            # Popcount for drawer A
            count_a_name = f"count_a_g{g}{suffix}"
            if has_ports_enable:
                count_a_expr = gen_popcount_expr(drawer_a_idx)
            else:
                count_a_expr = f"3'd{len(drawer_a_idx)}"
            #/ wire [2:0] `count_a_name` = `count_a_expr`;

            # Popcount for drawer B
            count_b_name = f"count_b_g{g}{suffix}"
            if has_ports_enable:
                count_b_expr = gen_popcount_expr(drawer_b_idx)
            else:
                count_b_expr = f"3'd{len(drawer_b_idx)}"
            #/ wire [2:0] `count_b_name` = `count_b_expr`;

            # fdCDM logic:
            #   any_ge3  => fdCDM = 4 (2'b10)
            #   any_eq1  => fdCDM = 1 (2'b00)
            #   else     => fdCDM = 2 (2'b01)
            # NOTE: when both drawers are empty (group inactive), this defaults
            #   to fdCDM = 2 — harmless since the group is unused.
            any_ge3_name = f"any_ge3_g{g}{suffix}"
            any_eq1_name = f"any_eq1_g{g}{suffix}"
            fdCDM_wire = f"fdCDM_g{g}{suffix}"
            #/ wire `any_ge3_name` = (`count_a_name` >= 3'd3) | (`count_b_name` >= 3'd3);
            #/ wire `any_eq1_name` = (`count_a_name` == 3'd1) | (`count_b_name` == 3'd1);
            #/ wire [1:0] `fdCDM_wire` = `any_ge3_name` ? 2'b10 : (`any_eq1_name` ? 2'b00 : 2'b01);

            # tdCDM logic:
            #   both drawers non-empty => tdCDM = 2 (1'b1)
            #   else                   => tdCDM = 1 (1'b0)
            tdCDM_wire = f"tdCDM_g{g}{suffix}"
            #/ wire `tdCDM_wire` = (|`count_a_name`) & (|`count_b_name`);

            type_wires[t] = (fdCDM_wire, tdCDM_wire)

        # Assign final outputs
        fdCDM_out = f"fdCDM_cdm{g}"
        tdCDM_out = f"tdCDM_cdm{g}"

        if needs_dmrs_type:
            has_t1 = 1 in type_wires
            has_t2 = 2 in type_wires

            if has_t1 and has_t2:
                fdCDM_t1 = type_wires[1][0]
                fdCDM_t2 = type_wires[2][0]
                tdCDM_t1 = type_wires[1][1]
                tdCDM_t2 = type_wires[2][1]
                #/ assign `fdCDM_out` = dmrs_type ? `fdCDM_t2` : `fdCDM_t1`;
                #/ assign `tdCDM_out` = dmrs_type ? `tdCDM_t2` : `tdCDM_t1`;
                pass
            elif has_t1:
                fdCDM_t1 = type_wires[1][0]
                tdCDM_t1 = type_wires[1][1]
                #/ assign `fdCDM_out` = `fdCDM_t1`;
                #/ assign `tdCDM_out` = `tdCDM_t1`;
                pass
            elif has_t2:
                fdCDM_t2 = type_wires[2][0]
                tdCDM_t2 = type_wires[2][1]
                #/ assign `fdCDM_out` = `fdCDM_t2`;
                #/ assign `tdCDM_out` = `tdCDM_t2`;
                pass
            else:
                # Degenerate: no ports in this group (shouldn't happen)
                #/ assign `fdCDM_out` = 2'b00;
                #/ assign `tdCDM_out` = 1'b0;
                pass
        else:
            t = active_types[0]
            fdCDM_w = type_wires[t][0]
            tdCDM_w = type_wires[t][1]
            #/ assign `fdCDM_out` = `fdCDM_w`;
            #/ assign `tdCDM_out` = `tdCDM_w`;
            pass

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    # Example: Type 1 CDM Group 0 ports with switchable is_enhanced/is_double_dmrs
    ModuleCDM_CTRL(
        antenna_ports=[0, 1, 4, 5, 8, 9, 12, 13],
        dmrs_Type=1,
    )
