# coding = utf-8
# Last Modified Date: 2025.3.12
# Author: Jiayan Xu
# Author: LiPtP
# Description:
# A Verithon file generating Cpp Verification Files.
import pdb
from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader

# Modify version at here
import sys
import os
import PyTB
from PyTU import QuMode, OfMode, QuType
import math

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@convert
def ModuleCppConfig():
    #/ // module config.h
    #!  LANGUAGE_MODE = "CPP"
    #/ #pragma once
    #/ #include "QuBLAS.h"
    #/ #include <cmath>
    #/ #include <fstream>
    #/ 
    #/ 
    #/ namespace fxp {
    #/ 
    #/     constexpr int ceil_log2(int x) {
    #/         if (x <= 0) return -1;
    #/         int result = 0;
    #/         --x;
    #/         while (x > 0) {
    #/             x >>= 1;
    #/             ++result;
    #/         }
    #/         return result;
    #/     }
    #/ 
    #/     constexpr int ceil_div(int x, int y) {
    #/         return (x + y - 1) / y;
    #/     }
    #/ 
    #/     template<typename T>
    #/     constexpr T max(T a, T b) {
    #/         return a > b ? a : b;
    #/     }
    #/     template<int intAugBits, typename QuType>
    #/     using AugQu = Qu<intBits<QuType::intB + intAugBits>, fracBits<QuType::fracB>, isSigned<QuType::isS>, QuMode<typename QuType::QuM_t>, OfMode<typename QuType::OfM_t>>;
    #/ 
    #/     template<typename QuT1, typename QuT2>
    #/     using MulQu = Qu< intBits<QuT1::intB + QuT2::intB>, fracBits<QuT1::fracB + QuT2::fracB>, isSigned<QuT1::isS>, QuMode<typename QuT1::QuM_t>, OfMode<typename QuT1::OfM_t>>;
    #/ 
    #/     template<size_t N, typename QuType>
    #/     using TreeQu = AugQu<ceil_log2(N), QuType>;
    #/ 
    #/     template<size_t N>
    #/     using Bits = Qu<intBits<N>, fracBits<0>, isSigned<false>, QuMode<TRN::TCPL>, OfMode<WRP::TCPL>>;
    #/ 
    #/     using bit =  Qu<intBits<1>, fracBits<0>, isSigned<false>, QuMode<TRN::TCPL>, OfMode<WRP::TCPL>>;
    #/ 
    #/     template<size_t N>
    #/     using CntQu = Bits<ceil_log2(N)>;
    #/ 
    #/     template<typename QuType>
    #/     using InputQu = Qu<intBits<QuType::intB>, fracBits<QuType::fracB>, isSigned<QuType::isS>, QuMode<RND::INF>, OfMode<SAT::TCPL>>;
    #/ 
    #/     template<typename QuType>
    #/     using AbsQu = Qu<intBits<QuType::intB + 1>, fracBits<QuType::fracB>, isSigned<false>, QuMode<typename QuType::QuM_t>, OfMode<typename QuType::OfM_t>>;
    #/ 
    #/     size_t randint(size_t N) {
    #/         std::random_device rd; // Obtain a random number from hardware
    #/         std::mt19937 gen(rd()); // Seed the generator
    #/         std::uniform_int_distribution<> distr(1, N); // Define the range
    #/         return distr(gen); // Generate a random number in the range [1, N]
    #/     }
    #/ 
    #/     template<typename QuType>
    #/     double urandfill() {
    #/         return static_cast<double>(randint(1 << (QuType::intB + QuType::fracB))-1) / (1 << QuType::fracB);
    #/     }
    #/ 
    #/     template<typename QuType>
    #/     double randfill() {
    #/         if (randint(2) == 1) {
    #/             return urandfill<QuType>();
    #/         } else {
    #/             return -urandfill<QuType>();
    #/         }
    #/     }
    #/ 
    #/ 
    #/     constexpr bit QuOne = 1;
    #/     constexpr bit QuZero = 0;
    #/ 
    #/ }
    #/ 
    #/ namespace LSCE {
    #/ 
    #/     template <size_t M, size_t V, typename QU_M, typename QU_V, typename QU_M_V, typename QU_OUT>
    #/     inline void M2V(
    #/         Qu<dim<M, V>, QU_M> &i_matrix,
    #/         Qu<dim<V>, QU_V> &i_vector,
    #/         Qu<dim<M>, QU_OUT> &o_result
    #/     ) {
    #/         // Multiplication
    #/         std::array<Qu<dim<V>, QU_M_V>, M> mult_result_temp;
    #/         for (size_t m = 0; m < M; ++m) {
    #/             for (size_t v = 0; v < V; ++v) {
    #/                 mult_result_temp[m][v] = Qmul<QU_M_V>(i_matrix[m, v], i_vector[v]);
    #/             }
    #/         }
    #/         // Adder Tree
    #/         for (size_t m = 0; m < M; ++m) {
    #/             o_result[m] = Qreduce<fxp::TreeQu<V, QU_M_V>>(mult_result_temp[m]);
    #/         }
    #/     }
    #/ 
    #/     template <size_t N_T, size_t P_T, size_t P_R, typename QU_Y, typename QU_P, typename QU_H, typename QU_M_V>
    #/     inline void LSCE_ACC(
    #/         Qu<dim<P_R, N_T>, QU_Y> &i_Y,
    #/         Qu<dim<N_T>, QU_P> &i_P,
    #/         Qu<dim<P_R>, QU_H> &o_H
    #/     ) {
    #/         // Parse the input dimensions
    #/         constexpr size_t STG_T = fxp::ceil_div(N_T, P_T);
    #/         if constexpr (STG_T <= 1) {
    #/             // Skip Accumulation
    #/             LSCE::M2V<P_R, P_T, QU_Y, QU_P, QU_M_V, QU_H>(i_Y, i_P, o_H);
    #/         } 
    #/         else {
    #/             // Set to Zero
    #/             o_H.fill(0);
    #/             // Temp Inputs
    #/             Qu<dim<P_R, P_T>, QU_Y> i_Y_temp;
    #/             Qu<dim<P_T>, QU_P> i_P_temp;
    #/             // Temp M2V Results
    #/             Qu<dim<P_R>, QU_H> H_temp;
    #/             for (size_t stg = 0; stg < STG_T; ++stg) {
    #/                 // Y Input
    #/                 for (size_t r = 0; r < P_R; ++r) {
    #/                     for (size_t t = 0; t < P_T; ++t) {
    #/                         i_Y_temp[r, t] = i_Y[r, stg * P_T + t];
    #/                     }
    #/                 }
    #/                 // P Input
    #/                 for (size_t t = 0; t < P_T; ++t) {
    #/                     i_P_temp[t] = i_P[stg * P_T + t];
    #/                 }
    #/                 // M2V Operation
    #/                 M2V<P_R, P_T, QU_Y, QU_P, QU_M_V, QU_H>(i_Y_temp, i_P_temp, H_temp);
    #/                 // Accumulate Results
    #/                 for (size_t r = 0; r < P_R; ++r) {
    #/                     o_H[r] = Qadd<QU_H>(o_H[r], H_temp[r]);
    #/                 }
    #/             }
    #/         }
    #/     }
    #/ 
    #/ 
    #/     template <size_t N_T, size_t N_R, size_t P_T, size_t P_R, typename QU_Y, typename QU_P, typename QU_H, typename QU_M_V>
    #/     inline void LSCE(
    #/         Qu<dim<N_R, N_T>, QU_Y> &i_Y, // Y
    #/         Qu<dim<N_T, N_T>, QU_P> &i_P, // P conjugate-transpose
    #/         Qu<dim<N_R, N_T>, QU_H> &o_H // H
    #/     ) {
    #/         // M2M is first reduced to M2V
    #/         // For Each column of P, perform Y * P conjugate-transpose_{i}
    #/         Qu<dim<N_T>, QU_P> i_P_col;
    #/         Qu<dim<P_R, N_T>, QU_Y> i_Y_group;
    #/         Qu<dim<P_R>, QU_H> H_group;
    #/         for (size_t col = 0; col < N_T; ++col) {
    #/             // Extract the column of P
    #/             for (size_t row = 0; row < N_T; ++row) {
    #/                 i_P_col[row] = i_P[row, col];
    #/             }
    #/             // Perform M2V for each group of P_R rows
    #/             static_assert(N_R % P_R == 0, "N_R must be divisible by P_R");
    #/             for (size_t r = 0; r < N_R; r += P_R) {
    #/                 // Extract the group of rows from Y
    #/                 for (size_t pr = 0; pr < P_R; ++pr) {
    #/                     for (size_t t = 0; t < N_T; ++t) {
    #/                         i_Y_group[pr, t] = i_Y[r + pr, t];
    #/                     }
    #/                 }
    #/                 // Perform M2V operation
    #/                 LSCE_ACC<N_T, P_T, P_R, QU_Y, QU_P, QU_H, QU_M_V>(i_Y_group, i_P_col, H_group);
    #/                 // Write the results back to H
    #/                 for (size_t pr = 0; pr < P_R; ++pr) {
    #/                     o_H[r + pr, col] = H_group[pr];
    #/                 }
    #/             }
    #/         }
    #/     }
    #/ }
    #!
    pass

@convert
def ModuleCppRun(N_T:int, N_R:int, P_T:int, P_R:int, QU_Y:QuType, QU_P:QuType, QU_H:QuType, QU_M_V:QuType, QU_MODE:QuMode, OF_MODE:OfMode, N_PIPELINES:list=[1, 1], input_file_dir="../../Input_Files", comparison_file_dir="../../Comparison_Files", N_FRAMES=50):
    # Parse the input arguments
    STG_T = math.ceil(N_T / P_T)
    # End of Input Argument Parsing #
    #/  // module main.cpp
    #!  LANGUAGE_MODE = "CPP"
    #/  #include "QuBLAS.h"
    #/  #include <iostream>
    #/  #include <fstream>
    #/  #include "config.h"
    #/ 
    #/  int main() {
    #/     // Verification Params
    #/     constexpr size_t N_FRAMES = `N_FRAMES`;
    #/     // Module Params
    #/     constexpr size_t N_T = `N_T`;
    #/     constexpr size_t N_R = `N_R`;
    #/     constexpr size_t P_T = `P_T`;
    #/     constexpr size_t P_R = `P_R`;
    #/     using QU_Y = Qu<intBits<`QU_Y.intBits()`>, fracBits<`QU_Y.fracBits()`>, isSigned<`QU_Y.isSigned()`>, QuMode<`QU_MODE.cppType()`>, OfMode<`OF_MODE.cppType()`>>;
    #/     using QU_P = Qu<intBits<`QU_P.intBits()`>, fracBits<`QU_P.fracBits()`>, isSigned<`QU_P.isSigned()`>, QuMode<`QU_MODE.cppType()`>, OfMode<`OF_MODE.cppType()`>>;
    #/     using QU_H = Qu<intBits<`QU_H.intBits()`>, fracBits<`QU_H.fracBits()`>, isSigned<`QU_H.isSigned()`>, QuMode<`QU_MODE.cppType()`>, OfMode<`OF_MODE.cppType()`>>;
    #/     using QU_M_V = Qu<intBits<`QU_M_V.intBits()`>, fracBits<`QU_M_V.fracBits()`>, isSigned<`QU_M_V.isSigned()`>, QuMode<`QU_MODE.cppType()`>, OfMode<`OF_MODE.cppType()`>>;
    #/     constexpr std::array<size_t, 2> N_PIPELINES = {`N_PIPELINES[0]`, `N_PIPELINES[1]`};
    #/     constexpr size_t STG_T = fxp::ceil_div(N_T, P_T);
    #/     // fstreams
    #/     std::ofstream f_i_Y("`input_file_dir`/i_Y.txt"); std::ofstream f_i_Y_d("`input_file_dir`/Decimal_i_Y.txt");
    #/     std::ofstream f_i_P("`input_file_dir`/i_P.txt"); std::ofstream f_i_P_d("`input_file_dir`/Decimal_i_P.txt");
    #/     std::ofstream f_o_H("`comparison_file_dir`/o_H.txt"); std::ofstream f_o_H_d("`comparison_file_dir`/Decimal_o_H.txt");
    #/     std::ofstream f_i_ctrl_stg("`input_file_dir`/i_ctrl_stg.txt"); std::ofstream f_i_ctrl_stg_d("`input_file_dir`/Decimal_i_ctrl_stg.txt");
    #/      // Input & Output
    #/      Qu<dim<P_R, N_T>, QU_Y> i_Y; Qu<dim<P_R, P_T>, QU_Y> i_Y_grp;
    #/      Qu<dim<N_T>, QU_P> i_P; Qu<dim<P_T>, QU_P> i_P_grp;
    #/      Qu<dim<P_R>, QU_H> o_H;
    #/      // Control
    #/      fxp::Bits<2> i_ctrl_stg;
    #/      // Control Prefix 
    if STG_T > 1:
        #/     for (size_t i = 0; i < N_PIPELINES[0] + N_PIPELINES[1]; ++i) {
        #/         i_ctrl_stg = 0;
        #/         f_i_ctrl_stg << i_ctrl_stg.toString() << std::endl; f_i_ctrl_stg_d << i_ctrl_stg.toDouble() << std::endl;
        #/     }
        pass
    #/     
    #/      for (size_t frame = 0; frame < N_FRAMES; ++frame) {
    #/          // Drive signal
    #/          i_Y.fill();
    #/          i_P.fill();
    #/          // Input is writen to file every frame
    #/          for (size_t stg = 0; stg < STG_T; ++stg) {
    #/              // Extract the columns of Y
    #/              for (size_t r = 0; r < P_R; ++r) {
    #/                  for (size_t t = 0; t < P_T; ++t) {
    #/                      i_Y_grp[r, t] = i_Y[r, stg * P_T + t];
    #/                  }
    #/              }
    #/              // Extract the columns of P
    #/              for (size_t t = 0; t < P_T; ++t) {
    #/                  i_P_grp[t] = i_P[stg * P_T + t];  
    #/              }
    #/              // Write to file
    #/              for (size_t v = P_T; v > 0; --v) {
    #/                  f_i_P << i_P_grp[v-1].toString(); f_i_P_d << i_P_grp[v-1].toDouble() << " ";
    #/                  for (size_t m = P_R; m > 0; --m) {
    #/                      f_i_Y << i_Y_grp[m-1, v-1].toString(); f_i_Y_d << i_Y_grp[m-1, v-1].toDouble() << " ";
    #/                  }
    #/              }
    #/              f_i_P << std::endl; f_i_P_d << std::endl;
    #/              f_i_Y << std::endl; f_i_Y_d << std::endl;
    #/              if (STG_T > 1) {
    #/                  // Write control signal
    #/                  i_ctrl_stg = (stg == 0) ? 1 : 2;
    #/                  f_i_ctrl_stg << i_ctrl_stg.toString() << std::endl; f_i_ctrl_stg_d << i_ctrl_stg.toDouble() << std::endl;
    #/              }
    #/          }  
    #/          // Perform LSCE 
    #/          LSCE::LSCE_ACC<N_T, P_T, P_R, QU_Y, QU_P, QU_H, QU_M_V>(i_Y, i_P, o_H);
    #/          // Dump Output
    #/          for (size_t r = P_R; r > 0; --r) {
    #/             f_o_H << o_H[r-1].toString(); f_o_H_d << o_H[r-1].toDouble() << " ";
    #/          }
    #/          f_o_H << std::endl; f_o_H_d << std::endl;    
    #/      }
    #/      // Close fstreams
    #/      f_i_Y.close(); f_i_Y_d.close();
    #/      f_i_P.close(); f_i_P_d.close();
    #/      f_o_H.close(); f_o_H_d.close();
    #/      f_i_ctrl_stg.close(); f_i_ctrl_stg_d.close();
    #/  }
    #!
    
    pass    




