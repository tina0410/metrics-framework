from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from typing import Literal, List
import sys
from os.path import dirname
sys.path.append(dirname(__file__))

from dmrs_config import port_in_type


def get_port_enable_condition(port: int, dmrs_type: int) -> str:
    """
    Determine the enable condition for a port under a specific DMRS type.

    Returns one of: 'always', 'enhanced', 'double_dmrs', 'enhanced_and_double'.

    Port classification follows 3GPP TS 38.211 antenna port numbering:
      Type 1 (16 ports): 0-3 basic, 4-7 double, 8-11 enhanced, 12-15 both
      Type 2 (24 ports): 0-5 basic, 6-11 double, 12-17 enhanced, 18-23 both
    """
    if dmrs_type == 1:
        if 0 <= port <= 3:
            return "always"
        elif 4 <= port <= 7:
            return "double_dmrs"
        elif 8 <= port <= 11:
            return "enhanced"
        elif 12 <= port <= 15:
            return "enhanced_and_double"
    elif dmrs_type == 2:
        if 0 <= port <= 5:
            return "always"
        elif 6 <= port <= 11:
            return "double_dmrs"
        elif 12 <= port <= 17:
            return "enhanced"
        elif 18 <= port <= 23:
            return "enhanced_and_double"
    raise ValueError(f"Port {port} not valid for DMRS Type {dmrs_type}")


def condition_to_verilog(cond: str, is_enhanced, is_double_dmrs) -> str:
    """
    Convert an enable condition string to a Verilog expression.

    Fixed-True parameters contribute 1'b1; "Hybrid" parameters contribute
    the runtime signal name.  Fixed-False parameters should not reach here
    (the port should not be in antenna_ports if its controlling mode is off).
    """
    if cond == "always":
        return "1'b1"
    elif cond == "enhanced":
        return "is_enhanced" if is_enhanced == "Hybrid" else "1'b1"
    elif cond == "double_dmrs":
        return "is_double_dmrs" if is_double_dmrs == "Hybrid" else "1'b1"
    elif cond == "enhanced_and_double":
        parts = []
        if is_enhanced == "Hybrid":
            parts.append("is_enhanced")
        if is_double_dmrs == "Hybrid":
            parts.append("is_double_dmrs")
        return " & ".join(parts) if parts else "1'b1"
    return "1'b0"


@convert
def ModulePORT_ENABLE(antenna_ports: List[int], dmrs_Type: int | Literal["Hybrid"], is_enhanced: bool | Literal["Hybrid"], is_double_dmrs: bool | Literal["Hybrid"], has_ext_enable: bool = False) -> None:
    """
    Antenna Port Enable Generator for switchable (Hybrid) mode.

    Generates a one-hot ``ports_enable`` output vector that indicates which
    antenna ports are active based on runtime ``is_enhanced`` and
    ``is_double_dmrs`` control signals.

    In Hybrid dmrs_Type mode, the enable condition for each port
    also depends on the runtime ``dmrs_type`` signal because the
    same port number may have different roles under different DMRS types
    (e.g., port 4 is "enhanced" under Type 1 but "basic" under Type 2).

    Port classification (3GPP TS 38.211):

    **DMRS Type 1** (16 ports, 0-15)::

        Ports 0-3:   always active (basic)
        Ports 4-7:   active when is_double_dmrs = 1
        Ports 8-11:  active when is_enhanced = 1
        Ports 12-15: active when is_enhanced & is_double_dmrs = 1

    **DMRS Type 2** (24 ports, 0-23)::

        Ports 0-5:   always active (basic)
        Ports 6-11:  active when is_double_dmrs = 1
        Ports 12-17: active when is_enhanced = 1
        Ports 18-23: active when is_enhanced & is_double_dmrs = 1

    When ``dmrs_Type = "Hybrid"``, ports present in both types use
    a runtime MUX (dmrs_type: 0 -> Type 1, 1 -> Type 2).
    Ports present in only one type are gated by ``~dmrs_type`` or ``dmrs_type``.

    :param antenna_ports: [0, 1, 4, 5]
        Maximal antenna port set (superset of all runtime-enabled ports).
    :type antenna_ports: List[int]
    :param dmrs_Type: 1
        DMRS type configuration. "Hybrid" enables runtime type selection.
    :type dmrs_Type: int | Literal["Hybrid"]
    :param is_enhanced: "Hybrid"
        Enhanced DMRS mode. "Hybrid" makes it a runtime-selectable signal.
    :type is_enhanced: bool | Literal["Hybrid"]
    :param is_double_dmrs: "Hybrid"
        Double-symbol DMRS mode. "Hybrid" makes it a runtime-selectable signal.
    :type is_double_dmrs: bool | Literal["Hybrid"]
    :param has_ext_enable: False
        When True, adds external per-port enable inputs (port_enable_ext_{i})
        that are ANDed with the protocol-derived enable logic, allowing
        user-controlled port switching for low-power operation.
    :type has_ext_enable: bool
    """
    N_PORTS = len(antenna_ports)
    needs_dmrs_type = (dmrs_Type == "Hybrid")
    needs_is_enhanced = (is_enhanced == "Hybrid")
    needs_is_double_dmrs = (is_double_dmrs == "Hybrid")

    #/ `timescale 1ns / 1ps
    #/ module PORT_ENABLE(
    
    if needs_is_enhanced:
        #/ input is_enhanced,
        pass
    if needs_is_double_dmrs:
        #/ input is_double_dmrs,
        pass
    if needs_dmrs_type:
        #/ input dmrs_type,
        pass
    if has_ext_enable:
        for i, port in enumerate(antenna_ports):
            #/ input `f"port_enable_ext_{i}"`,
            pass
    #/ output [`N_PORTS`-1:0] ports_enable
    #/ );

    for i, port in enumerate(antenna_ports):
        if has_ext_enable:
            en_name = f"ports_enable_int_{i}"
            #/ wire `en_name`;
        else:
            en_name = f"ports_enable[{i}]"

        if dmrs_Type == "Hybrid":
            in_t1 = port_in_type(port, 1)
            in_t2 = port_in_type(port, 2)

            if in_t1 and in_t2:
                # Port exists in both Type 1 and Type 2
                cond_t1 = get_port_enable_condition(port, 1)
                cond_t2 = get_port_enable_condition(port, 2)
                expr_t1 = condition_to_verilog(cond_t1, is_enhanced, is_double_dmrs)
                expr_t2 = condition_to_verilog(cond_t2, is_enhanced, is_double_dmrs)
                if expr_t1 == expr_t2:
                    #/ assign `en_name` = `expr_t1`;  // Port `port`
                    pass
                else:
                    #/ assign `en_name` = dmrs_type ? (`expr_t2`) : (`expr_t1`);  // Port `port`
                    pass
            elif in_t1:
                # Port only in Type 1 — disabled when Type 2 active
                cond_t1 = get_port_enable_condition(port, 1)
                expr_t1 = condition_to_verilog(cond_t1, is_enhanced, is_double_dmrs)
                #/ assign `en_name` = ~dmrs_type & (`expr_t1`);  // Port `port` (Type 1 only)
                pass
            elif in_t2:
                # Port only in Type 2 — disabled when Type 1 active
                cond_t2 = get_port_enable_condition(port, 2)
                expr_t2 = condition_to_verilog(cond_t2, is_enhanced, is_double_dmrs)
                #/ assign `en_name` = dmrs_type & (`expr_t2`);  // Port `port` (Type 2 only)
                pass
        else:
            # Fixed dmrs_Type: single condition
            cond = get_port_enable_condition(port, dmrs_Type)
            expr = condition_to_verilog(cond, is_enhanced, is_double_dmrs)
            #/ assign `en_name` = `expr`;  // Port `port`
            pass

        # External enable gating: AND internal enable with user-controlled enable
        if has_ext_enable:
            ext_name = f"port_enable_ext_{i}"
            final_name = f"ports_enable[{i}]"
            #/ assign `final_name` = `en_name` & `ext_name`;  // Port `port` (gated by external enable)

    #/ endmodule


if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()

    # Example: Type 1 CDM Group 0 ports with Hybrid is_enhanced and is_double_dmrs
    ModulePORT_ENABLE(
        antenna_ports=[0, 1, 4, 5, 8, 9, 12, 13],
        dmrs_Type=1,
        is_enhanced="Hybrid",
        is_double_dmrs="Hybrid",
    )
