# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
from pytv.Converter import convert

import PyTB
import PyTU


@convert
def ModuleFxMatchCppConfig(QU_IN: PyTU.QuType, QU_OUT: PyTU.QuType, QU_MODE: PyTU.QuMode, OF_MODE: PyTU.OfMode):
    dwt_int_in, dwt_frac_in = PyTB.calc_qublas_dwt(QU_IN)
    dwt_int_out, dwt_frac_out = PyTB.calc_qublas_dwt(QU_OUT)
    QuMode_str = QU_MODE.cppType()
    OfMode_str = OF_MODE.cppType()
    is_signed_in_str = QU_IN.isSigned()
    is_signed_out_str = QU_OUT.isSigned()

    #/ // module config.h
    #/ #pragma once
    #/ #include "QuBLAS.h"
    #/ #include <cmath>

    #/ namespace fxp {
    #/   using QU_IN = Qu<intBits<`dwt_int_in`>, fracBits<`dwt_frac_in`>, isSigned<`is_signed_in_str`>, QuMode<`QuMode_str`>, OfMode<`OfMode_str`>>;
    #/   using QU_OUT = Qu<intBits<`dwt_int_out`>, fracBits<`dwt_frac_out`>, isSigned<`is_signed_out_str`>, QuMode<`QuMode_str`>, OfMode<`OfMode_str`>>;
    #/ } // for testing
    pass


@convert
def ModuleFxMatchCppRun(N_FRAMES: int, DWT_IN: int, FRAC_IN: int):
    #/ // module FxMatch.cpp
    #/ # include<iostream>
    #/ # include<QuBLAS.h>
    #/ # include<utility>
    #/ # include<fstream>
    #/ # include<random>
    #/ # include "config.h"
    #/ size_t randint(size_t N) {
    #/     std::random_device rd; // Obtain a random number from hardware
    #/     std::mt19937 gen(rd()); // Seed the generator
    #/     std::uniform_int_distribution<> distr(1, N); // Define the range
    #/     return distr(gen); // Generate a random number in the range [1, N]
    #/ }
    #/ int main() {
    #/     // fstreams
    #/     std::ofstream  f_i_data("../Input_Files/fxmatch_i_data.txt");
    #/     std::ofstream  f_o_data("../Comparison_Files/fxmatch_o_data.txt");
    #/     for (size_t frame = 0; frame < `N_FRAMES`; frame++)
    #/     {
    #/         if(frame<`N_FRAMES-5`){
    #/              fxp::QU_IN  i_data;
    #/              i_data.fill();
    #/              fxp::QU_OUT o_data = i_data;
    #/              // std::cout << "i_data:   " <<   i_data.toString() << endl;
    #/              // std::cout << "o_data:  " <<   o_data.toString() << endl;
    #/              // write input data to Input_Files/fxm_i_data.txt
    #/              f_i_data << i_data.toString() << std::endl;
    #/              // write output data to Comparison_Files/fxm_o_data.txt
    #/              f_o_data << o_data.toString() << std::endl;
    #/         }
    #/         if(frame==95){
    #/              fxp::QU_IN  i_data;
    if FRAC_IN > 0:
        #/              i_data = pow(2, -`FRAC_IN`-1);
        pass
    else:
        #/              i_data = pow(2, abs(`FRAC_IN`)-1);
        pass
    #/              fxp::QU_OUT o_data = i_data;
    #/              // std::cout << "i_data:   " <<   i_data.toString() << endl;
    #/              // std::cout << "o_data:  " <<   o_data.toString() << endl;
    #/              // write input data to Input_Files/fxm_i_data.txt
    #/              f_i_data << i_data.toString() << std::endl;
    #/              // write output data to Comparison_Files/fxm_o_data.txt
    #/              f_o_data << o_data.toString() << std::endl;
    #/         }
    #/         if(frame==96){
    #/              fxp::QU_IN  i_data;
    if FRAC_IN > 0:
        #/              i_data = pow(2, `DWT_IN`-`FRAC_IN`-1)-pow(2, -`FRAC_IN`);
        pass
    else:
        #/              i_data = pow(2, `DWT_IN`+abs(`FRAC_IN`)-1)-pow(2, abs(`FRAC_IN`));
        pass
    #/              fxp::QU_OUT o_data = i_data;
    #/              // std::cout << "i_data:   " <<   i_data.toString() << endl;
    #/              // std::cout << "o_data:  " <<   o_data.toString() << endl;
    #/              // write input data to Input_Files/fxm_i_data.txt
    #/              f_i_data << i_data.toString() << std::endl;
    #/              // write output data to Comparison_Files/fxm_o_data.txt
    #/              f_o_data << o_data.toString() << std::endl;
    #/         }
    #/         if(frame==97){
    #/              fxp::QU_IN  i_data;
    if FRAC_IN > 0:
        #/              i_data = pow(2, -`FRAC_IN`);
        pass
    else:
        #/              i_data = pow(2, abs(`FRAC_IN`));
        pass
    #/              fxp::QU_OUT o_data = i_data;
    #/              // std::cout << "i_data:   " <<   i_data.toString() << endl;
    #/              // std::cout << "o_data:  " <<   o_data.toString() << endl;
    #/              // write input data to Input_Files/fxm_i_data.txt
    #/              f_i_data << i_data.toString() << std::endl;
    #/              // write output data to Comparison_Files/fxm_o_data.txt
    #/              f_o_data << o_data.toString() << std::endl;
    #/         }
    #/         if(frame==98){
    #/              fxp::QU_IN  i_data;
    if FRAC_IN > 0:
        #/              i_data = pow(2, `DWT_IN`-`FRAC_IN`)-pow(2, -`FRAC_IN`);
        pass
    else:
        #/              i_data = pow(2, `DWT_IN`+abs(`FRAC_IN`))-pow(2, abs(`FRAC_IN`));
        pass
    #/              fxp::QU_OUT o_data = i_data;
    #/              // std::cout << "i_data:   " <<   i_data.toString() << endl;
    #/              // std::cout << "o_data:  " <<   o_data.toString() << endl;
    #/              // write input data to Input_Files/fxm_i_data.txt
    #/              f_i_data << i_data.toString() << std::endl;
    #/              // write output data to Comparison_Files/fxm_o_data.txt
    #/              f_o_data << o_data.toString() << std::endl;
    #/         }
    #/         if(frame==99){
    #/              fxp::QU_IN  i_data;
    if FRAC_IN > 0:
        #/              i_data = pow(2, `DWT_IN`-`FRAC_IN`-1);
        pass
    else:
        #/              i_data = pow(2, `DWT_IN`+abs(`FRAC_IN`)-1);
        pass
    #/              fxp::QU_OUT o_data = i_data;
    #/              // std::cout << "i_data:   " <<   i_data.toString() << endl;
    #/              // std::cout << "o_data:  " <<   o_data.toString() << endl;
    #/              // write input data to Input_Files/fxm_i_data.txt
    #/              f_i_data << i_data.toString() << std::endl;
    #/              // write output data to Comparison_Files/fxm_o_data.txt
    #/              f_o_data << o_data.toString() << std::endl;
    #/         }
    #/     }
    #/ }
    pass
