// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Tracing implementation internals

#include "verilated_vcd_c.h"
#include "VTbAdd0000000001__Syms.h"


VL_ATTR_COLD void VTbAdd0000000001___024root__trace_init_dtype____0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd* tracep, const char* name, uint32_t fidx, uint32_t c, VerilatedTraceSigDirection direction);

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_init_sub__TOP__0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd* tracep) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_init_sub__TOP__0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    const int c = vlSymsp->__Vm_baseCode;
    VL_TRACE_PUSH_PREFIX(tracep, "TbAdd0000000001", VerilatedTracePrefixType::SCOPE_MODULE, 0, 0);
    VL_TRACE_DECL_BUS(tracep,c+0,0,"Input_i_data_1",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+6,0,"Input_i_data_2",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+1,0,"i_data_1",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+7,0,"i_data_2",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BIT(tracep,c+12,0,"clk",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC);
    VL_TRACE_DECL_BIT(tracep,c+13,0,"en",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC);
    VL_TRACE_DECL_BIT(tracep,c+14,0,"i_rst_n",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC);
    VL_TRACE_DECL_BUS(tracep,c+15,0,"o_data",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BIT(tracep,c+16,0,"Input_rdy",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC);
    VL_TRACE_DECL_BIT(tracep,c+17,0,"Output_rdy",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC);
    VL_TRACE_DECL_BUS(tracep,c+18,0,"Input_rdy_iter",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::INTEGER, 31,0);
    VL_TRACE_DECL_BUS(tracep,c+19,0,"Output_rdy_iter",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::INTEGER, 31,0);
    VL_TRACE_DECL_BUS(tracep,c+2,0,"i_data_1_dat",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::INTEGER, 31,0);
    VL_TRACE_DECL_BUS(tracep,c+3,0,"i_data_1_st",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::INTEGER, 31,0);
    VL_TRACE_DECL_BUS(tracep,c+8,0,"i_data_2_dat",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::INTEGER, 31,0);
    VL_TRACE_DECL_BUS(tracep,c+9,0,"i_data_2_st",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::INTEGER, 31,0);
    VL_TRACE_DECL_BUS(tracep,c+20,0,"o_data_dat",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::INTEGER, 31,0);
    VL_TRACE_DECL_BUS(tracep,c+21,0,"o_data_iter",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::INTEGER, 31,0);
    VL_TRACE_PUSH_PREFIX(tracep, "u_0000000001_Add0000000001", VerilatedTracePrefixType::SCOPE_MODULE, 0, 0);
    VL_TRACE_DECL_BUS(tracep,c+1,0,"i_data_1",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+7,0,"i_data_2",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+15,0,"o_data",-1, VerilatedTraceSigDirection::OUTPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BIT(tracep,c+12,0,"i_clk",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC);
    VL_TRACE_DECL_BUS(tracep,c+1,0,"data_1",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+7,0,"data_2",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+4,0,"data_1_fixed",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+10,0,"data_2_fixed",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+22,0,"result_unfixed",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+27,0,"result_fixed",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_PUSH_PREFIX(tracep, "u_0000000001_Delay0000000003", VerilatedTracePrefixType::SCOPE_MODULE, 0, 0);
    VL_TRACE_DECL_BUS(tracep,c+27,0,"i_data",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+15,0,"o_data",-1, VerilatedTraceSigDirection::OUTPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BIT(tracep,c+12,0,"i_clk",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC);

    VTbAdd0000000001___024root__trace_init_dtype____0(vlSelf, tracep, "data_d", 0, c+23, VerilatedTraceSigDirection::NONE);
    VL_TRACE_POP_PREFIX(tracep);
    VL_TRACE_PUSH_PREFIX(tracep, "u_0000000001_FxMatch0000000001", VerilatedTracePrefixType::SCOPE_MODULE, 0, 0);
    VL_TRACE_DECL_BUS(tracep,c+1,0,"i_data",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+4,0,"o_data",-1, VerilatedTraceSigDirection::OUTPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+4,0,"i_data_eq",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+5,0,"o_data_eq",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 2,0);
    VL_TRACE_DECL_BUS(tracep,c+4,0,"op_quan",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+4,0,"o_data_trunc",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_PUSH_PREFIX(tracep, "u_0000000001_Delay0000000001", VerilatedTracePrefixType::SCOPE_MODULE, 0, 0);
    VL_TRACE_DECL_BUS(tracep,c+4,0,"i_data",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+4,0,"o_data",-1, VerilatedTraceSigDirection::OUTPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_POP_PREFIX(tracep);
    VL_TRACE_POP_PREFIX(tracep);
    VL_TRACE_PUSH_PREFIX(tracep, "u_0000000001_FxMatch0000000002", VerilatedTracePrefixType::SCOPE_MODULE, 0, 0);
    VL_TRACE_DECL_BUS(tracep,c+22,0,"i_data",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+27,0,"o_data",-1, VerilatedTraceSigDirection::OUTPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+24,0,"i_data_eq",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 2,0);
    VL_TRACE_DECL_BUS(tracep,c+25,0,"o_data_eq",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+26,0,"op_quan",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 3,0);
    VL_TRACE_DECL_BUS(tracep,c+27,0,"o_data_trunc",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_PUSH_PREFIX(tracep, "u_0000000001_Delay0000000002", VerilatedTracePrefixType::SCOPE_MODULE, 0, 0);
    VL_TRACE_DECL_BUS(tracep,c+27,0,"i_data",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+27,0,"o_data",-1, VerilatedTraceSigDirection::OUTPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_POP_PREFIX(tracep);
    VL_TRACE_POP_PREFIX(tracep);
    VL_TRACE_PUSH_PREFIX(tracep, "u_0000000002_FxMatch0000000001", VerilatedTracePrefixType::SCOPE_MODULE, 0, 0);
    VL_TRACE_DECL_BUS(tracep,c+7,0,"i_data",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 0,0);
    VL_TRACE_DECL_BUS(tracep,c+10,0,"o_data",-1, VerilatedTraceSigDirection::OUTPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+10,0,"i_data_eq",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+11,0,"o_data_eq",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 2,0);
    VL_TRACE_DECL_BUS(tracep,c+10,0,"op_quan",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+10,0,"o_data_trunc",-1, VerilatedTraceSigDirection::NONE, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_PUSH_PREFIX(tracep, "u_0000000001_Delay0000000001", VerilatedTracePrefixType::SCOPE_MODULE, 0, 0);
    VL_TRACE_DECL_BUS(tracep,c+10,0,"i_data",-1, VerilatedTraceSigDirection::INPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_DECL_BUS(tracep,c+10,0,"o_data",-1, VerilatedTraceSigDirection::OUTPUT, VerilatedTraceSigKind::WIRE, VerilatedTraceSigType::LOGIC, 1,0);
    VL_TRACE_POP_PREFIX(tracep);
    VL_TRACE_POP_PREFIX(tracep);
    VL_TRACE_POP_PREFIX(tracep);
    VL_TRACE_POP_PREFIX(tracep);
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_init_dtype_sub____0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd* tracep, const char* name, uint32_t fidx, uint32_t c, VerilatedTraceSigDirection direction);

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_init_dtype____0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd* tracep, const char* name, uint32_t fidx, uint32_t c, VerilatedTraceSigDirection direction) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_init_dtype____0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    VTbAdd0000000001___024root__trace_init_dtype_sub____0(vlSelf, tracep, name, fidx, c, direction);
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_init_dtype_sub____0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd* tracep, const char* name, uint32_t fidx, uint32_t c, VerilatedTraceSigDirection direction) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_init_dtype_sub____0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    VL_TRACE_PUSH_PREFIX(tracep, name, VerilatedTracePrefixType::ARRAY_UNPACKED, 0, 0);
    for (int i = 0; i < 1; ++i) {
        VL_TRACE_DECL_BUS_ARRAY(tracep,c+0+i*1,fidx,"",-1, direction, VerilatedTraceSigKind::VAR, VerilatedTraceSigType::LOGIC, (0 - i), 0,0);
    }
    VL_TRACE_POP_PREFIX(tracep);
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_init_top(VTbAdd0000000001___024root* vlSelf, VerilatedVcd* tracep) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_init_top\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    VTbAdd0000000001___024root__trace_init_sub__TOP__0(vlSelf, tracep);
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_const_0(void* voidSelf, VerilatedVcd::Buffer* bufp);
VL_ATTR_COLD void VTbAdd0000000001___024root__trace_full_0(void* voidSelf, VerilatedVcd::Buffer* bufp);
void VTbAdd0000000001___024root__trace_chg_0(void* voidSelf, VerilatedVcd::Buffer* bufp);
void VTbAdd0000000001___024root__trace_cleanup(void* voidSelf, VerilatedVcd* /*unused*/);

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_register(VTbAdd0000000001___024root* vlSelf, VerilatedVcd* tracep) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_register\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    tracep->addConstCb(&VTbAdd0000000001___024root__trace_const_0, 0, vlSelf);
    tracep->addFullCb(&VTbAdd0000000001___024root__trace_full_0, 0, vlSelf);
    tracep->addChgCb(&VTbAdd0000000001___024root__trace_chg_0, 0, vlSelf);
    tracep->addCleanupCb(&VTbAdd0000000001___024root__trace_cleanup, vlSelf);
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_const_0_sub_0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp);

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_const_0(void* voidSelf, VerilatedVcd::Buffer* bufp) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_const_0\n"); );
    // Body
    VTbAdd0000000001___024root* const __restrict vlSelf VL_ATTR_UNUSED = static_cast<VTbAdd0000000001___024root*>(voidSelf);
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VTbAdd0000000001___024root__trace_const_0_sub_0((&vlSymsp->TOP), bufp);
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_const_0_sub_0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_const_0_sub_0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    uint32_t* const oldp VL_ATTR_UNUSED = bufp->oldp(vlSymsp->__Vm_baseCode);
    bufp->fullBit(oldp+27,(0U));
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_full_0_sub_0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp);

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_full_0(void* voidSelf, VerilatedVcd::Buffer* bufp) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_full_0\n"); );
    // Body
    VTbAdd0000000001___024root* const __restrict vlSelf VL_ATTR_UNUSED = static_cast<VTbAdd0000000001___024root*>(voidSelf);
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VTbAdd0000000001___024root__trace_full_0_sub_0((&vlSymsp->TOP), bufp);
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_full_dtype____0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp, uint32_t offset, const VlUnpacked<CData/*0:0*/, 1>& __VdtypeVar);

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_full_0_sub_0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_full_0_sub_0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    uint32_t* const oldp VL_ATTR_UNUSED = bufp->oldp(vlSymsp->__Vm_baseCode);
    bufp->fullBit(oldp+0,(vlSelfRef.TbAdd0000000001__DOT__Input_i_data_1));
    bufp->fullBit(oldp+1,(vlSelfRef.TbAdd0000000001__DOT__i_data_1));
    bufp->fullIData(oldp+2,(vlSelfRef.TbAdd0000000001__DOT__i_data_1_dat),32);
    bufp->fullIData(oldp+3,(vlSelfRef.TbAdd0000000001__DOT__i_data_1_st),32);
    bufp->fullCData(oldp+4,(vlSelfRef.TbAdd0000000001__DOT__i_data_1),2);
    bufp->fullCData(oldp+5,(vlSelfRef.TbAdd0000000001__DOT__i_data_1),3);
    bufp->fullBit(oldp+6,(vlSelfRef.TbAdd0000000001__DOT__Input_i_data_2));
    bufp->fullBit(oldp+7,(vlSelfRef.TbAdd0000000001__DOT__i_data_2));
    bufp->fullIData(oldp+8,(vlSelfRef.TbAdd0000000001__DOT__i_data_2_dat),32);
    bufp->fullIData(oldp+9,(vlSelfRef.TbAdd0000000001__DOT__i_data_2_st),32);
    bufp->fullCData(oldp+10,(vlSelfRef.TbAdd0000000001__DOT__i_data_2),2);
    bufp->fullCData(oldp+11,(vlSelfRef.TbAdd0000000001__DOT__i_data_2),3);
    bufp->fullBit(oldp+12,(vlSelfRef.TbAdd0000000001__DOT__clk));
    bufp->fullBit(oldp+13,(vlSelfRef.TbAdd0000000001__DOT__en));
    bufp->fullBit(oldp+14,(vlSelfRef.TbAdd0000000001__DOT__i_rst_n));
    bufp->fullBit(oldp+15,(vlSelfRef.TbAdd0000000001__DOT__u_0000000001_Add0000000001__DOT__u_0000000001_Delay0000000003__DOT__data_d[0U]));
    bufp->fullBit(oldp+16,(vlSelfRef.TbAdd0000000001__DOT__Input_rdy));
    bufp->fullBit(oldp+17,(vlSelfRef.TbAdd0000000001__DOT__Output_rdy));
    bufp->fullIData(oldp+18,(vlSelfRef.TbAdd0000000001__DOT__Input_rdy_iter),32);
    bufp->fullIData(oldp+19,(vlSelfRef.TbAdd0000000001__DOT__Output_rdy_iter),32);
    bufp->fullIData(oldp+20,(vlSelfRef.TbAdd0000000001__DOT__o_data_dat),32);
    bufp->fullIData(oldp+21,(vlSelfRef.TbAdd0000000001__DOT__o_data_iter),32);
    bufp->fullCData(oldp+22,((3U & ((IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_2) 
                                    + (IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_1)))),2);
    VTbAdd0000000001___024root__trace_full_dtype____0(vlSelf, bufp, 23, vlSelfRef.TbAdd0000000001__DOT__u_0000000001_Add0000000001__DOT__u_0000000001_Delay0000000003__DOT__data_d);
    bufp->fullCData(oldp+24,((3U & ((IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_2) 
                                    + (IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_1)))),3);
    bufp->fullCData(oldp+25,((2U & (((IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_2) 
                                     + (IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_1)) 
                                    << 1U))),2);
    bufp->fullCData(oldp+26,((6U & (((IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_2) 
                                     + (IData)(vlSelfRef.TbAdd0000000001__DOT__i_data_1)) 
                                    << 1U))),4);
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_full_dtype____0(VTbAdd0000000001___024root* vlSelf, VerilatedVcd::Buffer* bufp, uint32_t offset, const VlUnpacked<CData/*0:0*/, 1>& __VdtypeVar) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    VTbAdd0000000001___024root__trace_full_dtype____0\n"); );
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    uint32_t* const oldp VL_ATTR_UNUSED = bufp->oldp(vlSymsp->__Vm_baseCode + offset);
    bufp->fullBit(oldp+0,(__VdtypeVar[0]));
}
