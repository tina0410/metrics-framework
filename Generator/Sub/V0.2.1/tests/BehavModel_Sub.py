from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

# Modify version at here
import sys
import os
import PyTB
import PyTU

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@ convert
def ModuleCppConfig(QU_IN_1:PyTU.QuType, QU_IN_2:PyTU.QuType, QU_OUT:PyTU.QuType, QU_MODE:PyTU.QuMode, OF_MODE:PyTU.OfMode):
    dwt_int_in_1, dwt_frac_in_1 = PyTB.calc_qublas_dwt(QU_IN_1)
    dwt_int_in_2, dwt_frac_in_2 = PyTB.calc_qublas_dwt(QU_IN_2)
    dwt_int_out, dwt_frac_out = PyTB.calc_qublas_dwt(QU_OUT)
    QuMode_dict = {PyTU.QuMode.TRN.TCPL: "TRN::TCPL", PyTU.QuMode.TRN.SMGN: "TRN::SMGN", PyTU.QuMode.RND.POS_INF: "RND::POS_INF", PyTU.QuMode.RND.NEG_INF: "RND::NEG_INF", 
                   PyTU.QuMode.RND.INF: "RND::INF", PyTU.QuMode.RND.ZERO: "RND::ZERO",PyTU.QuMode.RND.CONV: "RND::CONV"}
    OfMode_dict = {PyTU.OfMode.WRP.TCPL: "WRP::TCPL", PyTU.OfMode.SAT.TCPL: "SAT::TCPL", PyTU.OfMode.SAT.ZERO: "SAT::ZERO", PyTU.OfMode.SAT.SMGN: "SAT::SMGN"}
    Signed_dict = {True: "true", False: "false"}
    QuMode_str = QuMode_dict[QU_MODE]
    OfMode_str = OfMode_dict[OF_MODE]
    is_signed_in_str_1 = Signed_dict[QU_IN_1.IF_SIGNED]
    is_signed_in_str_2 = Signed_dict[QU_IN_2.IF_SIGNED]
    is_signed_out_str = Signed_dict[QU_OUT.IF_SIGNED]

    #/ // module config.h
    #/ #pragma once
    #/ #include "QuBLAS.h"
    #/ #include <cmath>
    
    #/ namespace fxp {
    #/   using QU_IN_1= Qu<intBits<`dwt_int_in_1`>, fracBits<`dwt_frac_in_1`>, isSigned<`is_signed_in_str_1`>, QuMode<`QuMode_str`>, OfMode<SAT::ZERO>>;
    #/   using QU_IN_2= Qu<intBits<`dwt_int_in_2`>, fracBits<`dwt_frac_in_2`>, isSigned<`is_signed_in_str_2`>, QuMode<`QuMode_str`>, OfMode<SAT::ZERO>>;
    #/   using QU_OUT = Qu<intBits<`dwt_int_out`>, fracBits<`dwt_frac_out`>, isSigned<`is_signed_out_str`>, QuMode<`QuMode_str`>, OfMode<`OfMode_str`>>;
    #/ } // for testing
    pass

@convert
def ModuleCppRun(N_FRAMES):
    #/ // module Add.cpp
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
    #/     // verification params
    #/     size_t N_FRAMES = `N_FRAMES`;
    #/     // fstreams
    #/     std::ofstream  f_i_data_1("../Input_Files/sub_i_data_1.txt");
    #/     std::ofstream  f_i_data_2("../Input_Files/sub_i_data_2.txt");
    #/     std::ofstream  f_o_data("../Comparison_Files/sub_o_data.txt");
    #/     for (size_t frame = 0; frame < N_FRAMES; frame++)
    #/     {
    #/         fxp::QU_IN_1  i_data_1;
    #/         fxp::QU_IN_2  i_data_2;
    #/         fxp::QU_OUT   o_data;
    #/         i_data_1.fill();
    #/         i_data_2.fill();
    #/         o_data = Qsub<fxp::QU_OUT>(i_data_1, i_data_2);
    #/         // write input data to Input_Files/add_i_data_1.txt and Input_Files/add_i_data_2.txt
    #/         f_i_data_1 << i_data_1.toString() << std::endl;
    #/         f_i_data_2 << i_data_2.toString() << std::endl;
    #/         // write output data to Comparison_Files/add_o_data.txt
    #/         f_o_data << o_data.toString() << std::endl;
    #/     }
    #/     return 0;
    #/ }
    pass
            




