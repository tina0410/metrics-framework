# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
from pytv.Converter import convert

import PyTB
import PyTU


@convert
def ModuleNegCppConfig(QU_IN: PyTU.QuType, QU_OUT: PyTU.QuType, QU_MODE: PyTU.QuMode, OF_MODE: PyTU.OfMode):
    dwt_int_in, dwt_frac_in = PyTB.calc_qublas_dwt(QU_IN)
    dwt_int_out, dwt_frac_out = PyTB.calc_qublas_dwt(QU_OUT)
    qu_mode_str = QU_MODE.cppType()
    of_mode_str = OF_MODE.cppType()
    is_signed_in_str = QU_IN.isSigned()
    is_signed_out_str = QU_OUT.isSigned()

    #/ // module config.h
    #/ #pragma once
    #/ #include "QuBLAS.h"
    #/ #include <cmath>
    #/
    #/ namespace fxp {
    #/ using QU_IN = Qu<intBits<`dwt_int_in`>, fracBits<`dwt_frac_in`>, isSigned<`is_signed_in_str`>, QuMode<`qu_mode_str`>, OfMode<SAT::ZERO>>;
    #/ using QU_OUT = Qu<intBits<`dwt_int_out`>, fracBits<`dwt_frac_out`>, isSigned<`is_signed_out_str`>, QuMode<`qu_mode_str`>, OfMode<`of_mode_str`>>;
    #/ }
    pass


@convert
def ModuleNegCppRun(N_FRAMES: int, DWT_IN: int, FRAC_IN: int, IF_SIGNED_IN: bool):
    #/ // module Neg.cpp
    #/ #include <cmath>
    #/ #include <fstream>
    #/ #include <QuBLAS.h>
    #/ #include "config.h"
    #/
    #/ int main() {
    #/     const size_t N_FRAMES = `N_FRAMES`;
    #/     std::ofstream f_i_data("../Input_Files/neg_i_data.txt");
    #/     std::ofstream f_o_data("../Comparison_Files/neg_o_data.txt");
    #/
    #/     for (size_t frame = 0; frame < N_FRAMES; ++frame) {
    #/         fxp::QU_IN a;
    #/         fxp::QU_OUT o_data;
    #/
    #/         if (frame == 0) {
    #/             a = 0;
    #/         }
    if IF_SIGNED_IN:
        #/         else if (frame == 1) {
        #/             a = -std::pow(2.0, `DWT_IN - FRAC_IN - 1`);
        #/         }
        #/         else if (frame == 2) {
        #/             a = std::pow(2.0, `DWT_IN - FRAC_IN - 1`) - std::pow(2.0, `-FRAC_IN`);
        #/         }
        #/         else if (frame == 3) {
        #/             a = -std::pow(2.0, `-FRAC_IN`);
        #/         }
        #/         else if (frame == 4) {
        #/             a = std::pow(2.0, `-FRAC_IN`);
        #/         }
        pass
    else:
        #/         else if (frame == 1) {
        #/             a = std::pow(2.0, `DWT_IN - FRAC_IN`) - std::pow(2.0, `-FRAC_IN`);
        #/         }
        #/         else if (frame == 2) {
        #/             a = std::pow(2.0, `-FRAC_IN`);
        #/         }
        #/         else if (frame == 3) {
        #/             a = std::pow(2.0, `DWT_IN - FRAC_IN - 1`);
        #/         }
        #/         else if (frame == 4) {
        #/             a = 0;
        #/         }
        pass
    #/         else {
    #/             a.fill();
    #/         }
    #/
    #/         o_data = Qneg<fxp::QU_OUT>(a);
    #/         f_i_data << a.toString() << std::endl;
    #/         f_o_data << o_data.toString() << std::endl;
    #/     }
    #/
    #/     return 0;
    #/ }
    pass
