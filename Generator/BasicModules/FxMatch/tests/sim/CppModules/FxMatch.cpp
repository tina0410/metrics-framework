 // module FxMatchCppRun0000000001 .cpp
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
     // fstreams
     std::ofstream  f_i_data("../Input_Files/fxmatch_i_data.txt");
     std::ofstream  f_o_data("../Comparison_Files/fxmatch_o_data.txt");
     for (size_t frame = 0; frame < 100; frame++)
     {
         if(frame<95){
              fxp::QU_IN  i_data;
              i_data.fill();
              fxp::QU_OUT o_data = i_data;
              // std::cout << "i_data:   " <<   i_data.toString() << endl;
              // std::cout << "o_data:  " <<   o_data.toString() << endl;
              // write input data to Input_Files/fxm_i_data.txt
              f_i_data << i_data.toString() << std::endl;
              // write output data to Comparison_Files/fxm_o_data.txt
              f_o_data << o_data.toString() << std::endl;
         }
         if(frame==95){
              fxp::QU_IN  i_data;
              i_data = pow(2, -9-1);
              fxp::QU_OUT o_data = i_data;
              // std::cout << "i_data:   " <<   i_data.toString() << endl;
              // std::cout << "o_data:  " <<   o_data.toString() << endl;
              // write input data to Input_Files/fxm_i_data.txt
              f_i_data << i_data.toString() << std::endl;
              // write output data to Comparison_Files/fxm_o_data.txt
              f_o_data << o_data.toString() << std::endl;
         }
         if(frame==96){
              fxp::QU_IN  i_data;
              i_data = pow(2, 5-9-1)-pow(2, -9);
              fxp::QU_OUT o_data = i_data;
              // std::cout << "i_data:   " <<   i_data.toString() << endl;
              // std::cout << "o_data:  " <<   o_data.toString() << endl;
              // write input data to Input_Files/fxm_i_data.txt
              f_i_data << i_data.toString() << std::endl;
              // write output data to Comparison_Files/fxm_o_data.txt
              f_o_data << o_data.toString() << std::endl;
         }
         if(frame==97){
              fxp::QU_IN  i_data;
              i_data = pow(2, -9);
              fxp::QU_OUT o_data = i_data;
              // std::cout << "i_data:   " <<   i_data.toString() << endl;
              // std::cout << "o_data:  " <<   o_data.toString() << endl;
              // write input data to Input_Files/fxm_i_data.txt
              f_i_data << i_data.toString() << std::endl;
              // write output data to Comparison_Files/fxm_o_data.txt
              f_o_data << o_data.toString() << std::endl;
         }
         if(frame==98){
              fxp::QU_IN  i_data;
              i_data = pow(2, 5-9)-pow(2, -9);
              fxp::QU_OUT o_data = i_data;
              // std::cout << "i_data:   " <<   i_data.toString() << endl;
              // std::cout << "o_data:  " <<   o_data.toString() << endl;
              // write input data to Input_Files/fxm_i_data.txt
              f_i_data << i_data.toString() << std::endl;
              // write output data to Comparison_Files/fxm_o_data.txt
              f_o_data << o_data.toString() << std::endl;
         }
         if(frame==99){
              fxp::QU_IN  i_data;
              i_data = pow(2, 5-9-1);
              fxp::QU_OUT o_data = i_data;
              // std::cout << "i_data:   " <<   i_data.toString() << endl;
              // std::cout << "o_data:  " <<   o_data.toString() << endl;
              // write input data to Input_Files/fxm_i_data.txt
              f_i_data << i_data.toString() << std::endl;
              // write output data to Comparison_Files/fxm_o_data.txt
              f_o_data << o_data.toString() << std::endl;
         }
     }
 }
