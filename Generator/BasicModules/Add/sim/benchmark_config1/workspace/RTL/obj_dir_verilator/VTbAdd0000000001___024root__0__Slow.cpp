// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VTbAdd0000000001.h for the primary calling header

#include "VTbAdd0000000001__pch.h"

void VTbAdd0000000001___024root___timing_ready(VTbAdd0000000001___024root* vlSelf);

VL_ATTR_COLD void VTbAdd0000000001___024root___eval_static(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_static\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0 
        = vlSelfRef.TbAdd0000000001__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__en__0 
        = vlSelfRef.TbAdd0000000001__DOT__en;
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Input_rdy__0 
        = vlSelfRef.TbAdd0000000001__DOT__Input_rdy;
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Output_rdy__0 
        = vlSelfRef.TbAdd0000000001__DOT__Output_rdy;
    VTbAdd0000000001___024root___timing_ready(vlSelf);
    do {
        vlSelfRef.__VactTriggeredAcc[vlSelfRef.__Vi] 
            = vlSelfRef.__VactTriggered[vlSelfRef.__Vi];
        vlSelfRef.__Vi = ((IData)(1U) + vlSelfRef.__Vi);
    } while ((0U >= vlSelfRef.__Vi));
}

VL_ATTR_COLD void VTbAdd0000000001___024root___eval_initial__TOP(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial__TOP\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.TbAdd0000000001__DOT__i_data_1 = 0U;
    vlSelfRef.TbAdd0000000001__DOT__i_data_2 = 0U;
    vlSymsp->_vm_contextp__->dumpfile("wave.vcd"s);
    vlSymsp->_traceDumpOpen();
}

VL_ATTR_COLD void VTbAdd0000000001___024root___eval_final(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_final\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
}

VL_ATTR_COLD void VTbAdd0000000001___024root___eval_settle(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_settle\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
}

bool VTbAdd0000000001___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in);

#ifdef VL_DEBUG
VL_ATTR_COLD void VTbAdd0000000001___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___dump_triggers__act\n"); );
    // Body
    if ((1U & (~ (IData)(VTbAdd0000000001___024root___trigger_anySet__act(triggers))))) {
        VL_DBG_MSGS("         No '" + tag + "' region triggers active\n");
    }
    if ((1U & (IData)(triggers[0U]))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: @(posedge TbAdd0000000001.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 1U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 1 is active: @([true] __VdlySched.awaitingCurrentTime())\n");
    }
    if ((1U & (IData)((triggers[0U] >> 2U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 2 is active: @(negedge TbAdd0000000001.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 3U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 3 is active: @(posedge TbAdd0000000001.en)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 4U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 4 is active: @(posedge TbAdd0000000001.Input_rdy)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 5U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 5 is active: @(posedge TbAdd0000000001.Output_rdy)\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void VTbAdd0000000001___024root___ctor_var_reset(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___ctor_var_reset\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    const uint64_t __VscopeHash = VL_MURMUR64_HASH(vlSelf->vlNamep);
    vlSelf->TbAdd0000000001__DOT__Input_i_data_1 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14271562907772984523ull);
    vlSelf->TbAdd0000000001__DOT__Input_i_data_2 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16475284528028893474ull);
    vlSelf->TbAdd0000000001__DOT__i_data_1 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1032163260340863057ull);
    vlSelf->TbAdd0000000001__DOT__i_data_2 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8681215700479140143ull);
    vlSelf->TbAdd0000000001__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13551378423152300912ull);
    vlSelf->TbAdd0000000001__DOT__en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13066658473445353226ull);
    vlSelf->TbAdd0000000001__DOT__i_rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12377267855829164161ull);
    vlSelf->TbAdd0000000001__DOT__Input_rdy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14135483781072161374ull);
    vlSelf->TbAdd0000000001__DOT__Output_rdy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 677101802963866572ull);
    vlSelf->TbAdd0000000001__DOT__Input_rdy_iter = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 8626608663719241367ull);
    vlSelf->TbAdd0000000001__DOT__Output_rdy_iter = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2098480963740792730ull);
    vlSelf->TbAdd0000000001__DOT__i_data_1_dat = 0;
    vlSelf->TbAdd0000000001__DOT__i_data_1_st = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 3272539340511755790ull);
    vlSelf->TbAdd0000000001__DOT__i_data_2_dat = 0;
    vlSelf->TbAdd0000000001__DOT__i_data_2_st = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2589680915074199902ull);
    vlSelf->TbAdd0000000001__DOT__o_data_dat = 0;
    vlSelf->TbAdd0000000001__DOT__o_data_iter = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 3253087591634101963ull);
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->TbAdd0000000001__DOT__u_0000000001_Add0000000001__DOT__u_0000000001_Delay0000000003__DOT__data_d[__Vi0] = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13240197525183908837ull);
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggeredAcc[__Vi0] = 0;
    }
    vlSelf->__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__en__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Input_rdy__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Output_rdy__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
    vlSelf->__Vi = 0;
    for (int __Vi0 = 0; __Vi0 < 4; ++__Vi0) {
        vlSelf->__Vm_traceActivity[__Vi0] = 0;
    }
}
