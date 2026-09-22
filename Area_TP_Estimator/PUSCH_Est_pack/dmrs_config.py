"""
DMRS Configuration Layer (Unified Python-layer infrastructure)

Single source of truth for all DMRS-related lookup tables, CDM group categorization,
PCDMU configuration, and per-antenna-port interpolation metadata.

Design Principle:
  All protocol-derived knowledge (CDM group tables, pilot RE positions, port categorization)
  lives here.  The @convert modules (v_ls, v_freq_interp_simple) import the *results*
  of this layer; they never duplicate the lookup tables.
"""

from __future__ import annotations
from typing import Literal, List, Dict, Set, Tuple


# =============================================================================
# 1. CDM Group Lookup Tables (3GPP TS 38.211 Table 6.4.1.1.3-1/2)
# =============================================================================

# These two dicts indicates cdm_group <-> antenna_port relationship upon double_dmrs & enhanced_dmrs = True
# When either is false, some ports are not legal to appear.
CDM_GROUPS_TYPE1: Dict[int, List[int]] = {
    0: [0, 1, 4, 5, 8, 9, 12, 13],
    1: [2, 3, 6, 7, 10, 11, 14, 15],
}

CDM_GROUPS_TYPE2: Dict[int, List[int]] = {
    0: [0, 1, 6, 7, 12, 13, 18, 19],
    1: [2, 3, 8, 9, 14, 15, 20, 21],
    2: [4, 5, 10, 11, 16, 17, 22, 23],
}

# Type 3 (MUSE): 6 CDM groups, 2 REs/RB each, fdCDM=2, tdCDM=2
# Max 24 ports (4 per CDM group with double-symbol DMRS)
CDM_GROUPS_TYPE3: Dict[int, List[int]] = {
    0: [0, 1, 6, 7],
    1: [2, 3, 8, 9],
    2: [4, 5, 10, 11],
    3: [12, 13, 18, 19],
    4: [14, 15, 20, 21],
    5: [16, 17, 22, 23],
}

# Pilot RE positions within one RB (k % 12) per CDM group
PILOT_RE_TYPE1: Dict[int, List[int]] = {
    0: [0, 2, 4, 6, 8, 10],  # even subcarriers
    1: [1, 3, 5, 7, 9, 11],  # odd subcarriers
}

PILOT_RE_TYPE2: Dict[int, List[int]] = {
    0: [0, 1, 6, 7],
    1: [2, 3, 8, 9],
    2: [4, 5, 10, 11],
}

# Type 3: adjacent pairs, 2 REs per CDM group, all 12 subcarriers occupied across 6 groups
PILOT_RE_TYPE3: Dict[int, List[int]] = {
    0: [0, 1],
    1: [2, 3],
    2: [4, 5],
    3: [6, 7],
    4: [8, 9],
    5: [10, 11],
}


# =============================================================================
# 1b. fdCDM / tdCDM Drawer Lookup Tables
# =============================================================================
# Each CDM group's antenna ports are split into two "drawers".
# Drawer A and Drawer B correspond to tdCDM-orthogonal subsets.
# Within each drawer, fdCDM is determined by the number of ports.

# Type 1 drawers per CDM group
DRAWERS_TYPE1: Dict[int, Tuple[List[int], List[int]]] = {
    0: ([0, 1, 8, 9], [4, 5, 12, 13]),
    1: ([2, 3, 10, 11], [6, 7, 14, 15]),
}

# Type 2 drawers per CDM group
DRAWERS_TYPE2: Dict[int, Tuple[List[int], List[int]]] = {
    0: ([0, 1, 12, 13], [6, 7, 18, 19]),
    1: ([2, 3, 14, 15], [8, 9, 20, 21]),
    2: ([4, 5, 16, 17], [10, 11, 22, 23]),
}

# Type 3 drawers per CDM group (drawer A = Walsh lines 1,2; drawer B = Walsh lines 3,4)
DRAWERS_TYPE3: Dict[int, Tuple[List[int], List[int]]] = {
    0: ([0, 1], [6, 7]),
    1: ([2, 3], [8, 9]),
    2: ([4, 5], [10, 11]),
    3: ([12, 13], [18, 19]),
    4: ([14, 15], [20, 21]),
    5: ([16, 17], [22, 23]),
}


# =============================================================================
# 2. Port-Level Queries
# =============================================================================


def get_cdm_group_for_port(antenna_port: int, dmrs_type: int) -> int:
    """Return the CDM group index for a given antenna port and fixed DMRS type (1, 2, or 3)."""
    if dmrs_type == 1:
        table = CDM_GROUPS_TYPE1
    elif dmrs_type == 2:
        table = CDM_GROUPS_TYPE2
    elif dmrs_type == 3:
        table = CDM_GROUPS_TYPE3
    else:
        raise ValueError(f"Invalid dmrs_type: {dmrs_type}")
    for group_idx, port_list in table.items():
        if antenna_port in port_list:
            return group_idx
    raise ValueError(
        f"Antenna port {antenna_port} not found in DMRS Type {dmrs_type} CDM group table."
    )


def port_in_type(antenna_port: int, dmrs_type: int) -> bool:
    """Check if an antenna port appears in the CDM group table for a specific DMRS type."""
    if dmrs_type == 1:
        table = CDM_GROUPS_TYPE1
    elif dmrs_type == 2:
        table = CDM_GROUPS_TYPE2
    elif dmrs_type == 3:
        table = CDM_GROUPS_TYPE3
    else:
        raise ValueError(f"Invalid dmrs_type: {dmrs_type}")
    return any(antenna_port in ports for ports in table.values())


def compute_fdCDM_tdCDM(
    active_ports: List[int], dmrs_type: int, cdm_group: int
) -> Tuple[int, int]:
    """
    Compute fdCDM and tdCDM for a CDM group given the set of active antenna ports.

    Algorithm (per CDM group):
      1. Split the CDM group's port universe into two drawers (A and B).
      2. Count how many of *active_ports* fall into each drawer.
      3. fdCDM:
           - If any drawer has count >= 3  → fdCDM = 4
           - Else if any drawer has count == 1 → fdCDM = 1
           - Otherwise (all non-empty drawers have count == 2) → fdCDM = 2
           - If both drawers are empty → fdCDM = 1 (degenerate / unused)
      4. tdCDM:
           - If both drawers contain at least one active port → tdCDM = 2
           - Otherwise → tdCDM = 1

    :param active_ports: List of currently active antenna port numbers.
    :param dmrs_type: DMRS type (1, 2, or 3).
    :param cdm_group: CDM group index.
    :returns: (fdCDM, tdCDM) tuple.
    """
    if dmrs_type == 1:
        drawer_table = DRAWERS_TYPE1
    elif dmrs_type == 2:
        drawer_table = DRAWERS_TYPE2
    elif dmrs_type == 3:
        drawer_table = DRAWERS_TYPE3
    else:
        raise ValueError(f"Invalid dmrs_type: {dmrs_type}")
    drawer_a, drawer_b = drawer_table[cdm_group]

    count_a = sum(1 for p in active_ports if p in drawer_a)
    count_b = sum(1 for p in active_ports if p in drawer_b)

    # fdCDM
    counts = [c for c in (count_a, count_b) if c > 0]
    if not counts:
        fdCDM = 1  # degenerate: no active port in this group
    elif any(c >= 3 for c in counts):
        fdCDM = 4
    elif any(c == 1 for c in counts):
        fdCDM = 1
    else:
        fdCDM = 2

    # tdCDM
    tdCDM = 2 if (count_a > 0 and count_b > 0) else 1

    return fdCDM, tdCDM


def get_port_type_category(antenna_port: int) -> int:
    """
    Determine the DMRS-type membership of an antenna port.

    Returns:
        0  — port appears in BOTH Type 1 and Type 2 tables (dual-type)
        1  — port appears ONLY in Type 1 tables
        2  — port appears ONLY in Type 2 tables

    Raises ValueError if the port is not found in any table.
    """
    in_t1 = port_in_type(antenna_port, 1)
    in_t2 = port_in_type(antenna_port, 2)
    if in_t1 and in_t2:
        return 0
    elif in_t1:
        return 1
    elif in_t2:
        return 2
    raise ValueError(f"Antenna port {antenna_port} not found in any CDM group table.")


def get_pilot_re_for_port(antenna_port: int, dmrs_type: int) -> List[int]:
    """Return sorted pilot RE positions (k%12) for a given port under a fixed DMRS type."""
    grp = get_cdm_group_for_port(antenna_port, dmrs_type)
    if dmrs_type == 1:
        table = PILOT_RE_TYPE1
    elif dmrs_type == 2:
        table = PILOT_RE_TYPE2
    elif dmrs_type == 3:
        table = PILOT_RE_TYPE3
    else:
        raise ValueError(f"Invalid dmrs_type: {dmrs_type}")
    return list(table[grp])


def get_pilot_re_for_port_unified(
    antenna_port: int, dmrs_Type: int | Literal["Hybrid"]
) -> List[int]:
    """
    Compute the pilot RE set for an antenna port under the given DMRS type config.

    For Hybrid:
      - dual-type port  → sorted union of Type1 + Type2 pilot REs
      - single-type port → that type's pilot RE set
    """
    if dmrs_Type in (1, 2, 3):
        return get_pilot_re_for_port(antenna_port, dmrs_Type)
    elif dmrs_Type == "Hybrid":
        re_set: Set[int] = set()
        if port_in_type(antenna_port, 1):
            re_set.update(get_pilot_re_for_port(antenna_port, 1))
        if port_in_type(antenna_port, 2):
            re_set.update(get_pilot_re_for_port(antenna_port, 2))
        return sorted(re_set)
    raise ValueError(f"Invalid dmrs_Type: {dmrs_Type}")


def infer_cdm_groups_from_union(pilot_re: List[int]) -> Tuple[int, int]:
    """
    Given a union pilot RE set (from a Hybrid dual-type port), determine the
    CDM group indices for Type 1 and Type 2 by matching against known tables.

    Returns (grp_t1, grp_t2) where:
      - grp_t1: CDM group index in PILOT_RE_TYPE1 whose REs are a subset of pilot_re
      - grp_t2: CDM group index in PILOT_RE_TYPE2 whose REs are a subset of pilot_re

    Raises ValueError if no matching CDM group is found for either type.
    """
    pilot_set = set(pilot_re)
    grp_t1 = None
    for gidx, re_list in PILOT_RE_TYPE1.items():
        if set(re_list).issubset(pilot_set):
            grp_t1 = gidx
            break
    if grp_t1 is None:
        raise ValueError(
            f"Cannot infer Type1 CDM group from union pilot_re={sorted(pilot_re)}. "
            f"No Type1 group is a subset."
        )

    grp_t2 = None
    for gidx, re_list in PILOT_RE_TYPE2.items():
        if set(re_list).issubset(pilot_set):
            grp_t2 = gidx
            break
    if grp_t2 is None:
        raise ValueError(
            f"Cannot infer Type2 CDM group from union pilot_re={sorted(pilot_re)}. "
            f"No Type2 group is a subset."
        )

    return grp_t1, grp_t2


def compute_compact_mapping(
    pilot_re_t1: List[int],
    pilot_re_t2: List[int],
) -> Tuple[List[int], List[int], List[int]]:
    """
    Compute compact 6-wide pilot layout for a Hybrid dual-type port.

    Type 1 always has 6 pilots, Type 2 has 4. The compact layout uses the
    T1 pilot positions as the 6-slot frame. Each T2 pilot maps to the
    nearest T1 slot (shared REs map directly; non-shared T2 REs take the
    adjacent T1-only slot).

    Returns:
        compact_re:         T1's 6 RE positions (the compact pilot set)
        compact_t2_slots:   indices into compact_re where T2 pilots land
        compact_zero_slots: indices into compact_re that are zero for T2
    """
    compact_re = sorted(pilot_re_t1)
    t2_sorted = sorted(pilot_re_t2)
    t1_set = set(compact_re)
    t2_set = set(t2_sorted)

    # Reserve the physically shared REs before placing any Type-2-only REs.
    # Otherwise an earlier Type-2-only RE can claim a shared slot (for
    # example port 6: T2 RE0 used to claim T1/T2 shared RE1), causing two
    # distinct Type-2 pilots to alias onto one compact lane.
    direct_slots = {
        t2_re: compact_re.index(t2_re)
        for t2_re in t2_sorted
        if t2_re in t1_set
    }
    used_slots: Set[int] = set(direct_slots.values())
    slot_for_t2: Dict[int, int] = dict(direct_slots)

    for t2_re in t2_sorted:
        if t2_re in slot_for_t2:
            continue
        slot = min(
            (i for i in range(len(compact_re)) if i not in used_slots),
            key=lambda i: (abs(compact_re[i] - t2_re), i),
        )
        slot_for_t2[t2_re] = slot
        used_slots.add(slot)

    compact_t2_slots = [slot_for_t2[t2_re] for t2_re in t2_sorted]

    compact_zero_slots = sorted(
        i for i in range(len(compact_re)) if i not in used_slots
    )

    return compact_re, compact_t2_slots, compact_zero_slots


def compact_pad_lmmse_matrix(
    matrix: List[List[complex]],
    compact_slots: List[int],
    n_compact_per_rb: int,
    n_output: int,
    lmmse_p: int,
) -> List[List[complex]]:
    """Place native LMMSE columns into their ordered compact pilot slots."""
    n_native_per_rb = len(compact_slots)
    native_for_slot = {
        compact_slot: native_idx
        for native_idx, compact_slot in enumerate(compact_slots)
    }
    padded: List[List[complex]] = []
    for k in range(n_output):
        row: List[complex] = []
        for rb_lmmse in range(lmmse_p):
            for slot in range(n_compact_per_rb):
                if slot in native_for_slot:
                    native_idx = native_for_slot[slot]
                    row.append(
                        matrix[k][rb_lmmse * n_native_per_rb + native_idx]
                    )
                else:
                    row.append(0j)
        padded.append(row)
    return padded


def compute_required_re_indices(
    antenna_ports: List[int],
    dmrs_Type: int | Literal["Hybrid"],
) -> List[int]:
    """
    Compute the minimal set of RE positions (k % 12) required for LS estimation.

    The result is the sorted union of pilot RE positions across all CDM groups
    that contain at least one of the given antenna ports, for each active
    DMRS type.

    :param antenna_ports: Configured antenna port numbers.
    :param dmrs_Type: 1, 2, 3, or "Hybrid".
    :returns: Sorted list of unique RE indices in [0, 11].
    """
    required: Set[int] = set()

    if dmrs_Type == 1 or dmrs_Type == "Hybrid":
        for gidx, plist in CDM_GROUPS_TYPE1.items():
            if any(p in plist for p in antenna_ports):
                required.update(PILOT_RE_TYPE1[gidx])

    if dmrs_Type == 2 or dmrs_Type == "Hybrid":
        for gidx, plist in CDM_GROUPS_TYPE2.items():
            if any(p in plist for p in antenna_ports):
                required.update(PILOT_RE_TYPE2[gidx])

    if dmrs_Type == 3:
        for gidx, plist in CDM_GROUPS_TYPE3.items():
            if any(p in plist for p in antenna_ports):
                required.update(PILOT_RE_TYPE3[gidx])

    return sorted(required)


# =============================================================================
# 3. Interpolation Topology Analysis
# =============================================================================


class InterpTopology:
    """
    Pre-computed interpolation topology for a pilot RE layout within one RB.

    Given a set of pilot RE indices in [0,11], classifies all 12 REs into:
      - pilot_re:          always-available pilot positions (pass-through)
      - interior_re:       between two pilots → linear average / NN from neighbours
      - left_boundary_re:  below the lowest pilot → needs cross-RB or extrapolation
      - right_boundary_re: above the highest pilot → needs cross-RB or extrapolation
    """

    __slots__ = ("pilot_re", "interior_re", "left_boundary_re", "right_boundary_re")

    def __init__(self, re_index_list: List[int]):
        self.pilot_re: List[int] = sorted(re_index_list)
        self.interior_re: List[
            Tuple[int, int, int]
        ] = []  # (re_k, left_pilot, right_pilot)
        self.left_boundary_re: List[int] = []
        self.right_boundary_re: List[int] = []

        for k in range(12):
            if k in self.pilot_re:
                continue
            left_pilots = [p for p in self.pilot_re if p < k]
            right_pilots = [p for p in self.pilot_re if p > k]
            if left_pilots and right_pilots:
                self.interior_re.append((k, left_pilots[-1], right_pilots[0]))
            elif not left_pilots:
                self.left_boundary_re.append(k)
            else:
                self.right_boundary_re.append(k)

    @property
    def non_pilot_re(self) -> List[int]:
        """All non-pilot RE indices, sorted."""
        return sorted(
            [k for k, _, _ in self.interior_re]
            + self.left_boundary_re
            + self.right_boundary_re
        )


# =============================================================================
# 4. PCDMU_Unified (formerly in v_ls.py)
# =============================================================================


class PCDMU_Unified:
    """
    Unified Parallel CDM group processing unit (Architecture v2.0).

    Supports both DMRS Type 1 and Type 2 in a single hardware instance.
    At any given clock cycle, only one DMRS Type is active (protocol guarantee),
    so hardware resources can be shared with a runtime dmrs_type mux.

    This class is consumed by v_ls.py (for LS estimation) and by v_top.py
    (for enumerating LS→interpolation connections).
    """

    def __init__(self, group_idx: int):
        self.group_idx = group_idx

        # Type 1 configuration
        self.has_type1: bool = False
        self.type1_antenna_ports: List[int] = []
        self.type1_re_phy_indices: List[int] = []
        self.type1_re_logic_indices: List[int] = []

        # Type 2 configuration
        self.has_type2: bool = False
        self.type2_antenna_ports: List[int] = []
        self.type2_re_phy_indices: List[int] = []
        self.type2_re_logic_indices: List[int] = []

        # Type 3 configuration
        self.has_type3: bool = False
        self.type3_antenna_ports: List[int] = []
        self.type3_re_phy_indices: List[int] = []
        self.type3_re_logic_indices: List[int] = []

        # Unified (union of all types)
        self.unified_antenna_ports: List[int] = []
        self.max_re_count: int = 0

        # Static fdCDM / tdCDM per DMRS type (computed after configure())
        self.type1_fdCDM: int = 1
        self.type1_tdCDM: int = 1
        self.type2_fdCDM: int = 1
        self.type2_tdCDM: int = 1
        self.type3_fdCDM: int = 1
        self.type3_tdCDM: int = 1

    # -----------------------------------------------------------------
    def _extract_re_indices_for_type(
        self, TRUE_INDEX_LIST: List[int], dmrs_type: int
    ) -> Tuple[List[int], List[int]]:
        """
        Extract RE physical and logical indices for a specific DMRS type
        and this CDM group from TRUE_INDEX_LIST.

        Returns (re_phy_indices, re_logic_indices) sorted by physical index.
        Deduplicates by physical RE value, keeping only the first occurrence.
        """
        if dmrs_type == 1:
            pilot_re_table = PILOT_RE_TYPE1
        elif dmrs_type == 2:
            pilot_re_table = PILOT_RE_TYPE2
        elif dmrs_type == 3:
            pilot_re_table = PILOT_RE_TYPE3
        else:
            raise ValueError(f"Invalid dmrs_type: {dmrs_type}")
        valid_k_set = set(pilot_re_table.get(self.group_idx, []))

        matched: List[Tuple[int, int]] = []
        seen_phy: Set[int] = set()
        for idx, re_val in enumerate(TRUE_INDEX_LIST):
            if (re_val % 12) in valid_k_set and re_val not in seen_phy:
                matched.append((re_val, idx))
                seen_phy.add(re_val)
        matched.sort(key=lambda x: x[0])

        re_phy = [v for v, _ in matched]
        re_logic = [i for _, i in matched]
        return re_phy, re_logic

    # -----------------------------------------------------------------
    def configure(
        self,
        antenna_ports_type1: List[int],
        antenna_ports_type2: List[int],
        TRUE_INDEX_LIST: List[int],
        antenna_ports_type3: List[int] | None = None,
    ) -> None:
        """Configure with Type1, Type2, and optionally Type3 antenna ports + RE mapping."""
        if antenna_ports_type3 is None:
            antenna_ports_type3 = []
        if antenna_ports_type1:
            self.has_type1 = True
            self.type1_antenna_ports = antenna_ports_type1
            self.type1_re_phy_indices, self.type1_re_logic_indices = (
                self._extract_re_indices_for_type(TRUE_INDEX_LIST, dmrs_type=1)
            )
        if antenna_ports_type2:
            self.has_type2 = True
            self.type2_antenna_ports = antenna_ports_type2
            self.type2_re_phy_indices, self.type2_re_logic_indices = (
                self._extract_re_indices_for_type(TRUE_INDEX_LIST, dmrs_type=2)
            )
        if antenna_ports_type3:
            self.has_type3 = True
            self.type3_antenna_ports = antenna_ports_type3
            self.type3_re_phy_indices, self.type3_re_logic_indices = (
                self._extract_re_indices_for_type(TRUE_INDEX_LIST, dmrs_type=3)
            )

        self.unified_antenna_ports = sorted(
            set(antenna_ports_type1 + antenna_ports_type2 + antenna_ports_type3)
        )
        self.max_re_count = max(
            len(self.type1_re_phy_indices) if self.has_type1 else 0,
            len(self.type2_re_phy_indices) if self.has_type2 else 0,
            len(self.type3_re_phy_indices) if self.has_type3 else 0,
        )

        # Compute static fdCDM / tdCDM
        if self.has_type1:
            self.type1_fdCDM, self.type1_tdCDM = compute_fdCDM_tdCDM(
                self.type1_antenna_ports, dmrs_type=1, cdm_group=self.group_idx
            )
        if self.has_type2:
            self.type2_fdCDM, self.type2_tdCDM = compute_fdCDM_tdCDM(
                self.type2_antenna_ports, dmrs_type=2, cdm_group=self.group_idx
            )
        if self.has_type3:
            self.type3_fdCDM, self.type3_tdCDM = compute_fdCDM_tdCDM(
                self.type3_antenna_ports, dmrs_type=3, cdm_group=self.group_idx
            )

    # -----------------------------------------------------------------
    @property
    def is_hybrid(self) -> bool:
        """True if this PCDMU supports both Type1 and Type2 at runtime."""
        return self.has_type1 and self.has_type2

    def all_output_re_phy_indices(self) -> List[int]:
        """Sorted union of all possible output physical RE indices across all types."""
        s: Set[int] = set()
        if self.has_type1:
            s.update(self.type1_re_phy_indices)
        if self.has_type2:
            s.update(self.type2_re_phy_indices)
        if self.has_type3:
            s.update(self.type3_re_phy_indices)
        return sorted(s)

    def get_drawer_breakdown(self, dmrs_type: int) -> Tuple[List[int], List[int]]:
        """
        Return (drawer_A_active_ports, drawer_B_active_ports) for a given dmrs_type.
        Only ports actually configured in this PCDMU are included.
        """
        if dmrs_type == 1:
            drawer_table = DRAWERS_TYPE1
        elif dmrs_type == 2:
            drawer_table = DRAWERS_TYPE2
        elif dmrs_type == 3:
            drawer_table = DRAWERS_TYPE3
        else:
            raise ValueError(f"Invalid dmrs_type: {dmrs_type}")
        drawer_a_all, drawer_b_all = drawer_table[self.group_idx]
        if dmrs_type == 1:
            ports = self.type1_antenna_ports
        elif dmrs_type == 2:
            ports = self.type2_antenna_ports
        else:
            ports = self.type3_antenna_ports
        return (
            [p for p in ports if p in drawer_a_all],
            [p for p in ports if p in drawer_b_all],
        )

    def get_fdCDM(self, dmrs_type: int) -> int:
        """Return the statically-computed fdCDM for a given DMRS type."""
        if dmrs_type == 1:
            return self.type1_fdCDM
        elif dmrs_type == 2:
            return self.type2_fdCDM
        elif dmrs_type == 3:
            return self.type3_fdCDM
        raise ValueError(f"Invalid dmrs_type: {dmrs_type}")

    def get_tdCDM(self, dmrs_type: int) -> int:
        """Return the statically-computed tdCDM for a given DMRS type."""
        if dmrs_type == 1:
            return self.type1_tdCDM
        elif dmrs_type == 2:
            return self.type2_tdCDM
        elif dmrs_type == 3:
            return self.type3_tdCDM
        raise ValueError(f"Invalid dmrs_type: {dmrs_type}")

    def compute_fdCDM_tdCDM_from_ports(
        self, active_ports: List[int], dmrs_type: int
    ) -> Tuple[int, int]:
        """
        Dynamic fdCDM/tdCDM computation given a runtime-selected subset of ports.
        Used when antenna_ports are switchable (Hybrid is_enhanced / is_double_dmrs).
        """
        return compute_fdCDM_tdCDM(active_ports, dmrs_type, self.group_idx)


# =============================================================================
# 5. DmrsArchConfig — top-level orchestrator
# =============================================================================


class DmrsArchConfig:
    """
    Top-level DMRS architecture configuration object.

    Constructed once in v_top.py (or in v_ls.py's __main__) from the protocol
    parameters, then passed downstream to both LS and interpolation modules.

    Provides:
      - Antenna port categorization by CDM group
      - ENABLED_CDM_GROUPS lists
      - PCDMU instance list
      - Per-antenna-port interpolation metadata (pilot RE lists, topologies)
      - LS output port enumeration
      - LS→interpolation wiring helpers
    """

    def __init__(
        self,
        antenna_ports: List[int],
        dmrs_Type: int | Literal["Hybrid"],
        TRUE_INDEX_LIST: List[int],
    ):
        self.antenna_ports = antenna_ports
        self.dmrs_Type = dmrs_Type
        self.TRUE_INDEX_LIST = TRUE_INDEX_LIST

        # Determine which DMRS types are active
        if dmrs_Type == 1:
            self._active_types = [1]
        elif dmrs_Type == 2:
            self._active_types = [2]
        elif dmrs_Type == 3:
            self._active_types = [3]
        else:
            self._active_types = [1, 2]

        # --- CDM group categorization ---
        self.group_ports_type1: Dict[int, List[int]] = {0: [], 1: []}
        self.group_ports_type2: Dict[int, List[int]] = {0: [], 1: [], 2: []}
        self.group_ports_type3: Dict[int, List[int]] = {i: [] for i in range(6)}

        for port in antenna_ports:
            if 1 in self._active_types:
                for gidx, plist in CDM_GROUPS_TYPE1.items():
                    if port in plist:
                        self.group_ports_type1[gidx].append(port)
            if 2 in self._active_types:
                for gidx, plist in CDM_GROUPS_TYPE2.items():
                    if port in plist:
                        self.group_ports_type2[gidx].append(port)
            if 3 in self._active_types:
                for gidx, plist in CDM_GROUPS_TYPE3.items():
                    if port in plist:
                        self.group_ports_type3[gidx].append(port)

        # --- ENABLED_CDM_GROUPS ---
        self.ENABLED_CDM_GROUPS_TYPE1: List[bool] = [
            len(p) > 0 for p in self.group_ports_type1.values()
        ]
        self.ENABLED_CDM_GROUPS_TYPE2: List[bool] = [
            len(p) > 0 for p in self.group_ports_type2.values()
        ]
        self.ENABLED_CDM_GROUPS_TYPE3: List[bool] = [
            len(p) > 0 for p in self.group_ports_type3.values()
        ]

        # --- MAX_CDM_GROUPS ---
        if dmrs_Type == 1:
            self.MAX_CDM_GROUPS = sum(self.ENABLED_CDM_GROUPS_TYPE1)
            self._max_group_count = 2
        elif dmrs_Type == 2:
            self.MAX_CDM_GROUPS = sum(self.ENABLED_CDM_GROUPS_TYPE2)
            self._max_group_count = 3
        elif dmrs_Type == 3:
            self.MAX_CDM_GROUPS = sum(self.ENABLED_CDM_GROUPS_TYPE3)
            self._max_group_count = 6
        else:
            self.MAX_CDM_GROUPS = max(
                sum(self.ENABLED_CDM_GROUPS_TYPE1),
                sum(self.ENABLED_CDM_GROUPS_TYPE2),
            )
            self._max_group_count = 3

        # --- PCDMU instances ---
        self.pcdmu_instances: List[PCDMU_Unified] = []
        for gidx in range(self._max_group_count):
            pt1 = (
                self.group_ports_type1.get(gidx, []) if 1 in self._active_types else []
            )
            pt2 = (
                self.group_ports_type2.get(gidx, []) if 2 in self._active_types else []
            )
            pt3 = (
                self.group_ports_type3.get(gidx, []) if 3 in self._active_types else []
            )
            if pt1 or pt2 or pt3:
                pcdmu = PCDMU_Unified(group_idx=gidx)
                pcdmu.configure(pt1, pt2, TRUE_INDEX_LIST, antenna_ports_type3=pt3)
                self.pcdmu_instances.append(pcdmu)

        # --- Per-port interpolation metadata (lazy-cached) ---
        self._port_interp_cache: Dict[int, PortInterpInfo] = {}

    # -----------------------------------------------------------------
    # LS output port enumeration
    # -----------------------------------------------------------------
    def ls_output_pairs(self) -> List[Tuple[int, int]]:
        """
        Enumerate all unique (antenna_port, re_phy_idx) output pairs from LS.
        This determines both the LS module's output port list and the
        interpolation module's input port list.
        """
        seen: Set[Tuple[int, int]] = set()
        pairs: List[Tuple[int, int]] = []
        for pcdmu in self.pcdmu_instances:
            for ant_port in pcdmu.unified_antenna_ports:
                for re_phy in pcdmu.all_output_re_phy_indices():
                    p = (ant_port, re_phy)
                    if p not in seen:
                        seen.add(p)
                        pairs.append(p)
        return pairs

    def ls_output_signal_name(self, ant_port: int, re_phy_idx: int) -> str:
        """Canonical Verilog signal name for an LS output."""
        return f"H_LS_port{ant_port}_re{re_phy_idx}"

    # -----------------------------------------------------------------
    # Per-antenna-port interpolation info
    # -----------------------------------------------------------------
    def get_port_interp_info(self, antenna_port: int) -> "PortInterpInfo":
        """
        Get (or create) the interpolation metadata for one antenna port.
        This tells the interpolation module everything it needs:
          - which pilot RE indices it receives from LS
          - whether it needs a runtime dmrs_type mux
          - the interpolation topology (interior / boundary REs)
        """
        if antenna_port not in self._port_interp_cache:
            self._port_interp_cache[antenna_port] = PortInterpInfo(
                antenna_port, self.dmrs_Type
            )
        return self._port_interp_cache[antenna_port]

    def unique_interp_configs(self) -> List["PortInterpInfo"]:
        """
        Return de-duplicated PortInterpInfo objects for all antenna ports.
        Ports that share the same pilot RE layout share one interp config
        (only the antenna_port number differs).
        """
        infos = [self.get_port_interp_info(p) for p in self.antenna_ports]
        return infos

    # -----------------------------------------------------------------
    # Wiring helpers: LS output → interp input
    # -----------------------------------------------------------------
    def interp_input_signals_for_port(
        self, antenna_port: int, rb_idx: int
    ) -> List[Tuple[str, int]]:
        """
        For one antenna port and one RB slot, return the list of
        (ls_output_signal_name, re_phy_idx) that feed the interpolation module.

        The interpolation module expects inputs named:
            h_ls_port{antenna_port}_rb{rb_idx}_re{re_k}_complex
        and the LS module outputs:
            H_LS_port{antenna_port}_re{re_phy_idx}
        """
        info = self.get_port_interp_info(antenna_port)
        result: List[Tuple[str, int]] = []
        for re_k in info.pilot_re_list:
            ls_sig = self.ls_output_signal_name(antenna_port, re_k)
            result.append((ls_sig, re_k))
        return result


# =============================================================================
# 6. PortInterpInfo — per-antenna-port interpolation descriptor
# =============================================================================


class PortInterpInfo:
    """
    Describes the interpolation configuration for a single antenna port.

    Attributes:
        antenna_port:   the port number
        dmrs_Type:      1, 2, or "Hybrid"
        pilot_re_list:  sorted pilot RE indices in [0,11] (union for Hybrid dual-type)
        is_dual_type:   True if port uses both Type1 and Type2 RE sets at runtime
        type_category:  0 (dual), 1 (Type1-only), 2 (Type2-only)
        topology:       InterpTopology for the pilot_re_list
        topology_t1:    InterpTopology for Type1 sub-list (only if dual-type)
        topology_t2:    InterpTopology for Type2 sub-list (only if dual-type)
        re_list_type1:  pilot RE list under Type1 (only if dual-type)
        re_list_type2:  pilot RE list under Type2 (only if dual-type)
    """

    def __init__(self, antenna_port: int, dmrs_Type: int | Literal["Hybrid"]):
        self.antenna_port = antenna_port
        self.dmrs_Type = dmrs_Type

        self.pilot_re_list = get_pilot_re_for_port_unified(antenna_port, dmrs_Type)

        # Determine type category
        if dmrs_Type == "Hybrid":
            self.type_category = get_port_type_category(antenna_port)
        elif dmrs_Type in (1, 2, 3):
            self.type_category = dmrs_Type
        else:
            self.type_category = 2

        self.is_dual_type = dmrs_Type == "Hybrid" and self.type_category == 0

        # Main topology (on the union RE set)
        self.topology = InterpTopology(self.pilot_re_list)

        # Sub-topologies for dual-type ports
        self.re_list_type1: List[int] = []
        self.re_list_type2: List[int] = []
        self.topology_t1: InterpTopology | None = None
        self.topology_t2: InterpTopology | None = None

        # Compact mapping for dual-type ports (8→6 reduction)
        self.pilot_re_compact: List[int] = []
        self.compact_t2_slots: List[int] = []
        self.compact_zero_slots: List[int] = []

        if self.is_dual_type:
            grp1 = get_cdm_group_for_port(antenna_port, 1)
            grp2 = get_cdm_group_for_port(antenna_port, 2)
            self.re_list_type1 = list(PILOT_RE_TYPE1[grp1])
            self.re_list_type2 = list(PILOT_RE_TYPE2[grp2])
            self.topology_t1 = InterpTopology(self.re_list_type1)
            self.topology_t2 = InterpTopology(self.re_list_type2)
            self.pilot_re_compact, self.compact_t2_slots, self.compact_zero_slots = (
                compute_compact_mapping(self.re_list_type1, self.re_list_type2)
            )

    # -----------------------------------------------------------------
    # Signal naming conventions
    # -----------------------------------------------------------------
    def interp_input_name(self, rb: int, re_k: int) -> str:
        """Input signal name for the interpolation module (from LS output)."""
        return f"h_ls_port{self.antenna_port}_rb{rb}_re{re_k}_complex"

    def interp_output_name(self, method: str, rb: int, re_k: int) -> str:
        """Output signal name from the interpolation module."""
        return f"h_{method}_port{self.antenna_port}_rb{rb}_re{re_k}_complex"

    @property
    def num_pilots(self) -> int:
        return len(self.pilot_re_list)

    @property
    def num_pilots_compact(self) -> int:
        return len(self.pilot_re_compact) if self.is_dual_type else self.num_pilots

    def all_non_pilot_re_for_dual_type(self) -> List[int]:
        """
        For dual-type ports, return sorted list of all RE positions that are
        non-pilot under at least one of the two types (i.e., need muxed output).
        """
        if not self.is_dual_type:
            return []
        assert self.topology_t1 is not None and self.topology_t2 is not None

        all_np: Set[int] = set()
        # Non-pilot under Type1
        all_np.update(self.topology_t1.non_pilot_re)
        # Non-pilot under Type2
        all_np.update(self.topology_t2.non_pilot_re)
        # Also include positions that are pilot in one type but not the other
        only_t1 = set(self.re_list_type1) - set(self.re_list_type2)
        only_t2 = set(self.re_list_type2) - set(self.re_list_type1)
        all_np |= only_t1 | only_t2
        # Remove positions that are always pilots (in both types)
        always_pilots = set(self.re_list_type1) & set(self.re_list_type2)
        all_np -= always_pilots
        return sorted(all_np)

    def compile_observation_layout(
        self,
        *,
        active_dmrs_type: int,
        enhanced: bool,
        dmrs_symbols: Tuple[int, ...] | List[int],
        bwp_start_crb: int,
        allocation_start_rb: int,
        num_rbs: int,
        fd_cdm: int,
        td_cdm: int,
        boundary_policy: Literal["normalize", "reject"] = "reject",
        numerical_policy: str = "rtl_audited_trn_tcpl_v1",
        inter_stage_gain_policy: str = "none",
    ) -> "ObservationLayoutDescriptor":
        """Compile the complete production observation descriptor for this port."""

        # Lazy import: observation_model is a research/campaign dependency
        # (architecture_selector), not part of the TOP generation path.
        from observation_model import compile_observation_layout

        if self.dmrs_Type != "Hybrid" and self.dmrs_Type != active_dmrs_type:
            raise ValueError(
                f"PortInterpInfo for DMRS Type {self.dmrs_Type} cannot compile "
                f"Type {active_dmrs_type} observations"
            )
        if not port_in_type(self.antenna_port, active_dmrs_type):
            raise ValueError(
                f"antenna port {self.antenna_port} is not legal for DMRS Type {active_dmrs_type}"
            )
        return compile_observation_layout(
            antenna_port=self.antenna_port,
            dmrs_type=active_dmrs_type,
            enhanced=enhanced,
            dmrs_symbols=dmrs_symbols,
            bwp_start_crb=bwp_start_crb,
            allocation_start_rb=allocation_start_rb,
            num_rbs=num_rbs,
            fd_cdm=fd_cdm,
            td_cdm=td_cdm,
            boundary_policy=boundary_policy,
            numerical_policy=numerical_policy,
            inter_stage_gain_policy=inter_stage_gain_policy,
        )

    def compile_frequency_observations(
        self,
        active_dmrs_type: int,
        fd_cdm: int,
        num_rbs: int,
        *,
        first_rb: int = 0,
        boundary_policy: Literal["normalize", "reject"] = "reject",
    ) -> "Tuple[OccObservation, ...]":
        """Compile the unique OCC observations consumed by interpolation.

        ``pilot_re_list`` remains the physical LS input geometry.  This method
        deliberately derives a separate observation geometry after averaging;
        callers must not infer statistical independence from the physical RE
        labels or from a padded Hybrid bus.
        """

        # Lazy import (see compile_observation_layout).
        from observation_model import compile_frequency_observations

        if active_dmrs_type not in (1, 2):
            raise ValueError(f"active_dmrs_type must be 1 or 2, got {active_dmrs_type}")
        if self.dmrs_Type != "Hybrid" and self.dmrs_Type != active_dmrs_type:
            raise ValueError(
                f"PortInterpInfo for DMRS Type {self.dmrs_Type} cannot compile "
                f"Type {active_dmrs_type} observations"
            )
        if not port_in_type(self.antenna_port, active_dmrs_type):
            raise ValueError(
                f"antenna port {self.antenna_port} is not legal for DMRS Type {active_dmrs_type}"
            )
        pilot_re = get_pilot_re_for_port(self.antenna_port, active_dmrs_type)
        return compile_frequency_observations(
            pilot_re,
            fd_cdm,
            num_rbs,
            dmrs_type=active_dmrs_type,
            first_rb=first_rb,
            boundary_policy=boundary_policy,
        )
