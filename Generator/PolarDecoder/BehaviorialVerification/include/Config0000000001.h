 // module Config0000000001 ;
 # include "QuBLAS.h"
 //# include <iostream>
 # include "math.h"
 #ifndef _USE_MATH_DEFINES
 #define _USE_MATH_DEFINES
 #endif
 #include <stdio.h>
 #include <stdlib.h>
 #include <time.h>
 #include <iostream>
 #include <cmath>
 #include <bitset>
 #include <algorithm>
 #include <vector>
 #include <random>
 #include <fstream>
 #include <iomanip>
 #include <cassert>
 using namespace std;
 #define SIGN(n) (n==0?0:(n/abs(n)))
 using namespace QuBLAS;
 template <size_t data_width, size_t frac_width>
 using fixed_t = Qu<isSigned<true>, intBits<data_width - frac_width - 1>, fracBits<frac_width> ,QuMode<RND::INF>, OfMode<SAT::SMGN>>; // WRP:TCPL // TCPL
 constexpr size_t LLR_DATA_WIDTH = 5;
 constexpr size_t LLR_FRAC_WIDTH = 1;
 constexpr size_t TEST_MODE = 1;
 using LLR_t = fixed_t<LLR_DATA_WIDTH, LLR_FRAC_WIDTH>;
 const int N = 64;
 const int K = 32;
