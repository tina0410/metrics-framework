 // module NegCppConfig0000000001 .h
 #pragma once
 #include "QuBLAS.h"
 #include <cmath>

 namespace fxp {
 using QU_IN = Qu<intBits<5>, fracBits<3>, isSigned<false>, QuMode<TRN::TCPL>, OfMode<SAT::ZERO>>;
 using QU_OUT = Qu<intBits<5>, fracBits<3>, isSigned<true>, QuMode<TRN::TCPL>, OfMode<WRP::TCPL>>;
 }
