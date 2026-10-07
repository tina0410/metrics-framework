// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VTbAdd0000000001.h for the primary calling header

#include "VTbAdd0000000001__pch.h"

void VTbAdd0000000001___024root___ctor_var_reset(VTbAdd0000000001___024root* vlSelf);

VTbAdd0000000001___024root::VTbAdd0000000001___024root(VTbAdd0000000001__Syms* symsp, const char* namep)
    : __VdlySched{*symsp->_vm_contextp__}
 {
    vlSymsp = symsp;
    vlNamep = strdup(namep);
    // Reset structure values
    VTbAdd0000000001___024root___ctor_var_reset(this);
}

void VTbAdd0000000001___024root::__Vconfigure(bool first) {
    (void)first;  // Prevent unused variable warning
}

VTbAdd0000000001___024root::~VTbAdd0000000001___024root() {
    VL_DO_DANGLING(std::free(const_cast<char*>(vlNamep)), vlNamep);
}
