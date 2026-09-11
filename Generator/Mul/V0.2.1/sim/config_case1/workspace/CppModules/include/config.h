 // module CppConfig0000000001 .h
 #pragma once
 #include "QuBLAS.h"
 #include <cmath>
 namespace fxp {
   using QU_IN_1= Qu<intBits<1>, fracBits<2>, isSigned<true>, QuMode<TRN::TCPL>, OfMode<SAT::ZERO>>;
   using QU_IN_2= Qu<intBits<1>, fracBits<2>, isSigned<true>, QuMode<TRN::TCPL>, OfMode<SAT::ZERO>>;
   using QU_OUT = Qu<intBits<3>, fracBits<3>, isSigned<true>, QuMode<TRN::TCPL>, OfMode<WRP::TCPL>>;
 } // for testing
