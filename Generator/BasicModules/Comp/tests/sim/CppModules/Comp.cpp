 // module CppRunComp0000000001 .cpp
 # include<iostream>
 # include<QuBLAS.h>
 # include<utility>
 # include<fstream>
 # include<random>
 # include "config.h"
 size_t randint(size_t N) {
     std::random_device rd; // Obtain a random number from hardware
     std::mt19937 gen(rd()); // Seed the generator
     std::uniform_int_distribution<> distr(1, N); // Define the range
     return distr(gen); // Generate a random number in the range [1, N]
 }
 int main() {
     // verification params
     size_t N_FRAMES = 100;
     // fstreams
     std::ofstream  f_i_data_1("../Input_Files/Comp_i_data_1.txt");
     std::ofstream  f_i_data_2("../Input_Files/Comp_i_data_2.txt");
     std::ofstream  f_o_gidx("../Comparison_Files/Comp_o_gidx.txt");
     std::ofstream  f_o_lidx("../Comparison_Files/Comp_o_lidx.txt");
     std::ofstream  f_o_eidx("../Comparison_Files/Comp_o_eidx.txt");
     std::ofstream  f_o_gval("../Comparison_Files/Comp_o_gval.txt");
     std::ofstream  f_o_lval("../Comparison_Files/Comp_o_lval.txt");
     for (size_t frame = 0; frame < N_FRAMES; frame++)
     {
         fxp::QU_IN_1  i_data_1;
         fxp::QU_IN_2  i_data_2;
         bool o_gidx;
         bool o_lidx;
         bool o_eidx;
         fxp::GVAL   o_gval;
         fxp::LVAL   o_lval;
         i_data_1.fill();
         i_data_2.fill();
         if(i_data_1>i_data_2){
              o_gval=i_data_1;
              o_lval=i_data_2;
              o_gidx=true;
              o_lidx=false;
              o_eidx=false;
         }
         else if(i_data_1<i_data_2){
              o_gval=i_data_2;
              o_lval=i_data_1;
              o_gidx=false;
              o_lidx=true;
              o_eidx=false;
         }
         else{
              o_gval=i_data_1;
              o_lval=i_data_2;
              o_gidx=true;
              o_lidx=false;
              o_eidx=true;
         }
         // write input data to Input_Files/Mul_i_data_1.txt and Input_Files/Mul_i_data_2.txt
         f_i_data_1 << i_data_1.toString() << std::endl;
         f_i_data_2 << i_data_2.toString() << std::endl;
         // write output data to Comparison_Files/add_o_data.txt
         f_o_gidx << o_gidx << std::endl;
         f_o_lidx << o_lidx << std::endl;
         f_o_eidx << o_eidx << std::endl;
         f_o_gval << o_gval.toString() << std::endl;
         f_o_lval << o_lval.toString() << std::endl;
     }
     return 0;
 }
