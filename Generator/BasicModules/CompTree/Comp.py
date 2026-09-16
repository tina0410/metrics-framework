###################################################################################################
# Module Name: Comp
# Description: This module is used to Compare two fixed-point numbers.
# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
# Dependency Modules:
#   - Delay (1.0.0)
#   - FxMatch (1.0.0)
###########################################################################
import pytv
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

from enum import Enum

try:
    from .Delay import ModuleDelay
except ImportError:
    from Delay import ModuleDelay
try:
    from .FxMatch import ModuleFxMatch
except ImportError:
    from FxMatch import ModuleFxMatch
from Generator.BasicModules.Comp.Sub import ModuleSub
try:
    from .PyTU import QuMode, OfMode, QuType
except ImportError:
    from PyTU import QuMode, OfMode, QuType
# Explain Comp module here

@convert
def ModuleComp(QU_IN_1:QuType, QU_IN_2:QuType, QU_OUT:QuType, N_PIPELINES = 0, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N = False, IF_GIDX = False, IF_LIDX = False, IF_EIDX = False, IF_GVAL = False, IF_LVAL = False):
    # Parse the Input Args:
    if type(IF_RST_N) == bool:
        IF_RST_N = [IF_RST_N] * N_PIPELINES
        pass



    #/ module COMP(
    #/ i_data_1
    #/ ,i_data_2
    if IF_GIDX:
        #/ ,o_gidx
        pass
    if IF_LIDX:
        #/ ,o_lidx
        pass
    if IF_EIDX:
        #/ ,o_eidx
        pass
    if IF_GVAL:
        #/ ,o_gval
        pass
    if IF_LVAL:
        #/ ,o_lval
        pass


    if N_PIPELINES > 0:

        if any(IF_RST_N) == True:
            #/ ,i_rst_n
            pass


        #/ ,i_clk
    #/);

    #/ // Input and Output Ports

    #/ input wire [`QU_IN_1.DWT`-1:0] i_data_1;
    #/ input wire [`QU_IN_2.DWT`-1:0] i_data_2;
    if N_PIPELINES > 0:
        #/ input wire i_clk;
        if any(IF_RST_N) == True:
            #/ input wire i_rst_n;
            pass

    #/ wire [`QU_IN_1.DWT`-1:0] data_1;
    #/ wire [`QU_IN_2.DWT`-1:0] data_2;
    #/ assign data_1 = i_data_1;
    #/ assign data_2 = i_data_2;


    if IF_GIDX:
        #/ output wire o_gidx;
        pass
    if IF_LIDX:
        #/ output wire o_lidx;
        pass
    if IF_EIDX:
        #/ output wire o_eidx;
        pass
    if IF_GVAL:
        #/ output wire [`QU_OUT.DWT`-1:0] o_gval;
        pass
    if IF_LVAL:
        #/ output wire [`QU_OUT.DWT`-1:0] o_lval;
        pass



    QU_IN_FIX = QuType()

    LSB_FIX = -max(QU_IN_1.FRAC, QU_IN_2.FRAC)
    MSB_FIX = max(QU_IN_1.DWT - QU_IN_1.FRAC , QU_IN_2.DWT - QU_IN_2.FRAC+1)

    QU_IN_FIX.DWT = MSB_FIX - LSB_FIX + 1
    QU_IN_FIX.FRAC = -LSB_FIX
    QU_IN_FIX.IF_SIGNED = QU_IN_1.IF_SIGNED or QU_IN_2.IF_SIGNED

    if IF_GVAL or IF_LVAL:
        #/ // FxMatch for Output Fix
        #/ wire [`QU_OUT.DWT`-1:0] data_1_fixed;
        #/ wire [`QU_OUT.DWT`-1:0] data_2_fixed;
        inst_ports_fxmatch_1 = {
            "i_data": "data_1",
            "o_data": "data_1_fixed"
        }
        ModuleFxMatch(QU_IN = QU_IN_1, QU_OUT = QU_OUT, QU_MODE = QU_MODE, OF_MODE = OF_MODE, N_CLK = 0, IF_RST_N = False, PORTS = inst_ports_fxmatch_1)

        inst_ports_fxmatch_2 = {
            "i_data": "data_2",
            "o_data": "data_2_fixed"
        }
        ModuleFxMatch(QU_IN = QU_IN_2, QU_OUT = QU_OUT, QU_MODE = QU_MODE, OF_MODE = OF_MODE, N_CLK = 0, IF_RST_N = False, PORTS = inst_ports_fxmatch_2)
        pass

    # Unsigned Value Comparison
    if QU_IN_FIX.IF_SIGNED == False:
        #/ // Unsigned Value Comparison
        if IF_GIDX:
            #/ wire greater_sign;
            #/ assign greater_sign = (data_1 > data_2) ? 1'b1 : 1'b0;
            inst_ports = {
                "i_data": "greater_sign",
                "o_data": "o_gidx"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"

            ModuleDelay(DWT = 1, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
        if IF_LIDX:
            #/ wire lesser_sign;
            #/ assign lesser_sign = (data_1 < data_2) ? 1'b1 : 1'b0;
            inst_ports = {
                "i_data": "lesser_sign",
                "o_data": "o_lidx"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"
            ModuleDelay(DWT = 1, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
        if IF_EIDX:
            #/ wire equal_sign;
            #/ assign equal_sign = (data_1 == data_2) ? 1'b1 : 1'b0;
            inst_ports = {
                "i_data": "equal_sign",
                "o_data": "o_eidx"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"
            ModuleDelay(DWT = 1, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
        if IF_GVAL:
            #/ wire [`QU_OUT.DWT`-1:0] greater_value;
            #/ assign greater_value = (data_1 > data_2) ? data_1_fixed : data_2_fixed;
            inst_ports = {
                "i_data": "greater_value",
                "o_data": "o_gval"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"

            ModuleDelay(DWT = QU_OUT.DWT, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
        if IF_LVAL:
            #/ wire [`QU_OUT.DWT`-1:0] smaller_value;
            #/ assign smaller_value = (data_1 < data_2) ? data_1_fixed : data_2_fixed;
            inst_ports = {
                "i_data": "smaller_value",
                "o_data": "o_lval"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"

            ModuleDelay(DWT = QU_OUT.DWT, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
    else: # Signed
        #/ wire [`QU_IN_FIX.DWT`-1:0] comp_result;
        # ModuleSub
        inst_ports_sub = {
            "i_data_1": "data_1",
            "i_data_2": "data_2",
            "o_data": "comp_result"
        }
        ModuleSub(QU_IN_1=QU_IN_1, QU_IN_2=QU_IN_2, QU_OUT=QU_IN_FIX, N_CLK=0, QU_MODE = QuMode.TRN.TCPL, OF_MODE = OfMode.WRP.TCPL, IF_RST_N=False, PORTS = inst_ports_sub)
        #/ // Signed Value Comparison
        if IF_GIDX:
            #/ wire greater_sign;
            #/ assign greater_sign = (comp_result[`QU_IN_FIX.DWT`-1] == 1'b0 && comp_result != {`QU_IN_FIX.DWT`{1'b0}} ) ? 1'b1 : 1'b0;
            # Delay Module
            inst_ports = {
                "i_data": "greater_sign",
                "o_data": "o_gidx"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"

            ModuleDelay(DWT = 1, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
        if IF_LIDX:
            #/ wire lesser_sign;
            #/ assign lesser_sign = (comp_result[`QU_IN_FIX.DWT`-1] == 1'b1) ? 1'b1 : 1'b0;
            # Delay Module
            inst_ports = {
                "i_data": "lesser_sign",
                "o_data": "o_lidx"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"

            ModuleDelay(DWT = 1, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
        if IF_EIDX:
            #/ wire equal_sign;
            #/ assign equal_sign = (comp_result == 0) ? 1'b1 : 1'b0;
            # Delay Module
            inst_ports = {
                "i_data": "equal_sign",
                "o_data": "o_eidx"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"

            ModuleDelay(DWT = 1, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
        if IF_GVAL:
            #/ wire [`QU_OUT.DWT`-1:0] greater_value;
            #/ assign greater_value = ((comp_result[`QU_IN_FIX.DWT`-1] == 1'b0) && (comp_result != {`QU_IN_FIX.DWT`{1'b0}})) ? data_1_fixed : data_2_fixed;
            # Delay Module
            inst_ports = {
                "i_data": "greater_value",
                "o_data": "o_gval"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"

            ModuleDelay(DWT = QU_OUT.DWT, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
        if IF_LVAL:
            #/ wire [`QU_OUT.DWT`-1:0] smaller_value;
            #/ assign smaller_value = (comp_result[`QU_IN_FIX.DWT`-1] == 1'b1) ? data_1_fixed : data_2_fixed;
            # Delay Module
            inst_ports = {
                "i_data": "smaller_value",
                "o_data": "o_lval"
            }
            if N_PIPELINES > 0:
                inst_ports["i_clk"] = "i_clk"
                if any(IF_RST_N):
                    inst_ports["i_rst_n"] = "i_rst_n"

            ModuleDelay(DWT = QU_OUT.DWT, N_CLK = N_PIPELINES, IF_RST_N = IF_RST_N, PORTS = inst_ports)
            pass
            pass



    #/ endmodule
if __name__ == "__main__":
    moduleloader.set_root_dir("./RTL")
    moduleloader.set_naming_mode("SEQUENTIAL")
    # moduleloader.saveParams()
    moduleloader.disEnableWarning()

    # ModuleAdd(QU_IN_1=QuType(9,3,True),QU_IN_2=QuType(10,4,True),QU_OUT=QuType(9,3,True),N_PIPELINES=0) # Combinational

    ModuleComp(QU_IN_1 = QuType(5,4,True), QU_IN_2 = QuType(5,3,True), QU_OUT = QuType(5,2,True), N_PIPELINES = 4, IF_RST_N = True, IF_GIDX = True, IF_LIDX = True, IF_EIDX = True, IF_GVAL = True, IF_LVAL = True) # Sequential
