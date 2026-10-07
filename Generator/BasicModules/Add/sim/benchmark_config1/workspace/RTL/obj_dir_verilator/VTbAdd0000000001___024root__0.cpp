// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VTbAdd0000000001.h for the primary calling header

#include "VTbAdd0000000001__pch.h"

VL_ATTR_COLD void VTbAdd0000000001___024root___eval_initial__TOP(VTbAdd0000000001___024root* vlSelf);
VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__0(VTbAdd0000000001___024root* vlSelf);
VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__1(VTbAdd0000000001___024root* vlSelf);
VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__2(VTbAdd0000000001___024root* vlSelf);
VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__3(VTbAdd0000000001___024root* vlSelf);
VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__4(VTbAdd0000000001___024root* vlSelf);
VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__5(VTbAdd0000000001___024root* vlSelf);
VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__6(VTbAdd0000000001___024root* vlSelf);
VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__7(VTbAdd0000000001___024root* vlSelf);

void VTbAdd0000000001___024root___eval_initial(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    VTbAdd0000000001___024root___eval_initial__TOP(vlSelf);
    vlSelfRef.__Vm_traceActivity[1U] = 1U;
    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__0(vlSelf);
    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__1(vlSelf);
    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__2(vlSelf);
    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__3(vlSelf);
    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__4(vlSelf);
    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__5(vlSelf);
    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__6(vlSelf);
    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__7(vlSelf);
}

VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__0(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.TbAdd0000000001__DOT__clk = 0U;
    while (true) {
        co_await vlSelfRef.__VdlySched.delay(0x0000000000001388ULL, 
                                             nullptr, 
                                             "TbAdd0000000001.v", 
                                             23);
        vlSelfRef.TbAdd0000000001__DOT__clk = (1U & 
                                               (~ (IData)(vlSelfRef.TbAdd0000000001__DOT__clk)));
    }
    co_return;
}

void VTbAdd0000000001___024root____VbeforeTrig_h03ac94d9__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription);

VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__1(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__1\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_1__DOT____Vrepeat0;
    TbAdd0000000001__DOT__unnamedblk1_1__DOT____Vrepeat0 = 0;
    // Body
    vlSelfRef.TbAdd0000000001__DOT__en = 0U;
    TbAdd0000000001__DOT__unnamedblk1_1__DOT____Vrepeat0 = 3U;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_1__DOT____Vrepeat0)) {
        VTbAdd0000000001___024root____VbeforeTrig_h03ac94d9__0(vlSelf, 
                                                               "@(posedge TbAdd0000000001.clk)");
        co_await vlSelfRef.__VtrigSched_h03ac94d9__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(posedge TbAdd0000000001.clk)", 
                                                             "TbAdd0000000001.v", 
                                                             33);
        TbAdd0000000001__DOT__unnamedblk1_1__DOT____Vrepeat0 
            = (TbAdd0000000001__DOT__unnamedblk1_1__DOT____Vrepeat0 
               - (IData)(1U));
    }
    vlSelfRef.TbAdd0000000001__DOT__en = 1U;
    co_return;
}

void VTbAdd0000000001___024root____VbeforeTrig_h03ac95b1__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription);

VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__2(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__2\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_2__DOT____Vrepeat1;
    TbAdd0000000001__DOT__unnamedblk1_2__DOT____Vrepeat1 = 0;
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_3__DOT____Vrepeat2;
    TbAdd0000000001__DOT__unnamedblk1_3__DOT____Vrepeat2 = 0;
    // Body
    vlSelfRef.TbAdd0000000001__DOT__i_rst_n = 1U;
    TbAdd0000000001__DOT__unnamedblk1_2__DOT____Vrepeat1 = 1U;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_2__DOT____Vrepeat1)) {
        VTbAdd0000000001___024root____VbeforeTrig_h03ac95b1__0(vlSelf, 
                                                               "@(negedge TbAdd0000000001.clk)");
        co_await vlSelfRef.__VtrigSched_h03ac95b1__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(negedge TbAdd0000000001.clk)", 
                                                             "TbAdd0000000001.v", 
                                                             40);
        TbAdd0000000001__DOT__unnamedblk1_2__DOT____Vrepeat1 
            = (TbAdd0000000001__DOT__unnamedblk1_2__DOT____Vrepeat1 
               - (IData)(1U));
    }
    vlSelfRef.TbAdd0000000001__DOT__i_rst_n = 0U;
    TbAdd0000000001__DOT__unnamedblk1_3__DOT____Vrepeat2 = 1U;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_3__DOT____Vrepeat2)) {
        VTbAdd0000000001___024root____VbeforeTrig_h03ac95b1__0(vlSelf, 
                                                               "@(negedge TbAdd0000000001.clk)");
        co_await vlSelfRef.__VtrigSched_h03ac95b1__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(negedge TbAdd0000000001.clk)", 
                                                             "TbAdd0000000001.v", 
                                                             42);
        TbAdd0000000001__DOT__unnamedblk1_3__DOT____Vrepeat2 
            = (TbAdd0000000001__DOT__unnamedblk1_3__DOT____Vrepeat2 
               - (IData)(1U));
    }
    vlSelfRef.TbAdd0000000001__DOT__i_rst_n = 1U;
    co_return;
}

void VTbAdd0000000001___024root____VbeforeTrig_h147138a8__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription);

VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__3(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__3\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_4__DOT____Vrepeat3;
    TbAdd0000000001__DOT__unnamedblk1_4__DOT____Vrepeat3 = 0;
    // Body
    vlSelfRef.TbAdd0000000001__DOT__Input_rdy = 0U;
    TbAdd0000000001__DOT__unnamedblk1_4__DOT____Vrepeat3 = 1U;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_4__DOT____Vrepeat3)) {
        VTbAdd0000000001___024root____VbeforeTrig_h147138a8__0(vlSelf, 
                                                               "@(posedge TbAdd0000000001.en)");
        co_await vlSelfRef.__VtrigSched_h147138a8__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(posedge TbAdd0000000001.en)", 
                                                             "TbAdd0000000001.v", 
                                                             49);
        TbAdd0000000001__DOT__unnamedblk1_4__DOT____Vrepeat3 
            = (TbAdd0000000001__DOT__unnamedblk1_4__DOT____Vrepeat3 
               - (IData)(1U));
    }
    vlSelfRef.TbAdd0000000001__DOT__Input_rdy = 1U;
    vlSelfRef.TbAdd0000000001__DOT__Input_rdy_iter = 0U;
    while (VL_GTS_III(32, 0x0000001aU, vlSelfRef.TbAdd0000000001__DOT__Input_rdy_iter)) {
        co_await vlSelfRef.__VdlySched.delay(0x0000000000001388ULL, 
                                             nullptr, 
                                             "TbAdd0000000001.v", 
                                             52);
        vlSelfRef.TbAdd0000000001__DOT__Input_rdy = 
            (1U & (~ (IData)(vlSelfRef.TbAdd0000000001__DOT__Input_rdy)));
        vlSelfRef.TbAdd0000000001__DOT__Input_rdy_iter 
            = ((IData)(1U) + vlSelfRef.TbAdd0000000001__DOT__Input_rdy_iter);
    }
    co_return;
}

VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__4(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__4\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_5__DOT____Vrepeat4;
    TbAdd0000000001__DOT__unnamedblk1_5__DOT____Vrepeat4 = 0;
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_6__DOT____Vrepeat5;
    TbAdd0000000001__DOT__unnamedblk1_6__DOT____Vrepeat5 = 0;
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_7__DOT____Vrepeat6;
    TbAdd0000000001__DOT__unnamedblk1_7__DOT____Vrepeat6 = 0;
    // Body
    vlSelfRef.TbAdd0000000001__DOT__Output_rdy = 0U;
    TbAdd0000000001__DOT__unnamedblk1_5__DOT____Vrepeat4 = 1U;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_5__DOT____Vrepeat4)) {
        VTbAdd0000000001___024root____VbeforeTrig_h147138a8__0(vlSelf, 
                                                               "@(posedge TbAdd0000000001.en)");
        co_await vlSelfRef.__VtrigSched_h147138a8__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(posedge TbAdd0000000001.en)", 
                                                             "TbAdd0000000001.v", 
                                                             58);
        TbAdd0000000001__DOT__unnamedblk1_5__DOT____Vrepeat4 
            = (TbAdd0000000001__DOT__unnamedblk1_5__DOT____Vrepeat4 
               - (IData)(1U));
    }
    TbAdd0000000001__DOT__unnamedblk1_6__DOT____Vrepeat5 = 1U;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_6__DOT____Vrepeat5)) {
        VTbAdd0000000001___024root____VbeforeTrig_h03ac94d9__0(vlSelf, 
                                                               "@(posedge TbAdd0000000001.clk)");
        co_await vlSelfRef.__VtrigSched_h03ac94d9__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(posedge TbAdd0000000001.clk)", 
                                                             "TbAdd0000000001.v", 
                                                             59);
        TbAdd0000000001__DOT__unnamedblk1_6__DOT____Vrepeat5 
            = (TbAdd0000000001__DOT__unnamedblk1_6__DOT____Vrepeat5 
               - (IData)(1U));
    }
    vlSelfRef.TbAdd0000000001__DOT__Output_rdy = 1U;
    vlSelfRef.TbAdd0000000001__DOT__Output_rdy_iter = 0U;
    while (VL_GTS_III(32, 0x0000001aU, vlSelfRef.TbAdd0000000001__DOT__Output_rdy_iter)) {
        co_await vlSelfRef.__VdlySched.delay(0x0000000000001388ULL, 
                                             nullptr, 
                                             "TbAdd0000000001.v", 
                                             62);
        vlSelfRef.TbAdd0000000001__DOT__Output_rdy 
            = (1U & (~ (IData)(vlSelfRef.TbAdd0000000001__DOT__Output_rdy)));
        vlSelfRef.TbAdd0000000001__DOT__Output_rdy_iter 
            = ((IData)(1U) + vlSelfRef.TbAdd0000000001__DOT__Output_rdy_iter);
    }
    TbAdd0000000001__DOT__unnamedblk1_7__DOT____Vrepeat6 = 0x0000001eU;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_7__DOT____Vrepeat6)) {
        VTbAdd0000000001___024root____VbeforeTrig_h03ac94d9__0(vlSelf, 
                                                               "@(posedge TbAdd0000000001.clk)");
        co_await vlSelfRef.__VtrigSched_h03ac94d9__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(posedge TbAdd0000000001.clk)", 
                                                             "TbAdd0000000001.v", 
                                                             64);
        TbAdd0000000001__DOT__unnamedblk1_7__DOT____Vrepeat6 
            = (TbAdd0000000001__DOT__unnamedblk1_7__DOT____Vrepeat6 
               - (IData)(1U));
    }
    VL_FINISH_MT("TbAdd0000000001.v", 65, "");
    co_return;
}

void VTbAdd0000000001___024root____VbeforeTrig_h3ed62ded__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription);

VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__5(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__5\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_8__DOT____Vrepeat7;
    TbAdd0000000001__DOT__unnamedblk1_8__DOT____Vrepeat7 = 0;
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_9__DOT____Vrepeat8;
    TbAdd0000000001__DOT__unnamedblk1_9__DOT____Vrepeat8 = 0;
    // Body
    TbAdd0000000001__DOT__unnamedblk1_8__DOT____Vrepeat7 = 2U;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_8__DOT____Vrepeat7)) {
        VTbAdd0000000001___024root____VbeforeTrig_h03ac94d9__0(vlSelf, 
                                                               "@(posedge TbAdd0000000001.clk)");
        co_await vlSelfRef.__VtrigSched_h03ac94d9__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(posedge TbAdd0000000001.clk)", 
                                                             "TbAdd0000000001.v", 
                                                             70);
        vlSelfRef.__Vm_traceActivity[2U] = 1U;
        TbAdd0000000001__DOT__unnamedblk1_8__DOT____Vrepeat7 
            = (TbAdd0000000001__DOT__unnamedblk1_8__DOT____Vrepeat7 
               - (IData)(1U));
    }
    vlSelfRef.TbAdd0000000001__DOT__i_data_1_dat = VL_FOPEN_NN("../Input_Files/add_i_data_1.txt"s
                                                               , "r"s);
    ;
    while (true) {
        vlSelfRef.TbAdd0000000001__DOT____VlemExpr_0 
            = (vlSelfRef.TbAdd0000000001__DOT__i_data_1_dat ? feof(VL_CVT_I_FP(vlSelfRef.TbAdd0000000001__DOT__i_data_1_dat)) : true);
        if (!((! vlSelfRef.TbAdd0000000001__DOT____VlemExpr_0))) break;
        vlSelfRef.TbAdd0000000001__DOT__i_data_1_st 
            = VL_FSCANF_INX(vlSelfRef.TbAdd0000000001__DOT__i_data_1_dat,"%b\n",1
                            , '#',1,&(vlSelfRef.TbAdd0000000001__DOT__Input_i_data_1)) ;
        TbAdd0000000001__DOT__unnamedblk1_9__DOT____Vrepeat8 = 1U;
        while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_9__DOT____Vrepeat8)) {
            VTbAdd0000000001___024root____VbeforeTrig_h3ed62ded__0(vlSelf, 
                                                                   "@(posedge TbAdd0000000001.Input_rdy)");
            co_await vlSelfRef.__VtrigSched_h3ed62ded__0.trigger(0U, 
                                                                 nullptr, 
                                                                 "@(posedge TbAdd0000000001.Input_rdy)", 
                                                                 "TbAdd0000000001.v", 
                                                                 74);
            vlSelfRef.__Vm_traceActivity[2U] = 1U;
            TbAdd0000000001__DOT__unnamedblk1_9__DOT____Vrepeat8 
                = (TbAdd0000000001__DOT__unnamedblk1_9__DOT____Vrepeat8 
                   - (IData)(1U));
        }
        vlSelfRef.TbAdd0000000001__DOT__i_data_1 = vlSelfRef.TbAdd0000000001__DOT__Input_i_data_1;
    }
    VL_FCLOSE_I(vlSelfRef.TbAdd0000000001__DOT__i_data_1_dat); vlSelfRef.__Vm_traceActivity[2U] = 1U;
    co_return;
}

VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__6(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__6\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_10__DOT____Vrepeat9;
    TbAdd0000000001__DOT__unnamedblk1_10__DOT____Vrepeat9 = 0;
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_11__DOT____Vrepeat10;
    TbAdd0000000001__DOT__unnamedblk1_11__DOT____Vrepeat10 = 0;
    // Body
    TbAdd0000000001__DOT__unnamedblk1_10__DOT____Vrepeat9 = 2U;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_10__DOT____Vrepeat9)) {
        VTbAdd0000000001___024root____VbeforeTrig_h03ac94d9__0(vlSelf, 
                                                               "@(posedge TbAdd0000000001.clk)");
        co_await vlSelfRef.__VtrigSched_h03ac94d9__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(posedge TbAdd0000000001.clk)", 
                                                             "TbAdd0000000001.v", 
                                                             81);
        vlSelfRef.__Vm_traceActivity[3U] = 1U;
        TbAdd0000000001__DOT__unnamedblk1_10__DOT____Vrepeat9 
            = (TbAdd0000000001__DOT__unnamedblk1_10__DOT____Vrepeat9 
               - (IData)(1U));
    }
    vlSelfRef.TbAdd0000000001__DOT__i_data_2_dat = VL_FOPEN_NN("../Input_Files/add_i_data_2.txt"s
                                                               , "r"s);
    ;
    while (true) {
        vlSelfRef.TbAdd0000000001__DOT____VlemExpr_1 
            = (vlSelfRef.TbAdd0000000001__DOT__i_data_2_dat ? feof(VL_CVT_I_FP(vlSelfRef.TbAdd0000000001__DOT__i_data_2_dat)) : true);
        if (!((! vlSelfRef.TbAdd0000000001__DOT____VlemExpr_1))) break;
        vlSelfRef.TbAdd0000000001__DOT__i_data_2_st 
            = VL_FSCANF_INX(vlSelfRef.TbAdd0000000001__DOT__i_data_2_dat,"%b\n",1
                            , '#',1,&(vlSelfRef.TbAdd0000000001__DOT__Input_i_data_2)) ;
        TbAdd0000000001__DOT__unnamedblk1_11__DOT____Vrepeat10 = 1U;
        while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_11__DOT____Vrepeat10)) {
            VTbAdd0000000001___024root____VbeforeTrig_h3ed62ded__0(vlSelf, 
                                                                   "@(posedge TbAdd0000000001.Input_rdy)");
            co_await vlSelfRef.__VtrigSched_h3ed62ded__0.trigger(0U, 
                                                                 nullptr, 
                                                                 "@(posedge TbAdd0000000001.Input_rdy)", 
                                                                 "TbAdd0000000001.v", 
                                                                 85);
            vlSelfRef.__Vm_traceActivity[3U] = 1U;
            TbAdd0000000001__DOT__unnamedblk1_11__DOT____Vrepeat10 
                = (TbAdd0000000001__DOT__unnamedblk1_11__DOT____Vrepeat10 
                   - (IData)(1U));
        }
        vlSelfRef.TbAdd0000000001__DOT__i_data_2 = vlSelfRef.TbAdd0000000001__DOT__Input_i_data_2;
    }
    VL_FCLOSE_I(vlSelfRef.TbAdd0000000001__DOT__i_data_2_dat); vlSelfRef.__Vm_traceActivity[3U] = 1U;
    co_return;
}

void VTbAdd0000000001___024root____VbeforeTrig_heb13cd23__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription);

VlCoroutine VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__7(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_initial__TOP__Vtiming__7\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_12__DOT____Vrepeat11;
    TbAdd0000000001__DOT__unnamedblk1_12__DOT____Vrepeat11 = 0;
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_13__DOT____Vrepeat12;
    TbAdd0000000001__DOT__unnamedblk1_13__DOT____Vrepeat12 = 0;
    IData/*31:0*/ TbAdd0000000001__DOT__unnamedblk1_14__DOT____Vrepeat13;
    TbAdd0000000001__DOT__unnamedblk1_14__DOT____Vrepeat13 = 0;
    // Body
    TbAdd0000000001__DOT__unnamedblk1_12__DOT____Vrepeat11 = 2U;
    while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_12__DOT____Vrepeat11)) {
        VTbAdd0000000001___024root____VbeforeTrig_h03ac94d9__0(vlSelf, 
                                                               "@(posedge TbAdd0000000001.clk)");
        co_await vlSelfRef.__VtrigSched_h03ac94d9__0.trigger(0U, 
                                                             nullptr, 
                                                             "@(posedge TbAdd0000000001.clk)", 
                                                             "TbAdd0000000001.v", 
                                                             94);
        TbAdd0000000001__DOT__unnamedblk1_12__DOT____Vrepeat11 
            = (TbAdd0000000001__DOT__unnamedblk1_12__DOT____Vrepeat11 
               - (IData)(1U));
    }
    vlSelfRef.TbAdd0000000001__DOT__o_data_dat = VL_FOPEN_NN("../Output_Files/add_o_data.txt"s
                                                             , "w"s);
    ;
    vlSelfRef.TbAdd0000000001__DOT__o_data_iter = 0U;
    while (VL_GTS_III(32, 3U, vlSelfRef.TbAdd0000000001__DOT__o_data_iter)) {
        TbAdd0000000001__DOT__unnamedblk1_13__DOT____Vrepeat12 = 1U;
        while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_13__DOT____Vrepeat12)) {
            VTbAdd0000000001___024root____VbeforeTrig_heb13cd23__0(vlSelf, 
                                                                   "@(posedge TbAdd0000000001.Output_rdy)");
            co_await vlSelfRef.__VtrigSched_heb13cd23__0.trigger(0U, 
                                                                 nullptr, 
                                                                 "@(posedge TbAdd0000000001.Output_rdy)", 
                                                                 "TbAdd0000000001.v", 
                                                                 97);
            TbAdd0000000001__DOT__unnamedblk1_13__DOT____Vrepeat12 
                = (TbAdd0000000001__DOT__unnamedblk1_13__DOT____Vrepeat12 
                   - (IData)(1U));
        }
        TbAdd0000000001__DOT__unnamedblk1_14__DOT____Vrepeat13 = 1U;
        while (VL_LTS_III(32, 0U, TbAdd0000000001__DOT__unnamedblk1_14__DOT____Vrepeat13)) {
            VTbAdd0000000001___024root____VbeforeTrig_h03ac95b1__0(vlSelf, 
                                                                   "@(negedge TbAdd0000000001.clk)");
            co_await vlSelfRef.__VtrigSched_h03ac95b1__0.trigger(0U, 
                                                                 nullptr, 
                                                                 "@(negedge TbAdd0000000001.clk)", 
                                                                 "TbAdd0000000001.v", 
                                                                 98);
            TbAdd0000000001__DOT__unnamedblk1_14__DOT____Vrepeat13 
                = (TbAdd0000000001__DOT__unnamedblk1_14__DOT____Vrepeat13 
                   - (IData)(1U));
        }
        VL_FWRITEF_NX(vlSelfRef.TbAdd0000000001__DOT__o_data_dat,"%b\n",1
                      , '#',1,vlSelfRef.TbAdd0000000001__DOT__u_0000000001_Add0000000001__DOT__u_0000000001_Delay0000000003__DOT__data_d[0U]);
        vlSelfRef.TbAdd0000000001__DOT__o_data_iter 
            = ((IData)(1U) + vlSelfRef.TbAdd0000000001__DOT__o_data_iter);
    }
    VL_FCLOSE_I(vlSelfRef.TbAdd0000000001__DOT__o_data_dat); co_return;
}

void VTbAdd0000000001___024root___eval_triggers_vec__act(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_triggers_vec__act\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__VactTriggered[0U] = (QData)((IData)(
                                                    (((((IData)(vlSelfRef.TbAdd0000000001__DOT__Output_rdy) 
                                                        & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Output_rdy__0))) 
                                                       << 5U) 
                                                      | (((IData)(vlSelfRef.TbAdd0000000001__DOT__Input_rdy) 
                                                          & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Input_rdy__0))) 
                                                         << 4U)) 
                                                     | (((((IData)(vlSelfRef.TbAdd0000000001__DOT__en) 
                                                           & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__en__0))) 
                                                          << 3U) 
                                                         | (((~ (IData)(vlSelfRef.TbAdd0000000001__DOT__clk)) 
                                                             & (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0)) 
                                                            << 2U)) 
                                                        | ((vlSelfRef.__VdlySched.awaitingCurrentTime() 
                                                            << 1U) 
                                                           | ((IData)(vlSelfRef.TbAdd0000000001__DOT__clk) 
                                                              & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0))))))));
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0 
        = vlSelfRef.TbAdd0000000001__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__en__0 
        = vlSelfRef.TbAdd0000000001__DOT__en;
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Input_rdy__0 
        = vlSelfRef.TbAdd0000000001__DOT__Input_rdy;
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Output_rdy__0 
        = vlSelfRef.TbAdd0000000001__DOT__Output_rdy;
}

bool VTbAdd0000000001___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___trigger_anySet__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        if (in[n]) {
            return (1U);
        }
        n = ((IData)(1U) + n);
    } while ((1U > n));
    return (0U);
}

void VTbAdd0000000001___024root___nba_sequent__TOP__0(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___nba_sequent__TOP__0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.TbAdd0000000001__DOT__u_0000000001_Add0000000001__DOT__u_0000000001_Delay0000000003__DOT__data_d[0U] = 0U;
}

void VTbAdd0000000001___024root___eval_nba(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_nba\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
        VTbAdd0000000001___024root___nba_sequent__TOP__0(vlSelf);
    }
}

void VTbAdd0000000001___024root___timing_ready(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___timing_ready\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1ULL & vlSelfRef.__VactTriggered[0U])) {
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready("@(posedge TbAdd0000000001.clk)");
    }
    if ((4ULL & vlSelfRef.__VactTriggered[0U])) {
        vlSelfRef.__VtrigSched_h03ac95b1__0.ready("@(negedge TbAdd0000000001.clk)");
    }
    if ((8ULL & vlSelfRef.__VactTriggered[0U])) {
        vlSelfRef.__VtrigSched_h147138a8__0.ready("@(posedge TbAdd0000000001.en)");
    }
    if ((0x0000000000000010ULL & vlSelfRef.__VactTriggered[0U])) {
        vlSelfRef.__VtrigSched_h3ed62ded__0.ready("@(posedge TbAdd0000000001.Input_rdy)");
    }
    if ((0x0000000000000020ULL & vlSelfRef.__VactTriggered[0U])) {
        vlSelfRef.__VtrigSched_heb13cd23__0.ready("@(posedge TbAdd0000000001.Output_rdy)");
    }
}

void VTbAdd0000000001___024root___timing_resume(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___timing_resume\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__VtrigSched_h03ac94d9__0.moveToResumeQueue(
                                                          "@(posedge TbAdd0000000001.clk)");
    vlSelfRef.__VtrigSched_h03ac95b1__0.moveToResumeQueue(
                                                          "@(negedge TbAdd0000000001.clk)");
    vlSelfRef.__VtrigSched_h147138a8__0.moveToResumeQueue(
                                                          "@(posedge TbAdd0000000001.en)");
    vlSelfRef.__VtrigSched_h3ed62ded__0.moveToResumeQueue(
                                                          "@(posedge TbAdd0000000001.Input_rdy)");
    vlSelfRef.__VtrigSched_heb13cd23__0.moveToResumeQueue(
                                                          "@(posedge TbAdd0000000001.Output_rdy)");
    vlSelfRef.__VtrigSched_h03ac94d9__0.resume("@(posedge TbAdd0000000001.clk)");
    vlSelfRef.__VtrigSched_h03ac95b1__0.resume("@(negedge TbAdd0000000001.clk)");
    vlSelfRef.__VtrigSched_h147138a8__0.resume("@(posedge TbAdd0000000001.en)");
    vlSelfRef.__VtrigSched_h3ed62ded__0.resume("@(posedge TbAdd0000000001.Input_rdy)");
    vlSelfRef.__VtrigSched_heb13cd23__0.resume("@(posedge TbAdd0000000001.Output_rdy)");
    if ((2ULL & vlSelfRef.__VactTriggered[0U])) {
        vlSelfRef.__VdlySched.resume();
    }
}

void VTbAdd0000000001___024root___trigger_orInto__act_vec_vec(VlUnpacked<QData/*63:0*/, 1> &out, const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___trigger_orInto__act_vec_vec\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = (out[n] | in[n]);
        n = ((IData)(1U) + n);
    } while ((0U >= n));
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VTbAdd0000000001___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG

bool VTbAdd0000000001___024root___eval_phase__act(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_phase__act\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VactExecute;
    // Body
    VTbAdd0000000001___024root___eval_triggers_vec__act(vlSelf);
    VTbAdd0000000001___024root___timing_ready(vlSelf);
    VTbAdd0000000001___024root___trigger_orInto__act_vec_vec(vlSelfRef.__VactTriggered, vlSelfRef.__VactTriggeredAcc);
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        VTbAdd0000000001___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
    }
#endif
    VTbAdd0000000001___024root___trigger_orInto__act_vec_vec(vlSelfRef.__VnbaTriggered, vlSelfRef.__VactTriggered);
    __VactExecute = VTbAdd0000000001___024root___trigger_anySet__act(vlSelfRef.__VactTriggered);
    if (__VactExecute) {
        vlSelfRef.__VactTriggeredAcc.fill(0ULL);
        VTbAdd0000000001___024root___timing_resume(vlSelf);
    }
    return (__VactExecute);
}

bool VTbAdd0000000001___024root___eval_phase__inact(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_phase__inact\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VinactExecute;
    // Body
    __VinactExecute = vlSelfRef.__VdlySched.awaitingZeroDelay();
    if (__VinactExecute) {
        VL_FATAL_MT("TbAdd0000000001.v", 2, "", "ZERODLY: Design Verilated with '--no-sched-zero-delay', but #0 delay executed at runtime");
    }
    return (__VinactExecute);
}

void VTbAdd0000000001___024root___trigger_clear__act(VlUnpacked<QData/*63:0*/, 1> &out) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___trigger_clear__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = 0ULL;
        n = ((IData)(1U) + n);
    } while ((1U > n));
}

bool VTbAdd0000000001___024root___eval_phase__nba(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_phase__nba\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = VTbAdd0000000001___024root___trigger_anySet__act(vlSelfRef.__VnbaTriggered);
    if (__VnbaExecute) {
        VTbAdd0000000001___024root___eval_nba(vlSelf);
        VTbAdd0000000001___024root___trigger_clear__act(vlSelfRef.__VnbaTriggered);
    }
    return (__VnbaExecute);
}

void VTbAdd0000000001___024root___eval(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VnbaIterCount;
    // Body
    __VnbaIterCount = 0U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VnbaIterCount)))) {
#ifdef VL_DEBUG
            VTbAdd0000000001___024root___dump_triggers__act(vlSelfRef.__VnbaTriggered, "nba"s);
#endif
            VL_FATAL_MT("TbAdd0000000001.v", 2, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 10000 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VinactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VinactIterCount)))) {
                VL_FATAL_MT("TbAdd0000000001.v", 2, "", "DIDNOTCONVERGE: Inactive region did not converge after '--converge-limit' of 10000 tries");
            }
            vlSelfRef.__VinactIterCount = ((IData)(1U) 
                                           + vlSelfRef.__VinactIterCount);
            vlSelfRef.__VactIterCount = 0U;
            do {
                if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                    VTbAdd0000000001___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                    VL_FATAL_MT("TbAdd0000000001.v", 2, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 10000 tries");
                }
                vlSelfRef.__VactIterCount = ((IData)(1U) 
                                             + vlSelfRef.__VactIterCount);
                vlSelfRef.__VactPhaseResult = VTbAdd0000000001___024root___eval_phase__act(vlSelf);
            } while (vlSelfRef.__VactPhaseResult);
            vlSelfRef.__VinactPhaseResult = VTbAdd0000000001___024root___eval_phase__inact(vlSelf);
        } while (vlSelfRef.__VinactPhaseResult);
        vlSelfRef.__VnbaPhaseResult = VTbAdd0000000001___024root___eval_phase__nba(vlSelf);
    } while (vlSelfRef.__VnbaPhaseResult);
}

void VTbAdd0000000001___024root____VbeforeTrig_h03ac94d9__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root____VbeforeTrig_h03ac94d9__0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    VlUnpacked<QData/*63:0*/, 1> __VTmp;
    // Body
    __VTmp[0U] = (QData)((IData)(((((~ (IData)(vlSelfRef.TbAdd0000000001__DOT__clk)) 
                                    & (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0)) 
                                   << 2U) | ((IData)(vlSelfRef.TbAdd0000000001__DOT__clk) 
                                             & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0))))));
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0 
        = vlSelfRef.TbAdd0000000001__DOT__clk;
    if ((1ULL & __VTmp[0U])) {
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
    }
    if ((4ULL & __VTmp[0U])) {
        vlSelfRef.__VtrigSched_h03ac95b1__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac95b1__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac95b1__0.ready(__VeventDescription);
    }
    vlSelfRef.__VactTriggeredAcc[0U] = (vlSelfRef.__VactTriggeredAcc[0U] 
                                        | __VTmp[0U]);
}

void VTbAdd0000000001___024root____VbeforeTrig_h03ac95b1__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root____VbeforeTrig_h03ac95b1__0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    VlUnpacked<QData/*63:0*/, 1> __VTmp;
    // Body
    __VTmp[0U] = (QData)((IData)(((((~ (IData)(vlSelfRef.TbAdd0000000001__DOT__clk)) 
                                    & (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0)) 
                                   << 2U) | ((IData)(vlSelfRef.TbAdd0000000001__DOT__clk) 
                                             & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0))))));
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0 
        = vlSelfRef.TbAdd0000000001__DOT__clk;
    if ((1ULL & __VTmp[0U])) {
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac94d9__0.ready(__VeventDescription);
    }
    if ((4ULL & __VTmp[0U])) {
        vlSelfRef.__VtrigSched_h03ac95b1__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac95b1__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h03ac95b1__0.ready(__VeventDescription);
    }
    vlSelfRef.__VactTriggeredAcc[0U] = (vlSelfRef.__VactTriggeredAcc[0U] 
                                        | __VTmp[0U]);
}

void VTbAdd0000000001___024root____VbeforeTrig_h147138a8__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root____VbeforeTrig_h147138a8__0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    VlUnpacked<QData/*63:0*/, 1> __VTmp;
    // Body
    __VTmp[0U] = (QData)((IData)((((IData)(vlSelfRef.TbAdd0000000001__DOT__en) 
                                   & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__en__0))) 
                                  << 3U)));
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__en__0 
        = vlSelfRef.TbAdd0000000001__DOT__en;
    if ((8ULL & __VTmp[0U])) {
        vlSelfRef.__VtrigSched_h147138a8__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h147138a8__0.ready(__VeventDescription);
    }
    vlSelfRef.__VactTriggeredAcc[0U] = (vlSelfRef.__VactTriggeredAcc[0U] 
                                        | __VTmp[0U]);
}

void VTbAdd0000000001___024root____VbeforeTrig_h3ed62ded__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root____VbeforeTrig_h3ed62ded__0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    VlUnpacked<QData/*63:0*/, 1> __VTmp;
    // Body
    __VTmp[0U] = (QData)((IData)((((IData)(vlSelfRef.TbAdd0000000001__DOT__Input_rdy) 
                                   & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Input_rdy__0))) 
                                  << 4U)));
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Input_rdy__0 
        = vlSelfRef.TbAdd0000000001__DOT__Input_rdy;
    if ((0x0000000000000010ULL & __VTmp[0U])) {
        vlSelfRef.__VtrigSched_h3ed62ded__0.ready(__VeventDescription);
        vlSelfRef.__VtrigSched_h3ed62ded__0.ready(__VeventDescription);
    }
    vlSelfRef.__VactTriggeredAcc[0U] = (vlSelfRef.__VactTriggeredAcc[0U] 
                                        | __VTmp[0U]);
}

void VTbAdd0000000001___024root____VbeforeTrig_heb13cd23__0(VTbAdd0000000001___024root* vlSelf, const char* __VeventDescription) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root____VbeforeTrig_heb13cd23__0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    VlUnpacked<QData/*63:0*/, 1> __VTmp;
    // Body
    __VTmp[0U] = (QData)((IData)((((IData)(vlSelfRef.TbAdd0000000001__DOT__Output_rdy) 
                                   & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Output_rdy__0))) 
                                  << 5U)));
    vlSelfRef.__Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Output_rdy__0 
        = vlSelfRef.TbAdd0000000001__DOT__Output_rdy;
    if ((0x0000000000000020ULL & __VTmp[0U])) {
        vlSelfRef.__VtrigSched_heb13cd23__0.ready(__VeventDescription);
    }
    vlSelfRef.__VactTriggeredAcc[0U] = (vlSelfRef.__VactTriggeredAcc[0U] 
                                        | __VTmp[0U]);
}

#ifdef VL_DEBUG
void VTbAdd0000000001___024root___eval_debug_assertions(VTbAdd0000000001___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root___eval_debug_assertions\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
}
#endif  // VL_DEBUG
