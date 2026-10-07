// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Model implementation (design independent parts)

#include "VTbAdd0000000001__pch.h"
#include "verilated_vcd_c.h"

//============================================================
// Constructors

VTbAdd0000000001::VTbAdd0000000001(VerilatedContext* _vcontextp__, const char* _vcname__)
    : VerilatedModel{*_vcontextp__}
    , vlSymsp{new VTbAdd0000000001__Syms(contextp(), _vcname__, this)}
    , rootp{&(vlSymsp->TOP)}
{
    // Register model with the context
    contextp()->addModel(this);
    contextp()->traceBaseModelCbAdd(
        [this](VerilatedTraceBaseC* tfp, int levels, int options) { traceBaseModel(tfp, levels, options); });
}

VTbAdd0000000001::VTbAdd0000000001(const char* _vcname__)
    : VTbAdd0000000001(Verilated::threadContextp(), _vcname__)
{
}

//============================================================
// Destructor

VTbAdd0000000001::~VTbAdd0000000001() {
    delete vlSymsp;
}

//============================================================
// Evaluation function

#ifdef VL_DEBUG
void VTbAdd0000000001___024root___eval_debug_assertions(VTbAdd0000000001___024root* vlSelf);
#endif  // VL_DEBUG
void VTbAdd0000000001___024root___eval_static(VTbAdd0000000001___024root* vlSelf);
void VTbAdd0000000001___024root___eval_initial(VTbAdd0000000001___024root* vlSelf);
void VTbAdd0000000001___024root___eval_settle(VTbAdd0000000001___024root* vlSelf);
void VTbAdd0000000001___024root___eval(VTbAdd0000000001___024root* vlSelf);

void VTbAdd0000000001::eval_step() {
    VL_DEBUG_IF(VL_DBG_MSGF("+++++TOP Evaluate VTbAdd0000000001::eval_step\n"); );
#ifdef VL_DEBUG
    // Debug assertions
    VTbAdd0000000001___024root___eval_debug_assertions(&(vlSymsp->TOP));
#endif  // VL_DEBUG
    vlSymsp->__Vm_activity = true;
    vlSymsp->__Vm_deleter.deleteAll();
    if (VL_UNLIKELY(!vlSymsp->__Vm_didInit)) {
        VL_DEBUG_IF(VL_DBG_MSGF("+ Initial\n"););
        VTbAdd0000000001___024root___eval_static(&(vlSymsp->TOP));
        VTbAdd0000000001___024root___eval_initial(&(vlSymsp->TOP));
        VTbAdd0000000001___024root___eval_settle(&(vlSymsp->TOP));
        vlSymsp->__Vm_didInit = true;
    }
    VL_DEBUG_IF(VL_DBG_MSGF("+ Eval\n"););
    VTbAdd0000000001___024root___eval(&(vlSymsp->TOP));
    // Evaluate cleanup
    Verilated::endOfEval(vlSymsp->__Vm_evalMsgQp);
}

void VTbAdd0000000001::eval_end_step() {
    VL_DEBUG_IF(VL_DBG_MSGF("+eval_end_step VTbAdd0000000001::eval_end_step\n"); );
#ifdef VM_TRACE
    // Tracing
    if (VL_UNLIKELY(vlSymsp->__Vm_dumping)) vlSymsp->_traceDump();
#endif  // VM_TRACE
}

//============================================================
// Events and timing
bool VTbAdd0000000001::eventsPending() { return !vlSymsp->TOP.__VdlySched.empty() && !contextp()->gotFinish(); }

uint64_t VTbAdd0000000001::nextTimeSlot() { return vlSymsp->TOP.__VdlySched.nextTimeSlot(); }

//============================================================
// Utilities

const char* VTbAdd0000000001::name() const {
    return vlSymsp->name();
}

//============================================================
// Invoke final blocks

void VTbAdd0000000001___024root___eval_final(VTbAdd0000000001___024root* vlSelf);

VL_ATTR_COLD void VTbAdd0000000001::final() {
    contextp()->executingFinal(true);
    VTbAdd0000000001___024root___eval_final(&(vlSymsp->TOP));
    contextp()->executingFinal(false);
}

//============================================================
// Implementations of abstract methods from VerilatedModel

const char* VTbAdd0000000001::hierName() const { return vlSymsp->name(); }
const char* VTbAdd0000000001::modelName() const { return "VTbAdd0000000001"; }
unsigned VTbAdd0000000001::threads() const { return 1; }
void VTbAdd0000000001::prepareClone() const { contextp()->prepareClone(); }
void VTbAdd0000000001::atClone() const {
    contextp()->threadPoolpOnClone();
}
std::unique_ptr<VerilatedTraceConfig> VTbAdd0000000001::traceConfig() const {
    return std::unique_ptr<VerilatedTraceConfig>{new VerilatedTraceConfig{false}};
};

//============================================================
// Trace configuration

void VTbAdd0000000001___024root__trace_decl_types(VerilatedVcd* tracep);

void VTbAdd0000000001___024root__trace_init_top(VTbAdd0000000001___024root* vlSelf, VerilatedVcd* tracep);

VL_ATTR_COLD static void trace_init(void* voidSelf, VerilatedVcd* tracep, uint32_t code) {
    // Callback from tracep->open()
    VTbAdd0000000001___024root* const __restrict vlSelf VL_ATTR_UNUSED = static_cast<VTbAdd0000000001___024root*>(voidSelf);
    VTbAdd0000000001__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    if (!vlSymsp->_vm_contextp__->calcUnusedSigs()) {
        VL_FATAL_MT(__FILE__, __LINE__, __FILE__,
            "Turning on wave traces requires Verilated::traceEverOn(true) call before time 0.");
    }
    vlSymsp->__Vm_baseCode = code;
    tracep->pushPrefix(vlSymsp->name(), VerilatedTracePrefixType::SCOPE_MODULE);
    VTbAdd0000000001___024root__trace_decl_types(tracep);
    VTbAdd0000000001___024root__trace_init_top(vlSelf, tracep);
    tracep->popPrefix();
}

VL_ATTR_COLD void VTbAdd0000000001___024root__trace_register(VTbAdd0000000001___024root* vlSelf, VerilatedVcd* tracep);

VL_ATTR_COLD void VTbAdd0000000001::traceBaseModel(VerilatedTraceBaseC* tfp, int levels, int options) {
    (void)levels; (void)options;
    VerilatedVcdC* const stfp = dynamic_cast<VerilatedVcdC*>(tfp);
    if (VL_UNLIKELY(!stfp)) {
        vl_fatal(__FILE__, __LINE__, __FILE__,"'VTbAdd0000000001::trace()' called on non-VerilatedVcdC object;"
            " use --trace-fst with VerilatedFst object, and --trace-vcd with VerilatedVcd object");
    }
    stfp->spTrace()->addModel(this);
    stfp->spTrace()->addInitCb(&trace_init, &(vlSymsp->TOP), name(), false, 28);
    VTbAdd0000000001___024root__trace_register(&(vlSymsp->TOP), stfp->spTrace());
}
