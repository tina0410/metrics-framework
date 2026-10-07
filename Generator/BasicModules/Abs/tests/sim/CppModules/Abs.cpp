 // module CppRunAbs0000000001 .cpp
 #include <cmath>
 #include <fstream>
 #include <QuBLAS.h>
 #include "config.h"

 int main() {
     const size_t N_FRAMES = 32;
     std::ofstream f_i_data("../Input_Files/abs_i_data.txt");
     std::ofstream f_o_data("../Comparison_Files/abs_o_data.txt");

     for (size_t frame = 0; frame < N_FRAMES; ++frame) {
         fxp::QU_IN a;
         fxp::QU_OUT o_data;

         if (frame == 0) {
             a = 0;
         }
         else if (frame == 1) {
             a = std::pow(2.0, 5) - std::pow(2.0, -3);
         }
         else if (frame == 2) {
             a = std::pow(2.0, -3);
         }
         else if (frame == 3) {
             a = std::pow(2.0, 4);
         }
         else if (frame == 4) {
             a = 0;
         }
         else {
             a.fill();
         }

         o_data = Qabs<fxp::QU_OUT>(a);
         f_i_data << a.toString() << std::endl;
         f_o_data << o_data.toString() << std::endl;
     }

     return 0;
 }
