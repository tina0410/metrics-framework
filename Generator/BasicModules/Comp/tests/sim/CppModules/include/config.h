 // module CppConfigComp0000000001 .h
 #pragma once
 #include "QuBLAS.h"
 #include <cmath>
 namespace fxp {
   using QU_IN_1= Qu<intBits<3>, fracBits<4>, isSigned<true>, QuMode<TRN::TCPL>, OfMode<SAT::ZERO>>;
   using QU_IN_2= Qu<intBits<-3>, fracBits<7>, isSigned<true>, QuMode<TRN::TCPL>, OfMode<SAT::ZERO>>;
   using GVAL = Qu<intBits<0>, fracBits<3>, isSigned<true>, QuMode<TRN::TCPL>, OfMode<WRP::TCPL>>;
   using LVAL = Qu<intBits<0>, fracBits<3>, isSigned<true>, QuMode<TRN::TCPL>, OfMode<WRP::TCPL>>;
 } // for testing
