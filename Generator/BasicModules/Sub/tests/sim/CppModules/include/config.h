 // module CppConfig0000000001 .h
 #pragma once
 #include "QuBLAS.h"
 #include <cmath>
 namespace fxp {
   using QU_IN_1= Qu<intBits<2>, fracBits<4>, isSigned<true>, QuMode<RND::POS_INF>, OfMode<SAT::ZERO>>;
   using QU_IN_2= Qu<intBits<-3>, fracBits<7>, isSigned<true>, QuMode<RND::POS_INF>, OfMode<SAT::ZERO>>;
   using QU_OUT = Qu<intBits<0>, fracBits<3>, isSigned<true>, QuMode<RND::POS_INF>, OfMode<SAT::TCPL>>;
 } // for testing
