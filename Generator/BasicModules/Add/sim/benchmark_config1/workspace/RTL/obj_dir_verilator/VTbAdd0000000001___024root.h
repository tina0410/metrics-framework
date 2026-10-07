// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See VTbAdd0000000001.h for the primary calling header

#ifndef VERILATED_VTBADD0000000001___024ROOT_H_
#define VERILATED_VTBADD0000000001___024ROOT_H_  // guard

#include "verilated.h"
#include "verilated_timing.h"


class VTbAdd0000000001__Syms;

class alignas(VL_CACHE_LINE_BYTES) VTbAdd0000000001___024root final {
  public:

    // DESIGN SPECIFIC STATE
    CData/*0:0*/ TbAdd0000000001__DOT__Input_i_data_1;
    CData/*0:0*/ TbAdd0000000001__DOT__Input_i_data_2;
    CData/*0:0*/ TbAdd0000000001__DOT__i_data_1;
    CData/*0:0*/ TbAdd0000000001__DOT__i_data_2;
    CData/*0:0*/ TbAdd0000000001__DOT__clk;
    CData/*0:0*/ TbAdd0000000001__DOT__en;
    CData/*0:0*/ TbAdd0000000001__DOT__i_rst_n;
    CData/*0:0*/ TbAdd0000000001__DOT__Input_rdy;
    CData/*0:0*/ TbAdd0000000001__DOT__Output_rdy;
    CData/*0:0*/ __Vtrigprevexpr___TOP__TbAdd0000000001__DOT__clk__0;
    CData/*0:0*/ __Vtrigprevexpr___TOP__TbAdd0000000001__DOT__en__0;
    CData/*0:0*/ __Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Input_rdy__0;
    CData/*0:0*/ __Vtrigprevexpr___TOP__TbAdd0000000001__DOT__Output_rdy__0;
    CData/*0:0*/ __VactPhaseResult;
    CData/*0:0*/ __VinactPhaseResult;
    CData/*0:0*/ __VnbaPhaseResult;
    IData/*31:0*/ TbAdd0000000001__DOT____VlemExpr_1;
    IData/*31:0*/ TbAdd0000000001__DOT____VlemExpr_0;
    IData/*31:0*/ TbAdd0000000001__DOT__Input_rdy_iter;
    IData/*31:0*/ TbAdd0000000001__DOT__Output_rdy_iter;
    IData/*31:0*/ TbAdd0000000001__DOT__i_data_1_dat;
    IData/*31:0*/ TbAdd0000000001__DOT__i_data_1_st;
    IData/*31:0*/ TbAdd0000000001__DOT__i_data_2_dat;
    IData/*31:0*/ TbAdd0000000001__DOT__i_data_2_st;
    IData/*31:0*/ TbAdd0000000001__DOT__o_data_dat;
    IData/*31:0*/ TbAdd0000000001__DOT__o_data_iter;
    IData/*31:0*/ __VactIterCount;
    IData/*31:0*/ __VinactIterCount;
    IData/*31:0*/ __Vi;
    VlUnpacked<CData/*0:0*/, 1> TbAdd0000000001__DOT__u_0000000001_Add0000000001__DOT__u_0000000001_Delay0000000003__DOT__data_d;
    VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VactTriggeredAcc;
    VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;
    VlUnpacked<CData/*0:0*/, 4> __Vm_traceActivity;
    VlDelayScheduler __VdlySched;
    VlTriggerScheduler __VtrigSched_h03ac94d9__0;
    VlTriggerScheduler __VtrigSched_h03ac95b1__0;
    VlTriggerScheduler __VtrigSched_h147138a8__0;
    VlTriggerScheduler __VtrigSched_h3ed62ded__0;
    VlTriggerScheduler __VtrigSched_heb13cd23__0;

    // INTERNAL VARIABLES
    VTbAdd0000000001__Syms* vlSymsp;
    const char* vlNamep;

    // CONSTRUCTORS
    VTbAdd0000000001___024root(VTbAdd0000000001__Syms* symsp, const char* namep);
    ~VTbAdd0000000001___024root();
    VL_UNCOPYABLE(VTbAdd0000000001___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
