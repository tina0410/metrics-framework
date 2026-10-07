// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Tracing implementation internals

#include "verilated_vcd_c.h"
#include "VTbAdd0000000001__Syms.h"


void VTbAdd0000000001___024root__trace_chg_0_sub_0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp);

void VTbAdd0000000001___024root__trace_chg_0(void* voidSelf, VerilatedVcd::Buffer* bufp) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_chg_0\n"); );
    // Body
    VTbAdd0000000001___024root* const __restrict vlSelf VL_ATTR_UNUSED = static_cast<VTbAdd0000000001___024root*>(voidSelf);
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    if (VL_UNLIKELY(!vlSymsp->__Vm_activity)) return;
    VTbAdd0000000001___024root__trace_chg_0_sub_0((&vlSymsp->TOP), bufp);
}

void VTbAdd0000000001___024root__trace_chg_dtype____0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp, uint32_t offset, const VlUnpacked<CData/*0:0*/, 1>& __VdtypeVar);

void VTbAdd0000000001___024root__trace_chg_0_sub_0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_chg_0_sub_0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    uint32_t* const oldp VL_ATTR_UNUSED = bufp->oldp(vlSymsp->__Vm_baseCode + 0);
    if (VL_UNLIKELY(((vlSelfRef.__Vm_traceActivity[1U] 
                      | vlSelfRef.__Vm_traceActivity[2U])))) {
        bufp->chgBit(oldp+0,(vlSelfRef.TbAdd0000000001__DOT__Input_i_data_1));
        bufp->chgBit(oldp+1,(vlSelfRef.TbAdd0000000001__DOT__i_data_1));
        bufp->chgIData(oldp+2,(vlSelfRef.TbAdd0000000001__DOT__i_data_1_dat),32);
        bufp->chgIData(oldp+3,(vlSelfRef.TbAdd0000000001__DOT__i_data_1_st),32);
        bufp->chgCData(oldp+4,(vlSelfRef.TbAdd0000000001__DOT__i_data_1),2);
        bufp->chgCData(oldp+5,(vlSelfRef.TbAdd0000000001__DOT__i_data_1),3);
    }
    if (VL_UNLIKELY(((vlSelfRef.__Vm_traceActivity[1U] 
                      | vlSelfRef.__Vm_traceActivity[3U])))) {
        bufp->chgBit(oldp+6,(vlSelfRef.TbAdd0000000001__DOT__Input_i_data_2));
        bufp->chgBit(oldp+7,(vlSelfRef.TbAdd0000000001__DOT__i_data_2));
        bufp->chgIData(oldp+8,(vlSelfRef.TbAdd0000000001__DOT__i_data_2_dat),32);
        bufp->chgIData(oldp+9,(vlSelfRef.TbAdd0000000001__DOT__i_data_2_st),32);
        bufp->chgCData(oldp+10,(vlSelfRef.TbAdd0000000001__DOT__i_data_2),2);
        bufp->chgCData(oldp+11,(vlSelfRef.TbAdd0000000001__DOT__i_data_2),3);
    }
    bufp->chgBit(oldp+12,(vlSelfRef.TbAdd0000000001__DOT__clk));
    bufp->chgBit(oldp+13,(vlSelfRef.TbAdd0000000001__DOT__en));
    bufp->chgBit(oldp+14,(vlSelfRef.TbAdd0000000001__DOT__i_rst_n));
    bufp->chgBit(oldp+15,(vlSelfRef.TbAdd0000000001__DOT__u_0000000001_Add0000000001__DOT__u_0000000001_Delay0000000003__DOT__data_d[0U]));
    bufp->chgBit(oldp+16,(vlSelfRef.TbAdd0000000001__DOT__Input_rdy));
    bufp->chgBit(oldp+17,(vlSelfRef.TbAdd0000000001__DOT__Output_rdy));
    bufp->chgIData(oldp+18,(vlSelfRef.TbAdd0000000001__DOT__Input_rdy_iter),32);
    bufp->chgIData(oldp+19,(vlSelfRef.TbAdd0000000001__DOT__Output_rdy_iter),32);
    bufp->chgIData(oldp+20,(vlSelfRef.TbAdd0000000001__DOT__o_data_dat),32);
    bufp->chgIData(oldp+21,(vlSelfRef.TbAdd0000000001__DOT__o_data_iter),32);
    bufp->chgCData(oldp+22,((3U & ((IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_2) 
                                   + (IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_1)))),2);
    VTbAdd0000000001___024root__trace_chg_dtype____0(vlSelf, bufp, 23, vlSelfRef.TbAdd0000000001__DOT__u_0000000001_Add0000000001__DOT__u_0000000001_Delay0000000003__DOT__data_d);
    bufp->chgCData(oldp+24,((3U & ((IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_2) 
                                   + (IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_1)))),3);
    bufp->chgCData(oldp+25,((2U & (((IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_2) 
                                    + (IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_1)) 
                                   << 1U))),2);
    bufp->chgCData(oldp+26,((6U & (((IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_2) 
                                    + (IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_1)) 
                                   << 1U))),4);
}

void VTbAdd0000000001___024root__trace_chg_dtype____0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp, uint32_t offset, const VlUnpacked<CData/*0:0*/, 1>& __VdtypeVar) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_chg_dtype____0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    uint32_t* const oldp VL_ATTR_UNUSED = bufp->oldp(vlSymsp->__Vm_baseCode +  offset);
    bufp->chgBit(oldp+0,(__VdtypeVar[0]));
}

void VTbAdd0000000001___024root__trace_cleanup(void* voidSelf, VerilatedVcd* /*unused*/) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_cleanup\n"); );
    // Body
    VTbAdd0000000001___024root* const __restrict vlSelf VL_ATTR_UNUSED = static_cast<VTbAdd0000000001___024root*>(voidSelf);
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    vlSymsp->__Vm_activity = false;
    vlSymsp->TOP.__Vm_traceActivity[0U] = 0U;
    vlSymsp->TOP.__Vm_traceActivity[1U] = 0U;
    vlSymsp->TOP.__Vm_traceActivity[2U] = 0U;
    vlSymsp->TOP.__Vm_traceActivity[3U] = 0U;
}
