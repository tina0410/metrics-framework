###################################################################################################
# Module Name: AdderTree
# Description: This module is used to sum multiple inputs fixed-point numbers.
# Author: Yifang Dai
# Date: 2025.4.7
# Version: V0.1.0
# Doc Version: V0.1.0
# Dependency Modules: 
#   - Delay (V 0.1.0)
#   - FxMatch (V 0.2.1)
###########################################################################
import sys
from os.path import dirname
sys.path.append(dirname(dirname(__file__)))
sys.path.append(dirname(__file__))

from pytv.Converter import convert  # type: ignore
from pytv.ModuleLoader import moduleloader  # type: ignore


from enum import Enum
from PyTU import QuMode, OfMode, QuType
from Delay import ModuleDelay
from FxMatch import ModuleFxMatch
from Add import ModuleAdd
import math 
from typing import Literal

def has_non_zero(var):
    if isinstance(var, (int, float)):
        return var != 0
    elif isinstance(var, (list, tuple)):  
        return any(x != 0 for x in var)
    else:
        return True
    
@convert
def ModuleAdderTree(QU_IN: QuType | list[QuType], QU_OUT: QuType, N_PIPELINES: int | list, QU_MODE: QuMode.TRN | QuMode.RND | list, OF_MODE: OfMode.WRP | OfMode.SAT | list, IF_RST_N: bool, N_INPUTS: int, CONFIG_MODE: Literal['A'] | Literal['B'] | Literal['C']):
    """
    Adder Tree module — sums N_INPUTS fixed-point numbers via a binary tree of adders.

    Three configuration modes are supported:

    **Mode A (Uniform):**
        All layers share the same QU_MODE, OF_MODE.  A single N_PIPELINES integer
        is distributed evenly across ceil(log2(N_INPUTS)) layers.  Intermediate
        word-widths grow by 1 bit per layer starting from QU_IN; the final layer
        is matched to QU_OUT.

        Example:
            ModuleAdderTree(QU_IN=QuType(10,2,True), QU_OUT=QuType(12,2,True),
                            N_PIPELINES=4, QU_MODE=QuMode.TRN.TCPL,
                            OF_MODE=OfMode.WRP.TCPL, IF_RST_N=True,
                            N_INPUTS=8, CONFIG_MODE='A')

    **Mode B (Per-Layer):**
        Each layer's quantization format, quantization/overflow mode, and pipeline
        depth are specified individually via lists.  QU_IN is a list of QuTypes
        (one per layer, length == ceil(log2(N_INPUTS))).  N_PIPELINES, QU_MODE,
        and OF_MODE are also lists of the same length.

        Example:
            ModuleAdderTree(QU_IN=[QuType(10,2,True), QuType(9,2,True)],
                            QU_OUT=QuType(9,2,True), N_PIPELINES=[2,3],
                            QU_MODE=[QuMode.TRN.TCPL, QuMode.TRN.TCPL],
                            OF_MODE=[OfMode.WRP.TCPL, OfMode.WRP.TCPL],
                            IF_RST_N=True, N_INPUTS=4, CONFIG_MODE='B')

    **Mode C (Reserved):**
        Not yet implemented.

    :param QU_IN: QuType(10, 2, True)
        Mode A: single QuType for all inputs.
        Mode B: list of QuType, one per tree layer.
    :type QU_IN: QuType | list
    :param QU_OUT: QuType(9, 2, True)
        Quantization type of the final output.
    :type QU_OUT: QuType
    :param N_PIPELINES: 4
        Mode A: total pipeline stages (distributed across layers).
        Mode B: list of pipeline stages per layer.
    :type N_PIPELINES: int | list
    :param QU_MODE: QuMode.TRN.TCPL
        Mode A: single quantization mode for all layers.
        Mode B: list of quantization modes per layer.
    :type QU_MODE: QuMode.TRN | QuMode.RND | list
    :param OF_MODE: OfMode.WRP.TCPL
        Mode A: single overflow mode for all layers.
        Mode B: list of overflow modes per layer.
    :type OF_MODE: OfMode.WRP | OfMode.SAT | list
    :param IF_RST_N: True
        Whether pipeline registers use asynchronous reset.
    :type IF_RST_N: bool
    :param N_INPUTS: 4
        Number of input operands to sum.
    :type N_INPUTS: int
    :param CONFIG_MODE: 'A'
        Configuration mode selector: 'A', 'B', or 'C'.
    :type CONFIG_MODE: Literal['A'] | Literal['B'] | Literal['C']
    """

    #----------------------------------------------------------------------------------
    n_layers = math.ceil(math.log2(N_INPUTS))

    QU_LAYERS: list[QuType] = [QuType(0, 0, True) for _ in range(n_layers+1)]  

    # Normalize all per-layer parameters into lists 
    N_PIPELINES_LIST: list[int]
    QU_MODE_LIST: list
    OF_MODE_LIST: list
    IF_RST_N_LIST: list[bool]

    if CONFIG_MODE == "A":
        # prevent QuType vs QuType list confusion
        if not isinstance(QU_IN, QuType) and type(QU_IN).__name__ != 'QuType':
            raise TypeError(f"Mode A requires QU_IN to be a single QuType, currently {type(QU_IN)}") 
        if not isinstance(N_PIPELINES, int):
            raise TypeError(f"Mode A requires N_PIPELINES to be an int, currently {type(N_PIPELINES)}")
        # Expand scalar IF_RST_N → flat list of length N_PIPELINES
        IF_RST_N_LIST = [IF_RST_N] * N_PIPELINES
        # Replicate scalar modes across all layers
        QU_MODE_LIST = [QU_MODE] * n_layers
        OF_MODE_LIST = [OF_MODE] * n_layers
        # Distribute total pipeline stages evenly across layers
        base_pipelines = N_PIPELINES // n_layers
        extra_pipelines = N_PIPELINES % n_layers
        N_PIPELINES_LIST = [
            base_pipelines if i < n_layers - extra_pipelines else base_pipelines + 1
            for i in range(n_layers)
        ]
        # Build QU_LAYERS: widths grow by 1 bit per layer from QU_IN
        QU_LAYERS[0].IF_SIGNED = QU_IN.IF_SIGNED
        for i in range(n_layers):
            QU_LAYERS[i].DWT = QU_IN.DWT + i
            QU_LAYERS[i].FRAC = QU_IN.FRAC
        QU_LAYERS[n_layers].DWT = QU_OUT.DWT
        QU_LAYERS[n_layers].FRAC = QU_OUT.FRAC

    elif CONFIG_MODE == "B":
        if not isinstance(QU_IN, list):
            raise TypeError("Mode B requires QU_IN to be a list of QuType")
        if not isinstance(N_PIPELINES, list):
            raise TypeError("Mode B requires N_PIPELINES to be a list of int")
        if not isinstance(QU_MODE, list):
            raise TypeError("Mode B requires QU_MODE to be a list")
        if not isinstance(OF_MODE, list):
            raise TypeError("Mode B requires OF_MODE to be a list")
        N_PIPELINES_LIST = N_PIPELINES
        QU_MODE_LIST = QU_MODE
        OF_MODE_LIST = OF_MODE
        IF_RST_N_LIST = [IF_RST_N] * sum(N_PIPELINES_LIST)
        # Build QU_LAYERS from per-layer QU_IN list
        QU_LAYERS[0].IF_SIGNED = any(item.IF_SIGNED for item in QU_IN)
        for i in range(n_layers):
            QU_LAYERS[i].DWT = QU_IN[i].DWT
            QU_LAYERS[i].FRAC = QU_IN[i].FRAC
        QU_LAYERS[n_layers].DWT = QU_OUT.DWT
        QU_LAYERS[n_layers].FRAC = QU_OUT.FRAC

    else:
        raise NotImplementedError(f"CONFIG_MODE '{CONFIG_MODE}' is not supported")

    #/ `timescale 1ns / 1ps
    #/ module ADDERTREE(
    #/     i_data,
    #/     o_data
    if has_non_zero(N_PIPELINES_LIST):
        if any(IF_RST_N_LIST):
            #/ , i_rst_n
            pass
        #/ , i_clk
        pass
    #/ );

    #/ // Input and Output Ports
    #/ input                          wire [`QU_LAYERS[0].DWT * N_INPUTS`-1:0] i_data;
    #/ output wire [`QU_OUT.DWT`-1:0] o_data;
    if has_non_zero(N_PIPELINES_LIST):
        #/ input wire i_clk;
        if any(IF_RST_N_LIST):
            #/ input wire i_rst_n;
            pass
    #/ wire [`QU_LAYERS[0].DWT * N_INPUTS`-1:0] data0;
    #/ assign data0 = i_data;
    n_operators = N_INPUTS

    for layer in range(n_layers):
        n_remainder = n_operators % 2
        n_adders = n_operators // 2
        n_operators = n_adders + n_remainder
        
        #/ wire [`n_operators*QU_LAYERS[layer+1].DWT`-1:0] data`layer+1`;
        QU_IN_FIX = QuType(0, 0, True)
        QU_OUT_FIX = QuType(0, 0, True)
        QU_IN_FIX.DWT = QU_LAYERS[layer].DWT
        QU_IN_FIX.FRAC = QU_LAYERS[layer].FRAC
        QU_IN_FIX.IF_SIGNED = QU_LAYERS[0].IF_SIGNED
        QU_OUT_FIX.DWT = QU_LAYERS[layer+1].DWT
        QU_OUT_FIX.FRAC = QU_LAYERS[layer+1].FRAC
        QU_OUT_FIX.IF_SIGNED = QU_LAYERS[0].IF_SIGNED
        rst_n_slice = IF_RST_N_LIST[sum(N_PIPELINES_LIST[:layer]):sum(N_PIPELINES_LIST[:layer+1])]
        for adder in range(n_adders):
            inst_ports_add = {
                "i_data_1": f"data{layer}[{2*adder+1}*{QU_LAYERS[layer].DWT}-1:{2*adder}*{QU_LAYERS[layer].DWT}]",
                "i_data_2": f"data{layer}[{2*adder+2}*{QU_LAYERS[layer].DWT}-1:{2*adder+1}*{QU_LAYERS[layer].DWT}]",
                "o_data": f"data{layer+1}[{adder+1}*{QU_LAYERS[layer+1].DWT}-1:{adder}*{QU_LAYERS[layer+1].DWT}]"
            }
            if N_PIPELINES_LIST[layer] > 0:
                inst_ports_add["i_clk"] = "i_clk"
                if any(rst_n_slice):
                    inst_ports_add["i_rst_n"] = "i_rst_n"
            ModuleAdd(QU_IN_1 = QU_IN_FIX, QU_IN_2 = QU_IN_FIX, QU_OUT = QU_OUT_FIX, N_CLK=N_PIPELINES_LIST[layer], QU_MODE = QU_MODE_LIST[layer], OF_MODE = OF_MODE_LIST[layer], IF_RST_N=any(rst_n_slice), PORTS = inst_ports_add)  # type: ignore[call-arg]

        if n_remainder == 1:
            #/ wire [`QU_LAYERS[layer].DWT`-1:0] remainder_l`layer+1`;
            inst_ports_delay = {
                "i_data": f"data{layer}[{(2*n_operators-1)}*{QU_LAYERS[layer].DWT}-1:{(2*n_operators-2)}*{QU_LAYERS[layer].DWT}]",
                "o_data": f"remainder_l{layer+1}"
            }
            if N_PIPELINES_LIST[layer] > 0:
                inst_ports_delay["i_clk"] = "i_clk"
                if any(rst_n_slice):
                    inst_ports_delay["i_rst_n"] = "i_rst_n"

                ModuleDelay(DWT = QU_IN_FIX.DWT, N_CLK = N_PIPELINES_LIST[layer], IF_RST_N = any(rst_n_slice), PORTS = inst_ports_delay)  # type: ignore[call-arg]
            
                inst_ports_fxmatch_1 = {
                    "i_data": f"remainder_l{layer+1}",
                    "o_data":  f"data{layer+1}[{n_operators}*{QU_LAYERS[layer+1].DWT}-1:{(n_operators-1)}*{QU_LAYERS[layer+1].DWT}]"
                }
                ModuleFxMatch(QU_IN=QU_IN_FIX, QU_OUT=QU_OUT_FIX, QU_MODE = QU_MODE_LIST[layer], OF_MODE = OF_MODE_LIST[layer], N_CLK=0, IF_RST_N=False, PORTS = inst_ports_fxmatch_1)  # type: ignore[call-arg]
            else:
                inst_ports_fxmatch_1 = {
                    "i_data": f"data{layer}[{(2*n_operators-1)}*{QU_LAYERS[layer].DWT}-1:{(2*n_operators-2)}*{QU_LAYERS[layer].DWT}]",
                    "o_data":  f"data{layer+1}[{n_operators}*{QU_LAYERS[layer+1].DWT}-1:{(n_operators-1)}*{QU_LAYERS[layer+1].DWT}]"
                }
                ModuleFxMatch(QU_IN=QU_IN_FIX, QU_OUT=QU_OUT_FIX, QU_MODE = QU_MODE_LIST[layer], OF_MODE = OF_MODE_LIST[layer], N_CLK=0, IF_RST_N=False, PORTS = inst_ports_fxmatch_1)  # type: ignore[call-arg]
    
    #/ assign o_data = data`n_layers`;
    #/ endmodule
if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")  # type: ignore
    moduleloader.set_naming_mode("SEQUENTIAL")  # type: ignore
    moduleloader.disEnableWarning()  # type: ignore

    ModuleAdderTree(QU_IN = [QuType(10,2,True),QuType(9,2,True)], QU_OUT = QuType(9,2,True), N_PIPELINES = [2,3],  QU_MODE = [QuMode.TRN.TCPL,QuMode.TRN.TCPL], OF_MODE = [OfMode.WRP.TCPL,OfMode.WRP.TCPL], IF_RST_N = True, N_INPUTS = 4, CONFIG_MODE = "B") # Sequential
