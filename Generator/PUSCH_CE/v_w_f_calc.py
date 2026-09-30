from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from typing import List, Literal
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

def bit(x: int, n: int):
    return (x >> n) & 1


def drawer_b_indicator(port: int, dmrs_type: int) -> int:
    """Return 1 if `port` is in drawer B for the given DMRS type, else 0.

    3GPP TS 38.211 Table 6.4.1.1.3-1/2:
      Type 1 drawers per CDM group:
        A = {0,1,8,9} / {2,3,10,11},  B = {4,5,12,13} / {6,7,14,15}
        → drawer_B = bit(port, 2)
      Type 2 drawers per CDM group:
        A = {0-5, 12-17},  B = {6-11, 18-23}
        → drawer_B = (port % 12) >= 6
      Type 3 shares Type 2's drawer split. Per DRAWERS_TYPE3 the groups are
      ({0,1},{6,7}), ({2,3},{8,9}), ({4,5},{10,11}), ({12,13},{18,19}),
      ({14,15},{20,21}), ({16,17},{22,23}) — i.e. the low 6 ports of each
      12-port block are drawer A and the high 6 are drawer B, exactly as for
      Type 2. Type 3 differs only in group count (6 vs 3) and pilot REs per
      group (2 vs 4), neither of which affects the drawer indicator.
    """
    if dmrs_type == 1:
        return bit(port, 2)
    elif dmrs_type == 2 or dmrs_type == 3:
        return 1 if (port % 12) >= 6 else 0
    else:
        raise ValueError(f"Invalid dmrs_type: {dmrs_type}")


def enhanced_occ_bits(port: int, dmrs_type: int):
    """Return (s0, s1) for the 4-level enhanced OCC code.

    w_f(k') = (-1)^(s0 * k' + s1 * floor(k'/2))

    3GPP spec:
      s0 = bit(port, 0)     — alternating ±1 at the finest k' level
      s1 = drawer_B(port)    — alternating ±1 at the pair level (k'//2)

    Valid for both Type 1 (ports 8-15) and Type 2 (ports 12-23).
    """
    return bit(port, 0), drawer_b_indicator(port, dmrs_type)


def _wf_basic_bit(port_num, dtype, re_logic_idx_val):
    """Compute static basic w_f bit value (compile-time constant).
    Returns 0 or 1: s0 * (re_logic_idx % 2), where s0 = bit(port, 0).

    3GPP TS 38.211 Table 6.4.1.1.3-2/3:
      s0=0 → w_f = [+1, +1]  (no alternation)
      s0=1 → w_f = [+1, -1]  (alternation within pair)

    NOTE: Must be defined at module level (not inside @convert function)
    because @convert strips all 'return' statements."""
    s0 = bit(port_num, 0)
    return s0 * (re_logic_idx_val % 2)


def _wf_enhanced_static(port_num, dtype, re_logic_idx_val):
    """Compute static enhanced w_f (bit0, bit1) for DFT-4 encoding.
    Returns (bit0, bit1) where:
      bit0 = kq[0]
      bit1 = kq[1] ^ (s0 & kq[0])
    s0 = bit(port, 0).  Encoding: {bit1, bit0} = {imag_sign, real_sign}.

    NOTE: Must be defined at module level (not inside @convert function)
    because @convert strips all 'return' statements."""
    s0 = bit(port_num, 0)
    kp = re_logic_idx_val % 4
    kp0 = kp & 1
    kp1 = (kp >> 1) & 1
    b0 = kp0
    b1 = kp1 ^ (s0 & kp0)
    return (b0, b1)


@convert
def ModuleW_F_CALC(dmrs_type: int | Literal["Hybrid"], cdm_group: int, is_enhanced: bool | Literal["Hybrid"], antenna_ports: List[int], re_phy_indices: List[int], re_logic_indices: List[int]) -> None:
    """
    W_f (frequency-domain OCC factor) pre-calculation module for DMRS.
    
    Computes frequency-domain orthogonalization factors (w_f) for all antenna ports and resource elements
    in a specific PCDMU (Parallel CDM Unit). The w_f values depend on the antenna port, RE's logical
    position, and optionally on the RB index for enhanced DMRS Type 1.
    
    For hybrid DMRS type mode:
    - Ports 0-7: w_f calculation is type-independent (no dmrs_type input needed)
    - Ports 8+: w_f depends on dmrs_type (requires dmrs_type input)
    
    :param dmrs_type: 1 or "Hybrid"
        DMRS type for this PCDMU instance. Can be 1, 2, or "Hybrid" for runtime selection.
    :type dmrs_type: int | Literal["Hybrid"]
    :param cdm_group: 0
        CDM group index for this PCDMU (0-1 for Type 1, 0-2 for Type 2).
    :type cdm_group: int
    :param is_enhanced: "Hybrid"
        Enhanced DMRS mode selection.
    :type is_enhanced: bool | Literal["Hybrid"]
    :param antenna_ports: [0, 1]
        List of antenna port numbers processed by this PCDMU.
    :type antenna_ports: List[int]
    :param re_phy_indices: [0, 2, 4, 6, 8, 10]
        Physical RE indices processed by this PCDMU (sorted).
    :type re_phy_indices: List[int]
    :param re_logic_indices: [0, 1, 2, 3, 4, 5]
        Logical indices of REs in TRUE_INDEX_LIST corresponding to re_phy_indices.
    :type re_logic_indices: List[int]
    """
    
    # Check if any port needs dmrs_type signal (ports > 7 in Hybrid mode)
    needs_dmrs_type = (dmrs_type == "Hybrid" and any(port > 7 for port in antenna_ports))
    # print(f"needs_dmrs_type={needs_dmrs_type}, dmrs_Type = {dmrs_type}, ports = {antenna_ports}")
    # Determine if current_RB_idx is needed
    # For Hybrid dmrs_type mode with enhanced, always need RB index
    # For fixed Type 1 with enhanced, need RB index
    # For Type 2, never need RB index
    if dmrs_type == "Hybrid":
        needs_rb_idx = is_enhanced == True or is_enhanced == "Hybrid"
    else:
        needs_rb_idx = (dmrs_type == 1) and (is_enhanced == True or is_enhanced == "Hybrid")
    
    #/ `timescale 1ns / 1ps
    #/ module W_F_CALC(
    
    # Runtime mode selection input
    if is_enhanced == "Hybrid":
        #/ input is_enhanced,
        pass
    
    # DMRS type selection (only if ports > 7 exist in Hybrid mode)
    # Note: w_f is type-independent for ports 0-7 (verified against 3GPP spec).
    if needs_dmrs_type:
        #/ input dmrs_type,
        pass
    
    # RB index input (for Type 1 enhanced/hybrid)
    if needs_rb_idx:
        #/ input current_RB_idx_lsb,
        pass
    
    # W_f outputs for each antenna port and RE combination
    for port in antenna_ports:
        for re_phy_idx in re_phy_indices:
            w_f_name = f"w_f_p{port}_re{re_phy_idx}"
            #/ output [1:0] `w_f_name`,
            pass
    
    # Dummy input to prevent empty port list (removed by optimizer)
    #/ input _unused_dummy
    
    #/ );
    
    # NOTE: k_quote is derived statically from re_logic_indices (RE position within RB).
    # Only current_RB_idx_lsb is needed dynamically (for enhanced Type 1 DMRS).
    # The RB_COUNTER module in TOP layer provides current_RB_idx_lsb.
    
    # Generate w_f calculation logic for each antenna port
    #
    # 3GPP TS 38.211 Table 6.4.1.1.3-1/2:
    #   Basic (2-level OCC, k' ∈ {0,1}):
    #     w_f(k') = (-1)^(drawer_B * k')
    #     → w_f_enc = {d, d} where d = drawer_B * (k' % 2)
    #   Enhanced (4-level OCC, DFT-4, k' ∈ {0,1,2,3}):
    #     w_f(k') ∈ {+1, +j, -1, -j}  (complex DFT-4 pattern)
    #     s0 = bit(port, 0)
    #     kq = k'%4 represented as {kq[1], kq[0]}
    #     → bit[0] = kq[0]                    (real sign, LSB)
    #       bit[1] = kq[1] ^ (s0 & kq[0])    (imag sign, MSB)
    #     Even ports (s0=0): {00,01,10,11} → {+1,+j,-1,-j}
    #     Odd  ports (s0=1): {00,11,10,01} → {+1,-j,-1,+j}

    for port in antenna_ports:
        #/ // ========== Antenna Port `port` ==========

        # Determine if this port needs dmrs_type runtime selection
        port_needs_type_sel = (port > 7) and (dmrs_type == "Hybrid")

        if port_needs_type_sel:
            # Port > 7 with Hybrid dmrs_type: calculate for both types, mux at output
            for re_idx, re_phy_idx in enumerate(re_phy_indices):
                re_logic_idx = re_logic_indices[re_idx]
                w_f_name = f"w_f_p{port}_re{re_phy_idx}"

                #/ // RE `re_phy_idx` (logic index `re_logic_idx`)

                for _t in [1, 2]:
                    tname = f"w_f_type{_t}_p{port}_re{re_phy_idx}"
                    #/ wire [1:0] `tname`;
                    _s0_enh, _s1_enh = enhanced_occ_bits(port, _t)
                    _d = drawer_b_indicator(port, _t)

                    if is_enhanced == True:
                        if needs_rb_idx:
                            _base = re_logic_idx % 4
                            _off = (re_logic_idx + 2) % 4
                            _kq = f"{tname}_kq"
                            #/ wire [1:0] `_kq`;
                            #/ assign `_kq` = current_RB_idx_lsb ? 2'd`_off` : 2'd`_base`;
                            pass
                        else:
                            _kq = f"{tname}_kq"
                            _kp = re_logic_idx % 4
                            #/ wire [1:0] `_kq`;
                            #/ assign `_kq` = 2'd`_kp`;
                            pass
                        # DFT-4: bit[0]=kq[0], bit[1]=kq[1]^(s0&kq[0])
                        if _s0_enh == 0:
                            #/ assign `tname` = `_kq`;
                            pass
                        else:
                            #/ assign `tname` = {`_kq`[1] ^ `_kq`[0], `_kq`[0]};
                            pass
                    elif is_enhanced == False:
                        _v = _wf_basic_bit(port, _t, re_logic_idx)
                        # Power-of-j encoding: {_v, 0} → 00=+1, 10=-1.
                        # Paired with OCC `whid[0] = w_f[0]` (no XOR) and
                        # LS_ROT conjugate multiply (see v_occ.py / v_ls_rot.py).
                        #/ assign `tname` = 2'b`_v`0;
                        pass
                    else:  # Hybrid is_enhanced
                        # Enhanced path (DFT-4)
                        if needs_rb_idx:
                            _base = re_logic_idx % 4
                            _off = (re_logic_idx + 2) % 4
                            _kq_enh = f"{tname}_kq_enh"
                            #/ wire [1:0] `_kq_enh`;
                            #/ assign `_kq_enh` = current_RB_idx_lsb ? 2'd`_off` : 2'd`_base`;
                            pass
                        else:
                            _kq_enh = f"{tname}_kq_enh"
                            _kp = re_logic_idx % 4
                            #/ wire [1:0] `_kq_enh`;
                            #/ assign `_kq_enh` = 2'd`_kp`;
                            pass
                        _enh_sig = f"{tname}_enh"
                        #/ wire [1:0] `_enh_sig`;
                        if _s0_enh == 0:
                            #/ assign `_enh_sig` = `_kq_enh`;
                            pass
                        else:
                            #/ assign `_enh_sig` = {`_kq_enh`[1] ^ `_kq_enh`[0], `_kq_enh`[0]};
                            pass
                        # Basic path (power-of-j: {_v,0} → 00=+1, 10=-1)
                        _v_norm = _wf_basic_bit(port, _t, re_logic_idx)
                        _norm_sig = f"{tname}_norm"
                        #/ wire [1:0] `_norm_sig`;
                        #/ assign `_norm_sig` = 2'b`_v_norm`0;
                        #/ assign `tname`     = is_enhanced ? `_enh_sig` : `_norm_sig`;
                        pass

                # Mux based on dmrs_type
                _t1 = f"w_f_type1_p{port}_re{re_phy_idx}"
                _t2 = f"w_f_type2_p{port}_re{re_phy_idx}"
                #/ assign `w_f_name` = dmrs_type ? `_t2` : `_t1`;
                pass
        else:
            # Port 0-7 or fixed dmrs_type: single calculation
            # Type 3 must be preserved, not folded into Type 1: drawer_b_indicator
            # differs between the two (bit(port,2) vs (port%12)>=6), so mapping 3→1
            # would produce the wrong enhanced OCC / drawer sign for ports >= 4.
            if dmrs_type == 2:
                actual_dmrs_type = 2
            elif dmrs_type == 3:
                actual_dmrs_type = 3
            else:
                actual_dmrs_type = 1
            _s0_enh, _s1_enh = enhanced_occ_bits(port, actual_dmrs_type)
            _d = drawer_b_indicator(port, actual_dmrs_type)

            for re_idx, re_phy_idx in enumerate(re_phy_indices):
                re_logic_idx = re_logic_indices[re_idx]
                w_f_name = f"w_f_p{port}_re{re_phy_idx}"

                #/ // RE `re_phy_idx` (logic index `re_logic_idx`)

                if is_enhanced == True:
                    if needs_rb_idx:
                        _base = re_logic_idx % 4
                        _off = (re_logic_idx + 2) % 4
                        _kq = f"{w_f_name}_kq"
                        #/ wire [1:0] `_kq`;
                        #/ assign `_kq` = current_RB_idx_lsb ? 2'd`_off` : 2'd`_base`;
                        pass
                    else:
                        _kq = f"{w_f_name}_kq"
                        _kp = re_logic_idx % 4
                        #/ wire [1:0] `_kq`;
                        #/ assign `_kq` = 2'd`_kp`;
                        pass
                    # DFT-4: bit[0]=kq[0], bit[1]=kq[1]^(s0&kq[0])
                    if _s0_enh == 0:
                        #/ assign `w_f_name` = `_kq`;
                        pass
                    else:
                        #/ assign `w_f_name` = {`_kq`[1] ^ `_kq`[0], `_kq`[0]};
                        pass
                elif is_enhanced == False:
                    _v = _wf_basic_bit(port, actual_dmrs_type, re_logic_idx)
                    # Power-of-j encoding: {_v, 0} → 00=+1, 10=-1.
                    # Paired with OCC `whid[0] = w_f[0]` (no XOR) and
                    # LS_ROT conjugate multiply (see v_occ.py / v_ls_rot.py).
                    #/ assign `w_f_name` = 2'b`_v`0;
                    pass
                else:  # Hybrid is_enhanced
                    if needs_rb_idx:
                        _base = re_logic_idx % 4
                        _off = (re_logic_idx + 2) % 4
                        _kq_enh = f"{w_f_name}_kq_enh"
                        #/ wire [1:0] `_kq_enh`;
                        #/ assign `_kq_enh` = current_RB_idx_lsb ? 2'd`_off` : 2'd`_base`;
                        pass
                    else:
                        _kq_enh = f"{w_f_name}_kq_enh"
                        _kp = re_logic_idx % 4
                        #/ wire [1:0] `_kq_enh`;
                        #/ assign `_kq_enh` = 2'd`_kp`;
                        pass
                    _enh_sig = f"{w_f_name}_enh"
                    #/ wire [1:0] `_enh_sig`;
                    if _s0_enh == 0:
                        #/ assign `_enh_sig` = `_kq_enh`;
                        pass
                    else:
                        #/ assign `_enh_sig` = {`_kq_enh`[1] ^ `_kq_enh`[0], `_kq_enh`[0]};
                        pass
                    _v_norm = _wf_basic_bit(port, actual_dmrs_type, re_logic_idx)
                    _norm_sig = f"{w_f_name}_norm"
                    #/ wire [1:0] `_norm_sig`;
                    # Basic path (power-of-j: {_v,0} → 00=+1, 10=-1)
                    #/ assign `_norm_sig` = 2'b`_v_norm`0;
                    #/ assign `w_f_name`  = is_enhanced ? `_enh_sig` : `_norm_sig`;
                    pass

    #/ endmodule
