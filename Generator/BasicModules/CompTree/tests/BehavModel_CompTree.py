# Author: AutoHDW
# Version: 1.0.0
# Date: 2026.9.1
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

import PyTB
import PyTU


@convert
def ModuleCppConfigCompTree(QU_IN: PyTU.QuType, QU_OUT: PyTU.QuType, QU_MODE: PyTU.QuMode, OF_MODE: PyTU.OfMode, N_INPUTS):
    dwt_int_in, dwt_frac_in = PyTB.calc_qublas_dwt(QU_IN)
    dwt_int_out, dwt_frac_out = PyTB.calc_qublas_dwt(QU_OUT)
    QuMode_str = QU_MODE.cppType()
    OfMode_str = OF_MODE.cppType()
    is_signed_in_str = QU_IN.isSigned()
    is_signed_out_str = QU_OUT.isSigned()
    #! LANGUAGE_MODE = "CPP"
    #/ // module config.h
    #/ #pragma once
    #/ #include "QuBLAS.h"
    #/ #include <cmath>

    #/ namespace fxp {
    #/   using QU_IN_1= Qu<intBits<`dwt_int_in`>, fracBits<`dwt_frac_in`>, isSigned<`is_signed_in_str`>, QuMode<`QuMode_str`>, OfMode<`OfMode_str`>>;
    #/   using QU_OUT = Qu<intBits<`dwt_int_out`>, fracBits<`dwt_frac_out`>, isSigned<`is_signed_out_str`>, QuMode<`QuMode_str`>, OfMode<`OfMode_str`>>;
    #/   using QU_IN = Qu<dim<`N_INPUTS`>, QU_IN_1>;

    #/   template<int intAugBits, typename QuType>
    #/   using AugQu = Qu<intBits<QuType::intB + intAugBits>, fracBits<QuType::fracB>, isSigned<QuType::isS>, QuMode<typename QuType::QuM_t>, OfMode<typename QuType::OfM_t>>;

    #/   template<typename QuT1, typename QuT2>
    #/   using MulQu = Qu< intBits<QuT1::intB + QuT2::intB>, fracBits<QuT1::fracB + QuT2::fracB>, isSigned<QuT1::isS>, QuMode<typename QuT1::QuM>, OfMode<typename QuT1::OfM> >;

    #/   constexpr int ceil_log2(int x) {
    #/        if (x <= 0) return -1;
    #/        int result = 0;
    #/        --x;
    #/        while (x > 0) {
    #/            x >>= 1;
    #/            ++result;
    #/        }
    #/        return result;
    #/   }

    #/   template<size_t N, typename QuType>
    #/   using TreeQu = AugQu<ceil_log2(N), QuType>;
    #/   constexpr size_t dim_P = ceil_log2(`N_INPUTS`);
    #/ } // for testing
    #!
    pass


@convert
def ModuleCppRunCompTree(N_FRAMES, N_INPUTS):
    #/ // module AdderTree.cpp
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
    #/    template<typename QuType>
    #/    double urandfill() {
    #/        return static_cast<double>(randint(1 << (QuType::intB + QuType::fracB))-1) / (1 << QuType::fracB);
    #/    }
    #/ int main() {
    #/     // verification params
    #/     size_t N_FRAMES = `N_FRAMES`;
    #/     // fstreams
    #/     std::ofstream  f_i_data("../Input_Files/CompTree_i_data.txt");
    #/     std::ofstream  f_o_data("../Comparison_Files/CompTree_o_data.txt");
    #/     std::ofstream f_gpos("../Comparison_Files/CompTree_o_gidx.txt");
    #/     std::ofstream df_gpos("../Comparison_Files/gpos.txt");
    #/     for (size_t frame = 0; frame < N_FRAMES; frame++)
    #/     {
    #/         fxp::QU_IN  i_data;
    #/         int gpos_s = 0;
    #/         //fxp::QU_OUT   o_data;
    #/         //i_data[0]=urandfill<fxp::QU_IN_1>();
    #/         //for(int i=1; i<`N_INPUTS`;i++){i_data[i]=i_data[0];}
    #/         for(int i=0; i<`N_INPUTS`;i++){i_data[i]=urandfill<fxp::QU_IN_1>();}
    #/          //i_data.fill();
    #/         const int n_layer = std::ceil(std::log2(`N_INPUTS`));
    #/         std::vector<int> indices(`N_INPUTS`);
    #/         for (int i = 0; i <`N_INPUTS`; i++) {
    #/             indices[i] = `N_INPUTS` - i - 1;
    #/         }
    #/         for (int l = 1; l < `N_INPUTS`; l++) {
    #/              if (i_data[gpos_s] <= i_data[l]){
    #/                  gpos_s = l;
    #/              }
    #/         }
    #/         gpos_s = indices[gpos_s];
    #/
    #/         std::bitset<fxp::dim_P> gpos_b(gpos_s);
    #/         fxp::QU_OUT o_data=i_data[`N_INPUTS` - 1 - gpos_s];
    #/         for(size_t input= 0; input<`N_INPUTS`; input++ ){f_i_data << i_data[input].toString();}
    #/         f_i_data << std::endl;
    #/         // f_i_data << BitStream<l2r, l2r>(i_data)<<std::endl;
    #/         //f_i_data <<std::endl;
    #/         f_o_data << o_data.toString()<< std::endl;
    #/         //df_gpos << indices[0] << std::endl;
    #/         f_gpos << gpos_b << std::endl;
    #/     }
    #/     return 0;
    #/ }
    pass
