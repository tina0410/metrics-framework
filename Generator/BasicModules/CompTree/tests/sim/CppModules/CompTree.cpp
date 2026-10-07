 // module CppRunCompTree0000000001 .cpp
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
    template<typename QuType>
    double urandfill() {
        return static_cast<double>(randint(1 << (QuType::intB + QuType::fracB))-1) / (1 << QuType::fracB);
    }
 int main() {
     // verification params
     size_t N_FRAMES = 100;
     // fstreams
     std::ofstream  f_i_data("../Input_Files/CompTree_i_data.txt");
     std::ofstream  f_o_data("../Comparison_Files/CompTree_o_data.txt");
     std::ofstream f_gpos("../Comparison_Files/CompTree_o_gidx.txt");
     std::ofstream df_gpos("../Comparison_Files/gpos.txt");
     for (size_t frame = 0; frame < N_FRAMES; frame++)
     {
         fxp::QU_IN  i_data;
         int gpos_s = 0;
         //fxp::QU_OUT   o_data;
         //i_data[0]=urandfill<fxp::QU_IN_1>();
         //for(int i=1; i<31;i++){i_data[i]=i_data[0];}
         for(int i=0; i<31;i++){i_data[i]=urandfill<fxp::QU_IN_1>();}
          //i_data.fill();
         const int n_layer = std::ceil(std::log2(31));
         std::vector<int> indices(31);
         for (int i = 0; i <31; i++) {
             indices[i] = 31 - i - 1;
         }
         for (int l = 1; l < 31; l++) {
              if (i_data[gpos_s] <= i_data[l]){
                  gpos_s = l;
              }
         }
         gpos_s = indices[gpos_s];

         std::bitset<fxp::dim_P> gpos_b(gpos_s);
         fxp::QU_OUT o_data=i_data[31 - 1 - gpos_s];
         for(size_t input= 0; input<31; input++ ){f_i_data << i_data[input].toString();}
         f_i_data << std::endl;
         // f_i_data << BitStream<l2r, l2r>(i_data)<<std::endl;
         //f_i_data <<std::endl;
         f_o_data << o_data.toString()<< std::endl;
         //df_gpos << indices[0] << std::endl;
         f_gpos << gpos_b << std::endl;
     }
     return 0;
 }
