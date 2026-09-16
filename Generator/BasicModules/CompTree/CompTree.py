###################################################################################################
# Module Name: CompTree
# Description: Balanced fixed-point greater/lesser-value reduction tree.
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Dependency Modules:
#   - Comp
#   - Comppos
#   - Delay
#   - FxMatch
###########################################################################
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

try:
    from .Comp import ModuleComp
except ImportError:
    from Comp import ModuleComp
try:
    from .Comppos import ModuleComppos
except ImportError:
    from Comppos import ModuleComppos
try:
    from .Delay import ModuleDelay
except ImportError:
    from Delay import ModuleDelay
try:
    from .FxMatch import ModuleFxMatch
except ImportError:
    from FxMatch import ModuleFxMatch
try:
    from .PyTU import QuMode, OfMode, QuType
except ImportError:
    from PyTU import QuMode, OfMode, QuType
import math

def has_non_zero(var):
    if isinstance(var, (int, float)):
        return var != 0
    elif isinstance(var, (list, tuple)):
        return any(x != 0 for x in var)
    else:
        return True

@convert
def ModuleCompTree(QU_IN:QuType, QU_OUT:QuType, N_PIPELINES = 10, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N = False, N_INPUTS=2, IF_GIDX = False, IF_LIDX = False, IF_EIDX = False, IF_GVAL = True, IF_LVAL = False, CONFIG_MODE = "A"):
    """Reduce fixed-point inputs through a balanced binary comparison tree.

    ``IF_GVAL`` selects a maximum-value tree and ``IF_LVAL`` selects a
    minimum-value tree.  The two value reductions are intentionally mutually
    exclusive: after the first layer they require different operand streams.
    The v8 N0/N1 normalization use is the same-type, unsigned, combinational
    ``IF_LVAL`` configuration.
    """
    if not isinstance(N_INPUTS, int) or isinstance(N_INPUTS, bool):
        raise TypeError("N_INPUTS must be an integer.")
    if N_INPUTS < 2:
        raise ValueError("N_INPUTS must be at least 2.")

    # Parse Configuration Mode (Case Insensitive)
    CONFIG_MODE = CONFIG_MODE.lower()
    if CONFIG_MODE == "a" or CONFIG_MODE == "input-output" or CONFIG_MODE == "input_output" or CONFIG_MODE == "inout" or CONFIG_MODE == "auto":
        CONFIG_MODE = "A"
    elif CONFIG_MODE == "b" or CONFIG_MODE == "layer-wise" or CONFIG_MODE == "layer_wise":
        CONFIG_MODE = "B"
    elif CONFIG_MODE == "c" or CONFIG_MODE == "element-wise" or CONFIG_MODE == "element_wise":
        raise NotImplementedError("CONFIG_MODE C is reserved and not implemented.")
    else:
        CONFIG_MODE = "A"
        print("// Warning: Configuration Mode is not supported, set to default mode A")

    #----------------------------------------------------------------------------------
    n_layers = math.ceil(math.log2(N_INPUTS))

    QU_LAYERS: list[QuType] = [QuType() for _ in range(n_layers+1)]

    if CONFIG_MODE == "A":
        if not isinstance(QU_IN, QuType) and type(QU_IN).__name__ != "QuType":
            raise TypeError("Mode A requires QU_IN to be a single QuType.")
        if not isinstance(N_PIPELINES, int) or isinstance(N_PIPELINES, bool):
            raise TypeError("Mode A requires N_PIPELINES to be an integer.")
        if N_PIPELINES < 0:
            raise ValueError("N_PIPELINES must be non-negative.")
        if not all(isinstance(flag, bool) for flag in (IF_GIDX, IF_LIDX, IF_EIDX, IF_GVAL, IF_LVAL)):
            raise TypeError("Mode A output-enable flags must be bool.")
        if isinstance(IF_RST_N, bool):
            IF_RST_N = [IF_RST_N] * N_PIPELINES
        elif isinstance(IF_RST_N, list):
            if len(IF_RST_N) != N_PIPELINES or not all(isinstance(flag, bool) for flag in IF_RST_N):
                raise ValueError("IF_RST_N must contain exactly N_PIPELINES Boolean entries.")
        else:
            raise TypeError("IF_RST_N must be bool or list[bool].")
        # Convert Mode A Input to Mode B Input
        # QMode, OMode, if_arst_n, if_rst_n, if_en are the same for all layers
        QU_MODE = [QU_MODE] * n_layers
        OF_MODE = [OF_MODE] * n_layers
        IF_GIDX = [IF_GIDX] * n_layers
        if (IF_GIDX[0] and (IF_GVAL == False)):
            IF_GVAL = [True] * n_layers
            IF_GVAL[n_layers - 1] = False
        else:
            IF_GVAL = [IF_GVAL] * n_layers
        IF_LVAL = [IF_LVAL] * n_layers
        # IF_EIDX and IF_LIDX are not implemented by the legacy index tree,
        # but normalize them so validation and Mode A/B handling are uniform.
        IF_EIDX = [IF_EIDX] * n_layers
        IF_LIDX = [IF_LIDX] * n_layers
        # N_PIPELINES should distribute evenly to all layers
        base_pipelines = N_PIPELINES // n_layers
        extra_pipelines = N_PIPELINES % n_layers
        N_PIPELINES = [base_pipelines if i < n_layers - extra_pipelines else base_pipelines + 1 for i in range(n_layers)]
        # dwt_layers start from dwt_in and increase by 1, except the last being dwt_out
        QU_LAYERS[0].IF_SIGNED = QU_IN.IF_SIGNED
        for i in range(n_layers):
            QU_LAYERS[i].DWT = QU_IN.DWT
            # QU_LAYERS.FRAC are all the same as frac_in, except the last being frac_out
            QU_LAYERS[i].FRAC = QU_IN.FRAC
        QU_LAYERS[n_layers].DWT = QU_OUT.DWT
        QU_LAYERS[n_layers].FRAC = QU_OUT.FRAC
        DWT_GPOS_LAYERS = [i for i in range(n_layers + 1)]
        # Parse the Input Args:

    if CONFIG_MODE == "B":
        if not isinstance(QU_IN, list) or len(QU_IN) != n_layers or not all(isinstance(item, QuType) or type(item).__name__ == "QuType" for item in QU_IN):
            raise TypeError("Mode B requires one QU_IN QuType per tree layer.")
        if not isinstance(N_PIPELINES, list) or len(N_PIPELINES) != n_layers:
            raise TypeError("Mode B requires one N_PIPELINES integer per tree layer.")
        if not all(isinstance(depth, int) and not isinstance(depth, bool) and depth >= 0 for depth in N_PIPELINES):
            raise ValueError("Every Mode B pipeline depth must be a non-negative integer.")
        if not isinstance(QU_MODE, list) or len(QU_MODE) != n_layers:
            raise TypeError("Mode B requires one QU_MODE per tree layer.")
        if not isinstance(OF_MODE, list) or len(OF_MODE) != n_layers:
            raise TypeError("Mode B requires one OF_MODE per tree layer.")
        if isinstance(IF_GIDX, bool):
            IF_GIDX = [IF_GIDX] * n_layers
        if isinstance(IF_LIDX, bool):
            IF_LIDX = [IF_LIDX] * n_layers
        if isinstance(IF_EIDX, bool):
            IF_EIDX = [IF_EIDX] * n_layers
        if isinstance(IF_GVAL, bool):
            IF_GVAL = [IF_GVAL] * n_layers
        if isinstance(IF_LVAL, bool):
            IF_LVAL = [IF_LVAL] * n_layers
        if not all(isinstance(flags, list) and len(flags) == n_layers and all(isinstance(flag, bool) for flag in flags) for flags in (IF_GIDX, IF_LIDX, IF_EIDX, IF_GVAL, IF_LVAL)):
            raise TypeError("Mode B output-enable flags must be bool or one Boolean per layer.")
        if any(IF_GIDX) and not any(IF_GVAL):
            IF_GVAL = [True] * n_layers
            IF_GVAL[n_layers - 1] = False
        QU_LAYERS[0].IF_SIGNED = False
        if any(item.IF_SIGNED for item in QU_IN):
            QU_LAYERS[0].IF_SIGNED = True
        for i in range(n_layers):
            QU_LAYERS[i].DWT = QU_IN[i].DWT
            QU_LAYERS[i].FRAC = QU_IN[i].FRAC
        QU_LAYERS[n_layers].DWT = QU_OUT.DWT
        QU_LAYERS[n_layers].FRAC = QU_OUT.FRAC
        if isinstance(IF_RST_N, bool):
            IF_RST_N = [IF_RST_N] * sum(N_PIPELINES)
        elif isinstance(IF_RST_N, list):
            if len(IF_RST_N) != sum(N_PIPELINES) or not all(isinstance(flag, bool) for flag in IF_RST_N):
                raise ValueError("IF_RST_N must match the sum of Mode B pipeline depths.")
        else:
            raise TypeError("IF_RST_N must be bool or list[bool].")
        pass
        DWT_GPOS_LAYERS = [i for i in range(n_layers + 1)]

    if any(IF_GVAL) and any(IF_LVAL):
        raise ValueError("IF_GVAL and IF_LVAL cannot both be enabled in CompTree.")
    if any(IF_LVAL) and (any(IF_GIDX) or any(IF_LIDX) or any(IF_EIDX)):
        raise ValueError("The qualified IF_LVAL reduction is value-only.")

    #/ module COMPTREE(
    #/  i_data
    if IF_GIDX[0]:
        #/ ,o_gidx
        pass
    if IF_GVAL[n_layers - 1]:
        #/ ,o_gval
        pass
    if IF_LVAL[n_layers - 1]:
        #/ ,o_lval
        pass

    if has_non_zero(N_PIPELINES):

        if any(IF_RST_N) == True:
            #/, i_rst_n
            pass
        #/, i_clk
    #/);

    #/ // Input and Output Ports
    #/ input wire [`QU_LAYERS[0].DWT * N_INPUTS`-1:0] i_data;
    if IF_GIDX[0]:
        #/ output [`n_layers`-1:0] o_gidx;
        pass
    if IF_GVAL[n_layers - 1]:
        #/ output [`QU_LAYERS[n_layers].DWT`-1:0] o_gval;
        pass
    if IF_LVAL[n_layers - 1]:
        #/ output [`QU_LAYERS[n_layers].DWT`-1:0] o_lval;
        pass
    if has_non_zero(N_PIPELINES):
        #/ input wire i_clk;
        if any(IF_RST_N) == True:
            #/ input wire i_rst_n;
            pass
    #/ wire [`QU_LAYERS[0].DWT * N_INPUTS`-1:0] data0;
    #/ assign data0 = i_data;
    n_operators = N_INPUTS

    for layer in range(n_layers):
        n_remainder = n_operators % 2
        n_comps = n_operators // 2
        n_operators = n_comps + n_remainder

        if IF_GVAL[layer]:
            #/ wire [`n_operators*QU_LAYERS[layer+1].DWT`-1:0] gval_l`layer+1`;
            pass
        if IF_LVAL[layer]:
            #/ wire [`n_operators*QU_LAYERS[layer+1].DWT`-1:0] lval_l`layer+1`;
            pass
        if IF_GIDX[layer]:
            #/ wire [`n_operators*DWT_GPOS_LAYERS[layer+1]`-1:0] gidx_l`layer+1`;
            pass

        QU_IN_FIX = QuType()
        QU_OUT_FIX = QuType()
        QU_IN_FIX.DWT = QU_LAYERS[layer].DWT
        QU_IN_FIX.FRAC = QU_LAYERS[layer].FRAC
        QU_IN_FIX.IF_SIGNED = QU_LAYERS[0].IF_SIGNED
        QU_OUT_FIX.DWT = QU_LAYERS[layer+1].DWT
        QU_OUT_FIX.FRAC = QU_LAYERS[layer+1].FRAC
        QU_OUT_FIX.IF_SIGNED = QU_LAYERS[0].IF_SIGNED
        if (layer == 0):
            for comp in range(n_comps):
                inst_ports_comp = {
                    "i_data_2": f"data{layer}[{2*comp+1}*{QU_LAYERS[layer].DWT}-1:{2*comp}*{QU_LAYERS[layer].DWT}]",
                    "i_data_1": f"data{layer}[{2*comp+2}*{QU_LAYERS[layer].DWT}-1:{2*comp+1}*{QU_LAYERS[layer].DWT}]"
                }
                if IF_GVAL[layer]:
                    inst_ports_comp["o_gval" ]= f"gval_l{layer+1}[{comp+1}*{QU_LAYERS[layer+1].DWT}-1:{comp}*{QU_LAYERS[layer+1].DWT}]"
                if IF_LVAL[layer]:
                    inst_ports_comp["o_lval" ]= f"lval_l{layer+1}[{comp+1}*{QU_LAYERS[layer+1].DWT}-1:{comp}*{QU_LAYERS[layer+1].DWT}]"
                if IF_GIDX[layer]:
                    inst_ports_comp["o_gidx"] = f"gidx_l{layer+1}[{comp+1}*{DWT_GPOS_LAYERS[layer+1]}-1:{comp}*{DWT_GPOS_LAYERS[layer+1]}]"
                if N_PIPELINES[layer] > 0:
                    inst_ports_comp["i_clk"] = "i_clk"
                    if type(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]) == bool:
                        if(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                            inst_ports_comp["i_rst_n"] = "i_rst_n"
                    else:
                        if any(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                            inst_ports_comp["i_rst_n"] = "i_rst_n"
                ModuleComp(QU_IN_1 = QU_IN_FIX, QU_IN_2 = QU_IN_FIX, QU_OUT = QU_OUT_FIX, QU_MODE = QU_MODE[layer], OF_MODE = OF_MODE[layer], IF_RST_N=IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])], N_PIPELINES=N_PIPELINES[layer], IF_GVAL=IF_GVAL[layer], IF_LVAL=IF_LVAL[layer], IF_GIDX=IF_GIDX[layer], PORTS = inst_ports_comp)
        else:
            if IF_GIDX[layer]:
                for comp_pos in range(n_comps):
                    QU_GPOS_IN=QuType()
                    QU_GPOS_IN.DWT = DWT_GPOS_LAYERS[layer]
                    inst_ports_comp = {
                        "i_data_2": f"gval_l{layer}[{2*comp_pos+1}*{QU_LAYERS[layer].DWT}-1:{2*comp_pos}*{QU_LAYERS[layer].DWT}]",
                        "i_data_1": f"gval_l{layer}[{2*comp_pos+2}*{QU_LAYERS[layer].DWT}-1:{2*comp_pos+1}*{QU_LAYERS[layer].DWT}]",
                        "i_data_gpos_2": f"gidx_l{layer}[{2*comp_pos+1}*{DWT_GPOS_LAYERS[layer]}-1:{2*comp_pos}*{DWT_GPOS_LAYERS[layer]}]",
                        "i_data_gpos_1": f"gidx_l{layer}[{2*comp_pos+2}*{DWT_GPOS_LAYERS[layer]}-1:{2*comp_pos+1}*{DWT_GPOS_LAYERS[layer]}]"
                    }
                    if IF_GVAL[layer]:
                        inst_ports_comp["o_gval" ]= f"gval_l{layer+1}[{comp_pos+1}*{QU_LAYERS[layer+1].DWT}-1:{comp_pos}*{QU_LAYERS[layer+1].DWT}]"
                    if IF_GIDX[layer]:
                        inst_ports_comp["o_gidx"] = f"gidx_l{layer+1}[{comp_pos+1}*{DWT_GPOS_LAYERS[layer+1]}-1:{comp_pos}*{DWT_GPOS_LAYERS[layer+1]}]"
                    if N_PIPELINES[layer] > 0:
                        inst_ports_comp["i_clk"] = "i_clk"
                        if type(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]) == bool:
                            if(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                                inst_ports_comp["i_rst_n"] = "i_rst_n"
                        else:
                            if any(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                                inst_ports_comp["i_rst_n"] = "i_rst_n"
                    ModuleComppos(QU_IN_1 = QU_IN_FIX, QU_IN_2 = QU_IN_FIX, QU_GPOS_IN=QU_GPOS_IN, QU_OUT = QU_OUT_FIX, QU_MODE = QU_MODE[layer], OF_MODE = OF_MODE[layer], IF_RST_N=IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])], N_PIPELINES=N_PIPELINES[layer],IF_GVAL=IF_GVAL[layer], IF_GIDX=IF_GIDX[layer],PORTS = inst_ports_comp)
            elif IF_GVAL[layer]:
                for comp_pos in range(n_comps):
                    inst_ports_comp = {
                        "i_data_2": f"gval_l{layer}[{2*comp_pos+1}*{QU_LAYERS[layer].DWT}-1:{2*comp_pos}*{QU_LAYERS[layer].DWT}]",
                        "i_data_1": f"gval_l{layer}[{2*comp_pos+2}*{QU_LAYERS[layer].DWT}-1:{2*comp_pos+1}*{QU_LAYERS[layer].DWT}]"
                    }
                    if IF_GVAL[layer]:
                        inst_ports_comp["o_gval" ]= f"gval_l{layer+1}[{comp_pos+1}*{QU_LAYERS[layer+1].DWT}-1:{comp_pos}*{QU_LAYERS[layer+1].DWT}]"
                    if N_PIPELINES[layer] > 0:
                        inst_ports_comp["i_clk"] = "i_clk"
                        if type(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]) == bool:
                            if(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                                inst_ports_comp["i_rst_n"] = "i_rst_n"
                        else:
                            if any(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                                inst_ports_comp["i_rst_n"] = "i_rst_n"
                    ModuleComp(QU_IN_1 = QU_IN_FIX, QU_IN_2 = QU_IN_FIX, QU_OUT = QU_OUT_FIX, QU_MODE = QU_MODE[layer], OF_MODE = OF_MODE[layer], IF_RST_N=IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])], N_PIPELINES=N_PIPELINES[layer],IF_GVAL=IF_GVAL[layer], IF_GIDX=IF_GIDX[layer],PORTS = inst_ports_comp)
            elif IF_LVAL[layer]:
                for comp_pos in range(n_comps):
                    inst_ports_comp = {
                        "i_data_2": f"lval_l{layer}[{2*comp_pos+1}*{QU_LAYERS[layer].DWT}-1:{2*comp_pos}*{QU_LAYERS[layer].DWT}]",
                        "i_data_1": f"lval_l{layer}[{2*comp_pos+2}*{QU_LAYERS[layer].DWT}-1:{2*comp_pos+1}*{QU_LAYERS[layer].DWT}]",
                        "o_lval": f"lval_l{layer+1}[{comp_pos+1}*{QU_LAYERS[layer+1].DWT}-1:{comp_pos}*{QU_LAYERS[layer+1].DWT}]",
                    }
                    if N_PIPELINES[layer] > 0:
                        inst_ports_comp["i_clk"] = "i_clk"
                        if any(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                            inst_ports_comp["i_rst_n"] = "i_rst_n"
                    ModuleComp(QU_IN_1 = QU_IN_FIX, QU_IN_2 = QU_IN_FIX, QU_OUT = QU_OUT_FIX, QU_MODE = QU_MODE[layer], OF_MODE = OF_MODE[layer], IF_RST_N=IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])], N_PIPELINES=N_PIPELINES[layer], IF_GVAL=False, IF_LVAL=True, IF_GIDX=False, PORTS = inst_ports_comp)



        if n_remainder == 1 and IF_LVAL[layer]:
            if layer == 0:
                remainder_source = f"data{layer}[{(2*n_operators-1)}*{QU_LAYERS[layer].DWT}-1:{(2*n_operators-2)}*{QU_LAYERS[layer].DWT}]"
            else:
                remainder_source = f"lval_l{layer}[{(2*n_operators-1)}*{QU_LAYERS[layer].DWT}-1:{(2*n_operators-2)}*{QU_LAYERS[layer].DWT}]"
            remainder_dest = f"lval_l{layer+1}[{n_operators}*{QU_LAYERS[layer+1].DWT}-1:{(n_operators-1)}*{QU_LAYERS[layer+1].DWT}]"
            same_type = (
                QU_IN_FIX.DWT == QU_OUT_FIX.DWT
                and QU_IN_FIX.FRAC == QU_OUT_FIX.FRAC
                and QU_IN_FIX.IF_SIGNED == QU_OUT_FIX.IF_SIGNED
            )
            if N_PIPELINES[layer] == 0 and same_type:
                # Exact odd forwarding in the qualified same-type MIN tree.
                #/ assign `remainder_dest` = `remainder_source`;
                pass
            else:
                #/ wire [`QU_LAYERS[layer].DWT`-1:0] lval_remainder_l`layer+1`;
                inst_ports_val = {
                    "i_data": remainder_source,
                    "o_data": f"lval_remainder_l{layer+1}",
                }
                if N_PIPELINES[layer] > 0:
                    inst_ports_val["i_clk"] = "i_clk"
                    if any(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                        inst_ports_val["i_rst_n"] = "i_rst_n"
                ModuleDelay(DWT=QU_IN_FIX.DWT, N_CLK=N_PIPELINES[layer], IF_RST_N=IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])], PORTS=inst_ports_val)
                if same_type:
                    #/ assign `remainder_dest` = lval_remainder_l`layer+1`;
                    pass
                else:
                    inst_ports_fx = {
                        "i_data": f"lval_remainder_l{layer+1}",
                        "o_data": remainder_dest,
                    }
                    ModuleFxMatch(QU_IN=QU_IN_FIX, QU_OUT=QU_OUT_FIX, QU_MODE=QU_MODE[layer], OF_MODE=OF_MODE[layer], N_CLK=0, IF_RST_N=False, PORTS=inst_ports_fx)

        if n_remainder == 1 and not IF_LVAL[layer]:
            #/ wire [`QU_LAYERS[layer].DWT`-1:0] remainder_val_l`layer+1`;
            #/ wire [`DWT_GPOS_LAYERS[layer + 1]`-1:0] remainder_pos_l`layer+1`;
            if layer == 0:
                if IF_GIDX[layer]:
                    #/ assign remainder_pos_l`layer+1` = 1'b0;
                    inst_ports_posn = {
                        "i_data": f"remainder_pos_l{layer+1}",
                        "o_data": f"gidx_l{layer+1}[{(n_operators)}*{DWT_GPOS_LAYERS[layer+1]}-1:{(n_operators-1)}*{DWT_GPOS_LAYERS[layer+1]}]"
                    }
                    if N_PIPELINES[layer] > 0:
                        inst_ports_posn["i_clk"] = "i_clk"
                        if type(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]) == bool:
                            if(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                                inst_ports_posn["i_rst_n"] = "i_rst_n"
                        else:
                            if any(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                                inst_ports_posn["i_rst_n"] = "i_rst_n"
                    ModuleDelay(DWT = 1, N_CLK = N_PIPELINES[layer], IF_RST_N = IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])], PORTS = inst_ports_posn)

                inst_ports_val = {
                    "i_data": f"data{layer}[{(2*n_operators-1)}*{QU_LAYERS[layer].DWT}-1:{(2*n_operators-2)}*{QU_LAYERS[layer].DWT}]",
                    "o_data": f"remainder_val_l{layer+1}"
                }
                if N_PIPELINES[layer] > 0:
                    inst_ports_val["i_clk"] = "i_clk"
                    if type(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]) == bool:
                        if(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                            inst_ports_val["i_rst_n"] = "i_rst_n"
                    else:
                        if any(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                            inst_ports_val["i_rst_n"] = "i_rst_n"
                ModuleDelay(DWT = QU_IN_FIX.DWT, N_CLK = N_PIPELINES[layer], IF_RST_N = IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])], PORTS = inst_ports_val)

                inst_ports_fx = {
                    "i_data":  f"remainder_val_l{layer+1}",
                    "o_data": f"gval_l{layer+1}[{n_operators}*{QU_LAYERS[layer+1].DWT}-1:{(n_operators-1)}*{QU_LAYERS[layer+1].DWT}]"
                }
                ModuleFxMatch(QU_IN=QU_IN_FIX, QU_OUT=QU_OUT_FIX, QU_MODE = QU_MODE[layer], OF_MODE = OF_MODE[layer], N_CLK=0, IF_RST_N=False, PORTS = inst_ports_fx)
            else:
                if IF_GIDX[layer]:
                    #/ assign remainder_pos_l`layer+1` = {1'b0, gidx_l`layer`[(2*`n_operators`-1)*`DWT_GPOS_LAYERS[layer]`-1:(2*`n_operators`-2)*`DWT_GPOS_LAYERS[layer]`]};
                    inst_ports_posn = {
                        "i_data": f"remainder_pos_l{layer+1}",
                        "o_data":  f"gidx_l{layer+1}[{(n_operators)}*{DWT_GPOS_LAYERS[layer+1]}-1:{(n_operators-1)}*{DWT_GPOS_LAYERS[layer+1]}]"
                    }
                    if N_PIPELINES[layer] > 0:
                        inst_ports_posn["i_clk"] = "i_clk"
                        if type(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]) == bool:
                            if(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                                inst_ports_posn["i_rst_n"] = "i_rst_n"
                        else:
                            if any(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                                inst_ports_posn["i_rst_n"] = "i_rst_n"
                    ModuleDelay(DWT = layer+1, N_CLK = N_PIPELINES[layer], IF_RST_N = IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])], PORTS = inst_ports_posn)
                inst_ports_val = {
                    "i_data":  f"gval_l{layer}[{(2*n_operators-1)}*{QU_LAYERS[layer].DWT}-1:{(2*n_operators-2)}*{QU_LAYERS[layer].DWT}]",
                    "o_data": f"remainder_val_l{layer+1}"
                }
                if N_PIPELINES[layer] > 0:
                    inst_ports_val["i_clk"] = "i_clk"
                    if type(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]) == bool:
                        if(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                            inst_ports_val["i_rst_n"] = "i_rst_n"
                    else:
                        if any(IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])]):
                            inst_ports_val["i_rst_n"] = "i_rst_n"
                ModuleDelay(DWT = QU_IN_FIX.DWT, N_CLK = N_PIPELINES[layer], IF_RST_N = IF_RST_N[sum(N_PIPELINES[:layer]):sum(N_PIPELINES[:layer+1])], PORTS = inst_ports_val)

                inst_ports_fx = {
                    "i_data":  f"remainder_val_l{layer+1}",
                    "o_data": f"gval_l{layer+1}[{n_operators}*{QU_LAYERS[layer+1].DWT}-1:{(n_operators-1)}*{QU_LAYERS[layer+1].DWT}]"
                }
                ModuleFxMatch(QU_IN=QU_IN_FIX, QU_OUT=QU_OUT_FIX, QU_MODE = QU_MODE[layer], OF_MODE = OF_MODE[layer], N_CLK=0, IF_RST_N=False, PORTS = inst_ports_fx)

    if IF_GVAL[n_layers - 1]:
        #/ assign o_gval = gval_l`n_layers`;
        pass
    if IF_LVAL[n_layers - 1]:
        #/ assign o_lval = lval_l`n_layers`;
        pass
    if IF_GIDX[0]:
        #/ assign o_gidx = gidx_l`n_layers`;
        pass
    #/ endmodule
if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    # moduleloader.saveParams()
    moduleloader.disEnableWarning()

    # ModuleAdd(QU_IN_1=QuType(9,3,True),QU_IN_2=QuType(10,4,True),QU_OUT=QuType(9,3,True),N_PIPELINES=0) # Combinational

    ModuleCompTree(QU_IN = QuType(10,2,True), QU_OUT = QuType(9,2,True), N_PIPELINES = 6,   IF_RST_N = True, IF_GIDX= True, IF_GVAL= True,CONFIG_MODE = "A") # Sequential
