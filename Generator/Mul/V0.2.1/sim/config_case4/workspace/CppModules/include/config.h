 // module CppConfig0000000001 .h
 #pragma once
 #include "QuBLAS.h"
 #include <cmath>
 namespace fxp {
   using QU_IN_1= Qu<intBits<3>, fracBits<2>, isSigned<false>, QuMode<TRN::TCPL>, OfMode<SAT::ZERO>>;
   using QU_IN_2= Qu<intBits<4>, fracBits<2>, isSigned<false>, QuMode<TRN::TCPL>, OfMode<SAT::ZERO>>;
   using QU_OUT = Qu<intBits<4>, fracBits<4>, isSigned<false>, QuMode<TRN::TCPL>, OfMode<WRP::TCPL>>;
 } // for testing
