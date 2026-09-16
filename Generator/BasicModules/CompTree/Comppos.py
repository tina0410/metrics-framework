"""Comparison helper that propagates the winning operand position."""

from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

try:
    from .Delay import ModuleDelay
    from .FxMatch import ModuleFxMatch
    from .PyTU import OfMode, QuMode, QuType
except ImportError:
    from Delay import ModuleDelay
    from FxMatch import ModuleFxMatch
    from PyTU import OfMode, QuMode, QuType


@convert
def ModuleComppos(QU_IN_1: QuType, QU_IN_2: QuType, QU_GPOS_IN: QuType, QU_OUT: QuType, N_PIPELINES=0, QU_MODE=QuMode.TRN.TCPL, OF_MODE=OfMode.WRP.TCPL, IF_RST_N=False, IF_GVAL=True, IF_GIDX=True):
    if isinstance(IF_RST_N, bool):
        IF_RST_N = [IF_RST_N] * N_PIPELINES

    #/ module COMPPOS(
    #/     i_data_1, i_data_2, i_data_gpos_1, i_data_gpos_2
    if IF_GVAL:
        #/     , o_gval
        pass
    if IF_GIDX:
        #/     , o_gidx
        pass
    if N_PIPELINES > 0:
        #/     , i_clk
        if any(IF_RST_N):
            #/     , i_rst_n
            pass
    #/ );

    #/ input wire [`QU_IN_1.DWT`-1:0] i_data_1;
    #/ input wire [`QU_IN_2.DWT`-1:0] i_data_2;
    #/ input wire [`QU_GPOS_IN.DWT`-1:0] i_data_gpos_1;
    #/ input wire [`QU_GPOS_IN.DWT`-1:0] i_data_gpos_2;
    if IF_GVAL:
        #/ output wire [`QU_OUT.DWT`-1:0] o_gval;
        pass
    if IF_GIDX:
        #/ output wire [`QU_GPOS_IN.DWT`:0] o_gidx;
        pass
    if N_PIPELINES > 0:
        #/ input wire i_clk;
        if any(IF_RST_N):
            #/ input wire i_rst_n;
            pass

    if QU_IN_1.IF_SIGNED or QU_IN_2.IF_SIGNED:
        #/ wire choose_first;
        #/ assign choose_first = $signed(i_data_1) > $signed(i_data_2);
        pass
    else:
        #/ wire choose_first;
        #/ assign choose_first = i_data_1 > i_data_2;
        pass

    if IF_GVAL:
        #/ wire [`QU_IN_1.DWT`-1:0] greater_value_raw;
        #/ wire [`QU_OUT.DWT`-1:0] greater_value_fixed;
        #/ assign greater_value_raw = choose_first ? i_data_1 : i_data_2;
        ModuleFxMatch(QU_IN=QU_IN_1, QU_OUT=QU_OUT, QU_MODE=QU_MODE, OF_MODE=OF_MODE, N_CLK=0, IF_RST_N=False, PORTS={"i_data": "greater_value_raw", "o_data": "greater_value_fixed"})
        value_ports = {"i_data": "greater_value_fixed", "o_data": "o_gval"}
        if N_PIPELINES > 0:
            value_ports["i_clk"] = "i_clk"
            if any(IF_RST_N):
                value_ports["i_rst_n"] = "i_rst_n"
        ModuleDelay(DWT=QU_OUT.DWT, N_CLK=N_PIPELINES, IF_RST_N=IF_RST_N, PORTS=value_ports)

    if IF_GIDX:
        GPOS_OUT_DWT = QU_GPOS_IN.DWT + 1
        #/ wire [`GPOS_OUT_DWT`-1:0] greater_position;
        #/ assign greater_position = choose_first ? {{1{1'b0}}, i_data_gpos_1} : {{1{1'b0}}, i_data_gpos_2};
        index_ports = {"i_data": "greater_position", "o_data": "o_gidx"}
        if N_PIPELINES > 0:
            index_ports["i_clk"] = "i_clk"
            if any(IF_RST_N):
                index_ports["i_rst_n"] = "i_rst_n"
        ModuleDelay(DWT=GPOS_OUT_DWT, N_CLK=N_PIPELINES, IF_RST_N=IF_RST_N, PORTS=index_ports)

    #/ endmodule


__all__ = ["ModuleComppos"]
