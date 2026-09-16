 // module CppRun0000000001 .cpp
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
     size_t N_FRAMES = 8;
     // fstreams
     std::ofstream  f_i_data_1("../Input_Files/Mul_i_data_1.txt");
     std::ofstream  f_i_data_2("../Input_Files/Mul_i_data_2.txt");
     std::ofstream  f_o_data("../Comparison_Files/Mul_o_data.txt");
     for (size_t frame = 0; frame < N_FRAMES; frame++)
     {
         fxp::QU_IN_1  i_data_1;
         fxp::QU_IN_2  i_data_2;
         fxp::QU_OUT   o_data;
         i_data_1.fill();
         i_data_2.fill();
         o_data = Qmul<fxp::QU_OUT>(i_data_1, i_data_2);
         // write input data to Input_Files/Mul_i_data_1.txt and Input_Files/Mul_i_data_2.txt
         f_i_data_1 << i_data_1.toString() << std::endl;
         f_i_data_2 << i_data_2.toString() << std::endl;
         // write output data to Comparison_Files/add_o_data.txt
         f_o_data << o_data.toString() << std::endl;
     }
     return 0;
 }
