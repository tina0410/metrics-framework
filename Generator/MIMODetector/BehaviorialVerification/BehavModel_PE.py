from pytv.Converter import convert
from pytv.ModuleLoader import moduleloader
from collections import OrderedDict
# Modify version at here
import sys
import os
import PyTB
import PyTU
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@ convert
def ModuleCppConfig(QU:PyTU.QuType, QU_MODE:PyTU.QuMode, OF_MODE:PyTU.OfMode, Eq, I=3,J=4,K=5):
    outputs = {eq[0] for eq in Eq}  # {'C', 'E'}
    input_info = OrderedDict()  # 存储变量及其首次出现的位置

    for eq_idx, eq in enumerate(Eq):
        for var_idx, var in enumerate(eq[1:], start=1):  # 跳过输出变量（索引0）
            if var not in input_info and var not in outputs:
                input_info[var] = (eq_idx, var_idx)

    input_elements = list(input_info.keys())  # 保持顺序的输入变量 ['A', 'B', 'D']
    input_indices = list(input_info.values())  # 对应的首次出现位置 [(0, 1), (0, 2), (1, 1)]
    
    all_outputs = []
    all_indices = []
    for i, eq in enumerate(Eq):
        all_outputs.append(eq[0])  # 收集输出变量
        all_indices.append((i, 0))  # 记录位置 (方程索引, 0)
    used_vars = set()
    for eq in Eq:
        used_vars.update(eq[1:])  # 收集所有输入变量
    final_outputs = []
    final_indices = []
    for var, idx in zip(all_outputs, all_indices):
        if var not in used_vars:
            final_outputs.append(var)
            final_indices.append(idx)
    intermediate_outputs = []
    intermediate_indices = []
    for var, idx in zip(all_outputs, all_indices):
        if var in used_vars:  # 被其他方程使用过的输出变量
            intermediate_outputs.append(var)
            intermediate_indices.append(idx)
    dwt_int={}
    dwt_frac={} 
    is_signed={}       
    # dwt_int_in_1, dwt_frac_in_1 = PyTB.calc_qublas_dwt(QU_IN_1)
    # dwt_int_in_2, dwt_frac_in_2 = PyTB.calc_qublas_dwt(QU_IN_2)
    # dwt_int_out, dwt_frac_out = PyTB.calc_qublas_dwt(QU_OUT)
    Signed_dict = {True: "true", False: "false"}
    for key, value in QU.items():
        dwt_int[key], dwt_frac[key] = PyTB.calc_qublas_dwt(value)
        is_signed[key]=Signed_dict[value.IF_SIGNED]
    QuMode_dict = {PyTU.QuMode.TRN.TCPL: "TRN::TCPL", PyTU.QuMode.TRN.SMGN: "TRN::SMGN", PyTU.QuMode.RND.POS_INF: "RND::POS_INF", PyTU.QuMode.RND.NEG_INF: "RND::NEG_INF", 
                   PyTU.QuMode.RND.INF: "RND::INF", PyTU.QuMode.RND.ZERO: "RND::ZERO",PyTU.QuMode.RND.CONV: "RND::CONV"}
    OfMode_dict = {PyTU.OfMode.WRP.TCPL: "WRP::TCPL", PyTU.OfMode.SAT.TCPL: "SAT::TCPL", PyTU.OfMode.SAT.ZERO: "SAT::ZERO", PyTU.OfMode.SAT.SMGN: "SAT::SMGN"}

    QuMode_str = QuMode_dict[QU_MODE]
    OfMode_str = OfMode_dict[OF_MODE]
    # is_signed_in_str = Signed_dict[QU_IN_1.IF_SIGNED]
    # is_signed_out_str = Signed_dict[QU_OUT.IF_SIGNED]

    #/ // module config.h
    #/ #pragma once
    #/ #include "QuBLAS.h"
    #/ #include <cmath>
    
    #/ namespace fxp {
    for key in QU.keys():
        #/   using QU`key`= Qu<intBits<`dwt_int[key]`>, fracBits<`dwt_frac[key]`>, isSigned<`is_signed[key]`>, QuMode<`QuMode_str`>, OfMode<`OfMode_str`>>;
        pass

    for a, b in input_indices:
        if b==1:
            #/   using QU_`Eq[a][b]` = Qu<dim<`I[a]`,`K[a]`>, QU`Eq[a][b]`>;
            pass
        else:
            if Eq[a][b]=='D3' or Eq[a][b]=='D5':
                #/   using QU_`Eq[a][b]` = Qu<dim<`I[a]`,`K[a]`>, QU`Eq[a][b]`>;
                pass
            else:
                #/   using QU_`Eq[a][b]` = Qu<dim<`K[a]`,`J[a]`>, QU`Eq[a][b]`>;
                pass
            pass
    for a, b in intermediate_indices:
        #/   using QU_`Eq[a][b]` = Qu<dim<`I[a]`, `J[b]`>, QU`Eq[a][b]`>;   
        pass
    #/   //using QU_IN_1 = Qu<dim<`I`,`K`>, QU_IN1>;
    #/   //using QU_IN_2 = Qu<dim<`K`, `J`>, QU_IN2>;
    #/   using QU_`Eq[len(Eq)-1][0]` = Qu<dim<`I[len(Eq)-1]`, `J[len(Eq)-1]`>, QU`Eq[len(Eq)-1][0]`>;
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
    #/ } // for testing
    pass

@convert
def ModuleCppRun(iterations, N_FRAMES, T, In_A, start_time_a, end_time_a, In_B, start_time_b, end_time_b, Out_C, start_time_C, end_time_C, code_line, dependency_matrices, transpose, Eq, I=3,J=4,K=5):
    outputs = {eq[0] for eq in Eq}  # {'C', 'E'}
    input_info = OrderedDict()  # 存储变量及其首次出现的位置

    for eq_idx, eq in enumerate(Eq):
        for var_idx, var in enumerate(eq[1:], start=1):  # 跳过输出变量（索引0）
            if var not in input_info and var not in outputs:
                input_info[var] = (eq_idx, var_idx)

    input_elements = list(input_info.keys())  # 保持顺序的输入变量 ['A', 'B', 'D']
    input_indices = list(input_info.values())  # 对应的首次出现位置 [(0, 1), (0, 2), (1, 1)]
    
    all_outputs = []
    all_indices = []
    for i, eq in enumerate(Eq):
        all_outputs.append(eq[0])  # 收集输出变量
        all_indices.append((i, 0))  # 记录位置 (方程索引, 0)
    used_vars = set()
    for eq in Eq:
        used_vars.update(eq[1:])  # 收集所有输入变量
    final_outputs = []
    final_indices = []
    for var, idx in zip(all_outputs, all_indices):
        if var not in used_vars:
            final_outputs.append(var)
            final_indices.append(idx)
    intermediate_outputs = []
    intermediate_indices = []
    for var, idx in zip(all_outputs, all_indices):
        if var in used_vars:  # 被其他方程使用过的输出变量
            intermediate_outputs.append(var)
            intermediate_indices.append(idx)
    #! LANGUAGE_MODE = "CPP"
    #/ // module AdderTree.cpp
    
    
    #/ # include<iostream>
    #/ # include <armadillo>  
    #/ # include<QuBLAS.h>
    #/ # include<utility>
    #/ # include<fstream>
    #/ # include<random>
    #/ # include "PE.h"
    #/ # include "config.h"
    #/ using namespace arma;
    
    #/ size_t randint(size_t N) {
    #/     std::random_device rd; // Obtain a random number from hardware
    #/     std::mt19937 gen(rd()); // Seed the generator
    #/     std::uniform_int_distribution<> distr(1, N); // Define the range
    #/     return distr(gen); // Generate a random number in the range [1, N]
    #/ }
    #/ arma::vec lNSAq(double a, mat D, mat H, vec y, uword test_num) {
    #/     // verification params
    #/     size_t N_FRAMES = `N_FRAMES`;
    #/     // fstreams
    for a, b in input_indices:
        #/     if(test_num==0){std::ofstream clearFile("../Input_Files/PE_i_data_`Eq[a][b]`.txt");} 
        #/     //std::ofstream  f_i_data_`Eq[a][b]`("../Input_Files/PE_i_data_`Eq[a][b]`.txt");
        #/      std::ofstream  f_i_data_`Eq[a][b]`("../Input_Files/PE_i_data_`Eq[a][b]`.txt", std::ios::app);
        pass

    #/     //std::ofstream  f_i_data_1("../Input_Files/PE_i_data_1.txt");

    #/     //std::ofstream  f_i_data_2("../Input_Files/PE_i_data_2.txt");

    #/     
    #/     if(test_num==0){std::ofstream clearFile("../Comparison_Files/PE_o_data.txt");}      
    #/     std::ofstream  f_o_data("../Comparison_Files/PE_o_data.txt", std::ios::app);
    #/     //std::ofstream  f_o_data("../Comparison_Files/PE_o_data.txt");
    #/     //std::ofstream  f_o_data1("../Comparison_Files/PE_o_data1.txt");

    for a, b in input_indices:
        #/         fxp::QU_`Eq[a][b]`  i_data_`Eq[a][b]`;
        pass
    for a, b in input_indices:
        #/         i_data_`Eq[a][b]`.fill();
        pass

    if iterations >= 2:
        #/         for (size_t i = 0; i < `K[0]`; i++) {
        #/               for (size_t j = 0; j < `I[0]`; j++) {
        #/                 i_data_H2[i,j]=i_data_H1[i,j];
        #/               }
        #/         }
        pass
    if iterations==3:
        #/         for (size_t i = 0; i < `K[0]`; i++) {
        #/               for (size_t j = 0; j < `I[0]`; j++) {
        #/                 i_data_H3[i,j]=i_data_H1[i,j];
        #/               }
        #/         }
        #/         for (size_t i = 0; i < `I[0]`; i++) {
        #/                 i_data_D6[i,0]=i_data_D1[i,0];           
        #/         }
        #/         for (size_t i = 0; i < `I[0]`; i++) {
        #/                  i_data_D7[i,0]=i_data_D1[i,0];           
        #/         }
        #/         for (size_t i = 0; i < `I[0]`; i++) {
        #/               for (size_t j = 0; j < `K[0]`; j++) {
        #/                  i_data_HT4[i,j]=i_data_H1[j,i];
        #/               }
        #/         }
        pass

    #/         for (size_t i = 0; i < `I[0]`; i++) {
    #/                  i_data_D2[i,0]=i_data_D1[i,0];           
    #/         }
    #/         for (size_t i = 0; i < `I[0]`; i++) {
    #/                  i_data_D3[i,0]=i_data_D1[i,0];           
    #/         }
    if iterations >= 2:
        #/         for (size_t i = 0; i < `I[0]`; i++) {
        #/                  i_data_D4[i,0]=i_data_D1[i,0];           
        #/         }
        #/         for (size_t i = 0; i < `I[0]`; i++) {
        #/                  i_data_D5[i,0]=i_data_D1[i,0];           
        #/         }
        pass

    #/         for (size_t i = 0; i < `I[0]`; i++) {
    #/               for (size_t j = 0; j < `K[0]`; j++) {
    #/                  i_data_HT1[i,j]=i_data_H1[j,i];
    #/               }
    #/         }
    #/         for (size_t i = 0; i < `I[0]`; i++) {
    #/               for (size_t j = 0; j < `K[0]`; j++) {
    #/                  i_data_HT2[i,j]=i_data_H1[j,i];
    #/               }
    #/         }
    if iterations >= 2:
        #/         for (size_t i = 0; i < `I[0]`; i++) {
        #/               for (size_t j = 0; j < `K[0]`; j++) {
        #/                  i_data_HT3[i,j]=i_data_H1[j,i];
        #/               }
        #/         }
        pass
    for a, b in intermediate_indices:
        #/      fxp::QU_`Eq[a][b]`  data_`Eq[a][b]`;
        #/         for (size_t i = 0; i < `I[a]`; i++) {
        #/               for (size_t j = 0; j < `J[a]`; j++) {
        #/                  data_`Eq[a][b]`[i,j]=0;
        #/               }
        #/         }
        pass 
    #/         //fxp::QU_IN_1  i_data_1;
    #/         //fxp::QU_IN_2  i_data_2;
    #/         fxp::QU_`Eq[len(Eq)-1][0]`   o_data;
    #/         for (size_t i = 0; i < `I[0]`; i++) {
    #/               for (size_t j = 0; j < `J[0]`; j++) {
    #/                  o_data[i,j]=0;
    #/               }
    #/         }
    #/         
    #/         //i_data_1.fill();
    #/         //i_data_2.fill();
    #/         for (size_t i = 0; i < 1; i++) {
    #/                 i_data_a=a;           
    #/         }
###################################################################################################
    for tn in range(len(Eq)):
        if code_line[tn]==0:
            #/         for (size_t i = 0; i < `I[tn]`; i++) {
            #/              for (size_t j = 0; j < `J[tn]`; j++) {
            #/                  for (size_t k = 0; k < `K[tn]`; k++) {
            if  Eq[tn][0] in final_outputs:
                if  Eq[tn][1] in input_elements and Eq[tn][2] in input_elements:
                    #/                      o_data[i,j] = Qadd<fxp::QU`Eq[tn][0]`>(o_data[i,j],Qmul<fxp::QU`Eq[tn][0]`>(i_data_`Eq[tn][1]`[i,k], i_data_`Eq[tn][2]`[k,j]));
                    pass
                elif Eq[tn][1] in input_elements:
                    #/                      o_data[i,j] = Qadd<fxp::QU`Eq[tn][0]`>(o_data[i,j],Qmul<fxp::QU`Eq[tn][0]`>(i_data_`Eq[tn][1]`[i,k], data_`Eq[tn][2]`[k,j]));
                    pass
                elif Eq[tn][2] in input_elements:
                    #/                      o_data[i,j] = Qadd<fxp::QU`Eq[tn][0]`>(o_data[i,j],Qmul<fxp::QU`Eq[tn][0]`>(data_`Eq[tn][1]`[i,k], i_data_`Eq[tn][2]`[k,j]));
                    pass
                else:
                    #/                      o_data[i,j] = Qadd<fxp::QU`Eq[tn][0]`>(o_data[i,j],Qmul<fxp::QU`Eq[tn][0]`>(data_`Eq[tn][1]`[i,k], data_`Eq[tn][2]`[k,j]));
                    pass
            else:
                if  Eq[tn][1] in input_elements and Eq[tn][2] in input_elements:
                    #/                      data_`Eq[tn][0]`[i,j] = Qadd<fxp::QU`Eq[tn][0]`>(data_`Eq[tn][0]`[i,j],Qmul<fxp::QU`Eq[tn][0]`>(i_data_`Eq[tn][1]`[i,k], i_data_`Eq[tn][2]`[k,j]));
                    pass
                elif Eq[tn][1] in input_elements:
                    #/                      data_`Eq[tn][0]`[i,j] = Qadd<fxp::QU`Eq[tn][0]`>(data_`Eq[tn][0]`[i,j],Qmul<fxp::QU`Eq[tn][0]`>(i_data_`Eq[tn][1]`[i,k], data_`Eq[tn][2]`[k,j]));
                    pass
                elif Eq[tn][2] in input_elements:
                    #/                      data_`Eq[tn][0]`[i,j] = Qadd<fxp::QU`Eq[tn][0]`>(data_`Eq[tn][0]`[i,j],Qmul<fxp::QU`Eq[tn][0]`>(data_`Eq[tn][1]`[i,k], i_data_`Eq[tn][2]`[k,j]));
                    pass
                else:
                    #/                      data_`Eq[tn][0]`[i,j] = Qadd<fxp::QU`Eq[tn][0]`>(data_`Eq[tn][0]`[i,j],Qmul<fxp::QU`Eq[tn][0]`>(data_`Eq[tn][1]`[i,k], data_`Eq[tn][2]`[k,j]));   
                    pass         
            #/                  }
            #/              }
            #/         }

        else:
            code_all = PyTB.extract_variables_without_index(code_line[tn])
            #/         fxp::QU_`code_all[0]`  data1_`tn`_`code_all[1]`;
            #/         fxp::QU_`code_all[0]`  data2_`tn`_`code_all[2]`;
            #/         for (size_t i = 0; i < `I[tn]`; i++) {
            if tn ==1 or tn==4 or tn==8 or tn==12:
                #/              data_`code_all[0]`[i,0]=  Qmul<fxp::QU`code_all[0]`>(i_data_`code_all[1]`[i,0],data_`code_all[2]`[i,0]);
                pass    
            elif Eq[tn][0] in final_outputs:
                #/              data1_`tn`_`code_all[1]`[i,0]=data_`code_all[1]`[i,0];
                #/              data2_`tn`_`code_all[2]`[i,0]=data_`code_all[2]`[i,0];
                #/              o_data[i,0]=  Qsub<fxp::QU`code_all[0]`>(Qadd<fxp::QU`code_all[0]`>(data1_`tn`_`code_all[1]`[i,0],data2_`tn`_`code_all[2]`[i,0]),Qadd<fxp::QU`code_all[0]`>(Qmul<fxp::QU`code_all[0]`>(i_data_`code_all[3]`[0,0],data_`code_all[4]`[i,0]),Qmul<fxp::QU`code_all[0]`>(i_data_`code_all[5]`[i,0],data_`code_all[6]`[i,0])));
                pass
            else:
                #/              data1_`tn`_`code_all[1]`[i,0]=data_`code_all[1]`[i,0];
                #/              data2_`tn`_`code_all[2]`[i,0]=data_`code_all[2]`[i,0];
                #/              data_`code_all[0]`[i,0]=  Qsub<fxp::QU`code_all[0]`>(Qadd<fxp::QU`code_all[0]`>(data1_`tn`_`code_all[1]`[i,0],data2_`tn`_`code_all[2]`[i,0]),Qadd<fxp::QU`code_all[0]`>(Qmul<fxp::QU`code_all[0]`>(i_data_`code_all[3]`[0,0],data_`code_all[4]`[i,0]),Qmul<fxp::QU`code_all[0]`>(i_data_`code_all[5]`[i,0],data_`code_all[6]`[i,0])));
                pass
                
            #/         } 
###################################################################################################

    #/         for (size_t i = 0; i < `I[0]`; i++) {
    #/               for (size_t k = 0; k < `K[0]`; k++) {
    #/                  // f_i_data_1 << i_data_`Eq[0][1]`[`I[0]`-i-1,`K[0]`-k-1].toString();
    #/               }
    #/              
    #/         }
    #/         for (size_t i = 0; i < `I[0]`; i++) {
    #/               for (size_t j = 0; j < `J[0]`; j++) {
    #/                   //f_i_data_1 << data_`Eq[0][0]`[i,j].toString()<<std::endl;
    #/               }
    #/              
    #/         }
    #/         for (size_t k = 0; k < `K[0]`; k++) {
    #/               for (size_t j = 0; j < `J[0]`; j++) {
    #/                  // f_i_data_2 << i_data_`Eq[0][2]`[`K[0]`-k-1,`J[0]`-j-1].toString();
    #/               }
    #/               //f_i_data_2 << std::endl;
    #/         }
    #/         for (size_t i = 0; i < `I[len(Eq)-1]`; i++) {
    #/               for (size_t j = 0; j < `J[len(Eq)-1]`; j++) {
    #/                  // f_o_data1 << o_data[i,j].toString()<<std::endl;
    #/               }
    #/               //f_i_data_2 << std::endl;
    #/         }
    #/         for (size_t i = 0; i < `I[len(Eq)-1]`; i++) {
    #/               for (size_t j = 0; j < `J[len(Eq)-1]`; j++) {
    #/                   f_o_data << o_data[i,j].toString()<<std::endl;
    #/               }
    #/               //f_i_data_2 << std::endl;
    #/         }
    
    # T_inv= T_inv_float.astype(np.int64)
    
    for a, b in input_indices:
        if T[a].shape == (3,3):
            T_inv = np.linalg.inv(T[a])
            if b==1:
                matrix_values = {}
                for pe_address in In_A[a]:
                    i, j = pe_address
                    # print("start_time_a[1]",start_time_a[1])
                    for t in range(start_time_a[a][i,j], end_time_a[a][i,j]+1):
                        
                        vec = np.array([i, j, t], dtype=np.int64)
                        Ia= T_inv.dot(vec)
                        matrix= dependency_matrices[a][Eq[a][b]][0].dot(Ia)
                        matrix= matrix.astype(np.int64)
                        matrix_values[(i, j, t-start_time_a[a][i,j])] = matrix 
                max_t = max(t for (i,j,t) in matrix_values.keys())
                min_t = min(t for (i,j,t) in matrix_values.keys())
                sorted_keys = sorted(matrix_values.keys(), key=lambda x: (-x[0], -x[1]))
                
                for tt in range(min_t, max_t+1):
                    for (i,j,t) in sorted_keys:
                        if tt==t:
                            matrix_index= matrix_values[(i, j, t)]
                            #/      f_i_data_`Eq[a][b]` << i_data_`Eq[a][b]`[`matrix_index[0]`,`matrix_index[1]`].toString();
                    #/      f_i_data_`Eq[a][b]` <<std::endl;
            else:
                matrix_values = {}
                for pe_address in In_B[a]:
                    i, j = pe_address
                    for t in range(start_time_b[a][i,j], end_time_b[a][i,j]+1):
                        vec = np.array([i, j, t], dtype=np.int64)
                        Ia= T_inv.dot(vec)
                        matrix= dependency_matrices[a][Eq[a][b]][0].dot(Ia)
                        matrix= matrix.astype(np.int64)
                        matrix_values[(i, j, t-start_time_b[a][i,j])] = matrix 
                max_t = max(t for (i,j,t) in matrix_values.keys())
                min_t = min(t for (i,j,t) in matrix_values.keys())
                sorted_keys = sorted(matrix_values.keys(), key=lambda x: (-x[0], -x[1]))
                for tt in range(min_t, max_t+1):
                    for (i,j,t) in sorted_keys:
                        if tt==t:
                            matrix_index= matrix_values[(i, j, t)]
                            #/      f_i_data_`Eq[a][b]` << i_data_`Eq[a][b]`[`matrix_index[0]`,`matrix_index[1]`].toString();
                    #/      f_i_data_`Eq[a][b]` <<std::endl;        
        else:
            if Eq[a][b]=='a':
                #/                  f_i_data_`Eq[a][b]` <<i_data_`Eq[a][b]`[0,0].toString()<<std::endl; 
                pass
            else:           
                #/        for (size_t i = 0; i < `I[a]`; i++) {
                #/           //    for (size_t k = 0; k < `K[a]`; k++) {
                #/                  f_i_data_`Eq[a][b]` <<i_data_`Eq[a][b]`[i,0].toString()<<std::endl; //i_data_`Eq[a][b]`.toString();
                #/          //     }
                #/              
                #/        }
                pass
            pass
    #/     for (size_t i = 0; i < `I[a]-1`; i++) {f_i_data_y << i_data_y[15,0].toString()<<std::endl; }       
    #/     arma::vec tilde_x(`I[0]`, arma::fill::zeros);
    #/         for (size_t i = 0; i < `I[0]`; i++) {
    #/                  tilde_x(i)=o_data[i,0].toDouble();           
    #/         }
    #/     return tilde_x;
    #/ }
    #!
    pass
            





