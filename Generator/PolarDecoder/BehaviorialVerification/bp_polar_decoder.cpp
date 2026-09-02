# include "QuBLAS.h"
# include "Config0000000001.h"
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
#include <xmmintrin.h>
#include <immintrin.h>
#include <smmintrin.h>
#include <random>
#include <fstream>
#include <iomanip>
#include <cassert>
using namespace std;

#define SIGN(n) (n==0?0:(n/abs(n)))
using namespace QuBLAS;

// template <size_t data_width, size_t frac_width>
// using fixed_t = Qu<isSigned<true>, intBits<data_width - frac_width - 1>, fracBits<frac_width> ,QuMode<RND::INF>, OfMode<SAT::SMGN>>; // WRP:TCPL // TCPL



// constexpr size_t LLR_DATA_WIDTH = 5;
// constexpr size_t LLR_FRAC_WIDTH = 1;
// constexpr size_t TEST_MODE = 1;

// using LLR_t = fixed_t<LLR_DATA_WIDTH, LLR_FRAC_WIDTH>; 


int bit_reverse(int x, int n_bits) {
    int rev = 0;
    for (int i = 0; i < n_bits; ++i) {
        rev = (rev << 1) | (x & 1);
        x >>= 1;
    }
    return rev;
}


std::vector<int> informationbit_index(const std::vector<int>& A, int N) {
    int n_bits = static_cast<int>(std::log2(N));
    std::vector<int> reverse_map(N + 1); // 索引0不使用
    std::vector<int> reverse_map_new(N + 1); // 索引0不使用
    for (int i = 0; i < N; ++i) {
        int rev_index = bit_reverse(i, n_bits); // 0-based反转索引
        reverse_map[rev_index + 1] = i + 1;     // 1-based位置映射
        reverse_map_new[i + 1] = rev_index + 1; // 1-based反转索引映射
    }
    std::vector<int> B;
    B.reserve(A.size());
    for (int a : A) {
        B.push_back(reverse_map_new[a+1]-1);
    }
    std::sort(B.begin(), B.end());
    return B;
}

struct PhiTables {
    std::vector<double> phi_x_table;
    std::vector<double> minus_log_phi_inv_table;
    double min_x = 0.0;
    double max_x = 100.0;
    double increment_x = 0.01;
    double min_minus_log_phi = 0.0;
    double max_minus_log_phi = 100.0;
    double increment_minus_log_phi = 0.001;
};


const PhiTables& get_phi_tables() {
    static PhiTables tables = []() {
        PhiTables t;
        int size_phi_x = static_cast<int>((t.max_x - t.min_x) / t.increment_x) + 1;
        t.phi_x_table.resize(size_phi_x);
        for (int i = 0; i < size_phi_x; ++i) {
            double x = t.min_x + i * t.increment_x;
            if (x < 10.0) {
                t.phi_x_table[i] = std::exp(-0.4527 * std::pow(x, 0.86) + 0.0218);
            } else {
                t.phi_x_table[i] = std::sqrt(M_PI / x) * (1.0 - 1.4286 / x) * std::exp(-x / 4.0);
            }
        }
        int size_inv = static_cast<int>((t.max_minus_log_phi - t.min_minus_log_phi) / t.increment_minus_log_phi) + 1;
        t.minus_log_phi_inv_table.resize(size_inv, 0.0);
        double x_increment = 0.0001;
        for (double x_val = 0.0; x_val <= 400.0; x_val += x_increment) {
            double phi_val;
            if (x_val < 10.0) {
                phi_val = std::exp(-0.4527 * std::pow(x_val, 0.86) + 0.0218);
            } else {
                phi_val = std::sqrt(M_PI / x_val) * (1.0 - 1.4286 / x_val) * std::exp(-x_val / 4.0);
            }
            phi_val = std::min(phi_val, 1.0);
            double minus_log_phi = -std::log(phi_val);
            if (minus_log_phi < t.max_minus_log_phi) {
                int idx = static_cast<int>(std::ceil((minus_log_phi - t.min_minus_log_phi) / t.increment_minus_log_phi));
                if (idx >= 0 && idx < size_inv) {
                    t.minus_log_phi_inv_table[idx] = x_val;
                }
            }
        }
        return t;
    }();
    return tables;
}


double phi_x_table(double x) {
    const PhiTables& tables = get_phi_tables();
    x = std::max(tables.min_x, std::min(tables.max_x, x));
    int index = static_cast<int>(std::round((x - tables.min_x) / tables.increment_x));
    index = std::min(std::max(index, 0), static_cast<int>(tables.phi_x_table.size()) - 1);
    return tables.phi_x_table[index];
}


double phi_x_inv(double y) {
    const PhiTables& tables = get_phi_tables();
    y = std::min(std::max(y, 1e-12), 1.0); 
    double minus_log_phi = -std::log(y);
    minus_log_phi = std::max(tables.min_minus_log_phi, std::min(tables.max_minus_log_phi, minus_log_phi));
    double t_val = (minus_log_phi - tables.min_minus_log_phi) / tables.increment_minus_log_phi - 0.499;
    int index = static_cast<int>(std::round(t_val));
    index = std::min(std::max(index, 0), static_cast<int>(tables.minus_log_phi_inv_table.size()) - 1);
    //std::cout << "index: " << index << " " << tables.minus_log_phi_inv_table[index] << "  ";
    return tables.minus_log_phi_inv_table[index];
}


void construct_polar_code_GA(int N, int K, double sigma, 
                            std::vector<int>& A, 
                            std::vector<int>& Ac, 
                            std::vector<double>& channels) {

    int n = static_cast<int>(std::ceil(std::log2(N)));
    int NN = 1 << n;
    std::vector<int> bitreversedindices(N);
    for (int index = 0; index < N; ++index) {
        int rev = 0;
        for (int j = 0; j < n; ++j) {
            rev = (rev << 1) | ((index >> j) & 1);
        }
        bitreversedindices[index] = rev;
    }
    double mean_llr = 2.0 / (sigma * sigma);
    std::vector<double> channels_vec(N, mean_llr);
    for (int i = 0; i < n; ++i) {
        std::vector<double> c1, c2;
        for (int j = 0; j < channels_vec.size(); j += 2) {
            if (j < channels_vec.size()) c1.push_back(channels_vec[j]);
            if (j + 1 < channels_vec.size()) c2.push_back(channels_vec[j + 1]);
        }
        std::vector<double> set1;
        for (int j = 0; j < c1.size(); ++j) {
            double term1 = 1.0 - phi_x_table(c1[j]);
            double term2 = 1.0 - phi_x_table(c2[j]);
            double temp = 1.0 - term1 * term2;
            set1.push_back(phi_x_inv(temp));
        }
        std::vector<double> set2;
        for (int j = 0; j < c1.size(); ++j) {
            set2.push_back(c1[j] + c2[j]);
        }
        channels_vec = set1;
        channels_vec.insert(channels_vec.end(), set2.begin(), set2.end());
    }
    std::vector<double> channels_permuted(N);
    for (int i = 0; i < N; ++i) {
        channels_permuted[i] = channels_vec[bitreversedindices[i]];
    }
    std::vector<int> indices(N);
    for (int i = 0; i < N; ++i) indices[i] = i;
    std::sort(indices.begin(), indices.end(), [&](int a, int b) {
        return channels_permuted[a] > channels_permuted[b];
    });
    A = std::vector<int>(indices.begin(), indices.begin() + K);
    Ac = std::vector<int>(indices.begin() + K, indices.end());
    std::vector<int> B;
    B = informationbit_index(A, N);
    A = std::move(B);
    channels = std::move(channels_permuted);
}



/*
function sampleNormal:
@brief: This function generates a sample from the standard normal distribution using the Box-Muller method.
*/
double sampleNormal_mimo() {
    double p = ((double)rand() / (RAND_MAX)) * 2 - 1;
    double v = ((double)rand() / (RAND_MAX)) * 2 - 1;
    double r = p * p + v * v;
    if (r == 0 || r > 1) return sampleNormal_mimo();
    double c = sqrt(-2 * log(r) / r);
    return p * c;
}

/*
function g:
@brief: This function calculates the g function used in the BP polar decoder. g(s,x,y) = s * min(x,y) * sign(x) * sign(y)
*/
template <typename LLR_t>
LLR_t g(LLR_t s, LLR_t x, LLR_t y)
{
    LLR_t sign_x = x.toDouble() < 0? -1 : 1;
    LLR_t sign_y = y.toDouble() < 0? -1 : 1;
    LLR_t xy_min = (abs(x.toDouble()) < abs(y.toDouble()))? abs(x.toDouble()) :abs(y.toDouble());
    LLR_t sign = Qmul<LLR_t>(sign_x, sign_y);
    LLR_t s_min = Qmul<LLR_t>(s, xy_min);
    LLR_t res= Qmul<LLR_t>(s_min, sign);
    return res;
}


/*
function PolarEncode_xor:
@brief: This function performs the polar encoding of the input data using XOR operations
@param: uout = output data, int array of length len
@param: uin = input data, int array of length len
@param: len = polar code length
*/
void PolarEncode_xor(int* uout, int* uin, int len) {
    if (len == 1) {
        return;
    } else if (len == 2) {
        uout[0] = uin[0] ^ uin[1];
        uout[1] = uin[1];
    } else if (len == 4) {
        uout[1] = uin[1] ^ uin[3];
        uout[2] = uin[2] ^ uin[3];
        uout[3] = uin[3];
        uout[0] = uin[0] ^ uin[1] ^ uout[2];
    } else {
        // First stage: process pairs
        for (int i = 0; i < len; i += 2) {
            uout[i] = uin[i] ^ uin[i + 1];
            uout[i + 1] = uin[i + 1];
        }
        
        // Second stage: process groups of 4
        for (int i = 0; i < len; i += 4) {
            for (int k = 0; k < 2; k++) {
                uout[i + k] ^= uout[i + k + 2];
            }
        }
        
        // Process larger blocks (8, 16, 32, ...)
        int block_size = 8;
        while (block_size <= len) {
            int half_block = block_size / 2;
            for (int i = 0; i < len; i += block_size) {
                for (int j = 0; j < half_block; j++) {
                    uout[i + j] ^= uout[i + j + half_block];
                }
            }
            block_size <<= 1;  // Double block size
        }
    }
}


/*
function Gn:
@brief: This function constructs the generator matrix G 
@param in: n = log2(N), where N is the code length
@param out: G = generator matrix, N x N array
*/
void Gn(int n, int** G) {
    int N = 1 << n; // Calculate N = 2^n
    
    // Initialize for n=0 (1x1 matrix)
    G[0][0] = 1;
    
    // Iteratively build the matrix for n>0
    for (int k = 0; k < n; ++k) {
        int current_size = 1 << k; // Size of current block matrix (2^k)
        int next_size = current_size << 1; // Size after Kronecker product (2^{k+1})
        
        // Construct next matrix using Kronecker product with F
        for (int i = 0; i < current_size; ++i) {
            for (int j = 0; j < current_size; ++j) {
                // Top-right block: 0 * current_block
                G[i][j + current_size] = 0;
                
                // Bottom-left block: 1 * current_block
                G[i + current_size][j] = G[i][j];
                
                // Bottom-right block: 1 * current_block
                G[i + current_size][j + current_size] = G[i][j];
            }
        }
    }
}

double phi(double t)
{
	if (t < 0.867861)
		return std::exp(0.0564 * t * t - 0.48560 * t);
	else // if(t >= phi_pivot)
		return std::exp(-0.4527 * std::pow(t, 0.8600) + 0.0218);
}


double phi_inv(double t)
{
	if (t > 0.6845772418)
		return 4.304964539 * (1 - sqrt(1 + 0.9567131408 * std::log(t)));
	else
		return std::pow(-2.208968 * std::log(t) + 0.0482, 1.1628);
}

/*
function GA_codeconstruction:
@brief: This function implements GA (Gaussian Approximation) polar code construction.
@param in: CodeLength = code length
@param_in: sigma = standard deviation of the Gaussian noise
*/
void GA_codeconstruction(int CodeLength, float sigma, vector<int>& best_channel)
{
	int m = (int)(log(CodeLength)/log(2));
	std::vector<float> z(CodeLength, 0);
	const float alpha = -0.4527;
	const float beta = 0.0218;
	const float gamma = 0.8600;
	const float bisection_max = std::numeric_limits<float>::max();
	const float epsilon = 0.00000000001;

	for (unsigned i = 0; i < CodeLength; i++)
		best_channel[i] = i;

	//for (auto i = 0; i < std::exp2(m); i++)
	for (auto i = 0; i < pow(2.0,m); i++)
		z[i] = 2.0 / std::pow((float)sigma, 2.0);

	for (auto l = 1; l <= m; l++)
	{
		//auto o1 = (int)std::exp2(m - l + 1);
		//auto o2 = (int)std::exp2(m - l);
		auto o1 = (int)pow(2.0,m - l + 1);
		auto o2 = (int)pow(2.0,m - l);
		//for (auto t = 0; t < (int)std::exp2(l - 1); t++)
		for (auto t = 0; t < (int)pow(2.0,l - 1); t++)
		{
			float T = z[t * o1];

			z[t * o1] = phi_inv(1.0 - std::pow(1.0 - phi(T), 2.0));
			if (z[t * o1] == HUGE_VAL)
				z[t * o1] = T + M_LN2 / (alpha * gamma);

			z[t * o1 + o2] = 2.0 * T;
		}
	}
	std::sort(best_channel.begin(), best_channel.end(), [&](int i1, int i2) { return z[i1] > z[i2]; });
}


/*
function bp_polar_decoder_MS:
@brief: This function implements the BP polar decoder using MS (min-sum) algorithm.
@param in: y received llr values (log(p0/p(1)))
@param in: A information and frozen bit set, 1 x N array; 0-frozen bit, 1-information bit
@param in: t BP iteration number
@param in: N code length
@param in: s scaling factor (to 1 for MS, to 0.9375 for NMS(SMS))
@param in: sigma_sq noise variance
@param out: u_out decoded bits, 1 x N array
*/
template <typename LLR_t> 
void bp_polar_decoder_MS (float* llr_in, int* A, int* u_out, float sigma_sq, float s, int t, int N, int MAX)
{
    // std::cout << "a_test=" << a_test.toDouble() << " b_test=" << b_test.toDouble() << " c_test=" << c_test.toDouble() << std::endl;
    std::ofstream test_log("log.txt");
    // for (int i=0; i<N; i++) {if(llr_in[i]>7.50) llr_in[i]=7.50; if(llr_in[i]<-7.50) llr_in[i]=-7.50;}
    // Initialize 
    int n = log2(N);
    int N_half = N/2;
    LLR_t s_quant = s;
    LLR_t* llr_quant = new LLR_t[N];
    for (int i = 0; i < N; i++) { llr_quant[i] = llr_in[i]; }
    LLR_t* llr_pre = new LLR_t[N];
    for (int i = 0; i < N; i++) { llr_pre[i] = 0.0; }
    LLR_t** L = new LLR_t*[n+1];  // message from right to left
    for (int i = 0; i < n+1; i++) { L[i] = new LLR_t[N]; }
    for (int i = 0; i < n+1; i++) { for (int j = 0; j < N; j++) { L[i][j] = 0.0; } }
    LLR_t** R = new LLR_t*[n];   // message from left to right
    for (int i = 0; i < n; i++) { R[i] = new LLR_t[N]; }
    for (int i = 0; i < n; i++) { for (int j = 0; j < N; j++) { R[i][j] = 0.0; } }
    int* index = new int[N_half];
    for (int i = 0; i < N_half; i++) { index[i] = i+1; }  // index = 1:N/2
    int* index3 = new int[N_half];
    int* index4 = new int[N_half];
    int* index1 = new int[N_half];
    int* index2 = new int[N_half];
    //int MAX = pow(2,LLR_DATA_WIDTH);
    for (int i = 0; i < N_half; i++) { index3[i] = index[i]; index4[i] = index[i]+N_half; index1[i] = 2*index[i]-1; index2[i] = 2*index[i]; }
    // Initialize L and R
    for (int i = 0; i < N; i++) { L[n][i] = llr_quant[i]; }
    for (int i=0; i<N; i++){
        if (A[i] == 1) {
            R[0][i] = 0;  // info bit 
        }
        else {
            R[0][i] = MAX;  // frozen bit // 7.50
        }
    }
    // Iterative BP decoding
    for (int k=0; k<t; k++)
    {
        // from left to right.
        for (int i=0; i<n-1; i++)
        {
             for (int j=0; j<N_half; j++)
             {
                LLR_t llr_sum_quant = R[i][index4[j]-1] + L[i+1][index2[j]-1];
                R[i+1][index1[j]-1] = g(s_quant, R[i][index3[j]-1], llr_sum_quant);
                R[i+1][index2[j]-1] = g(s_quant, R[i][index3[j]-1],L[i+1][index1[j]-1]) + R[i][index4[j]-1];

             }
        }
        // from right to left
        for (int i=(n-1); i>0; i--)
        {
             for (int j=0; j<N_half; j++)
             {
                LLR_t llr_sum_quant = L[i+1][index2[j]-1] + R[i][index4[j]-1];
                L[i][index3[j]-1] = g(s_quant, L[i+1][index1[j]-1], llr_sum_quant);
                L[i][index4[j]-1] = g(s_quant, L[i+1][index1[j]-1], R[i][index3[j]-1]) + L[i+1][index2[j]-1];
             }
        }
        // Early Termination
        bool b_same = 1;
        for (int i=0; i<N; i++)
        {
            int sign_llr_pre = (llr_pre[i].toDouble() < 0 )? -1 : 1;
            int sign_L = (L[1][i].toDouble() < 0 )? -1 : 1;
            if (sign_llr_pre != sign_L)
            {
                b_same = 0;
                break;
            }
        }
        if (b_same)
        { 
            break;
        }
        else
        {
            for (int i=0; i<N; i++){ llr_pre[i] = L[1][i];}
        }
    }
    // decision
    for (int j=0; j<N_half; j++){
        int i=0;
        LLR_t llr_sum_quant = L[i+1][index2[j]-1] + R[i][index4[j]-1];
        L[i][index3[j]-1] = g(s_quant, L[i+1][index1[j]-1], llr_sum_quant);
        L[i][index4[j]-1] = g(s_quant, L[i+1][index1[j]-1], R[i][index3[j]-1]) + L[i+1][index2[j]-1];
    }
    for (int i=0; i<N; i++)
    {
        LLR_t llr_dec_quant = L[0][i] + R[0][i];
        float llr_dec = llr_dec_quant.toDouble();
        u_out[i] = ((llr_dec > 0)|(llr_dec==0)) ? 0 : 1;
    }

    // free memory
    delete[] llr_quant;
    delete[] llr_pre;
    for (int i = 0; i < n+1; i++) { delete[] L[i]; }
    for (int i = 0; i < n; i++) { delete[] R[i]; }
    delete[] L;
    delete[] R;
    delete[] index;
    delete[] index3;
    delete[] index4;
    delete[] index1;
    delete[] index2;
}



/*
function bp_polar_decoder_MS_standard:
@brief: This function implements the BP polar decoder using MS (min-sum) algorithm.
@param in: y received llr values (log(p0/p(1)))
@param in: A information and frozen bit set, 1 x N array; 0-frozen bit, 1-information bit
@param in: t BP iteration number
@param in: N code length
@param in: s scaling factor (to 1 for MS, to 0.9375 for NMS(SMS))
@param in: sigma_sq noise variance (currently not used)
@param in: MAX maximum of llr for the current quantization mode, used to clip llr_in and intialize R message
@param out: u_out decoded bits, 1 x N array
*/
template <typename LLR_t> 
void bp_polar_decoder_MS_standard (LLR_t* llr_in, int* A, int* u_out, LLR_t s, int t, int N, int MAX, int* iter_out = nullptr)
{
    int n = log2(N);
    int N_half = N/2;
    LLR_t s_quant = s;
    LLR_t* llr_quant = new LLR_t[N];
    for (int i = 0; i < N; i++) { llr_quant[i] = llr_in[i]; }
    LLR_t* llr_pre = new LLR_t[N];
    for (int i = 0; i < N; i++) { llr_pre[i] = 0.0; }
    LLR_t** L = new LLR_t*[n+1];  // message from right to left
    for (int i = 0; i < n+1; i++) { L[i] = new LLR_t[N]; }
    for (int i = 0; i < n+1; i++) { for (int j = 0; j < N; j++) { L[i][j] = 0.0; } }
    LLR_t** R = new LLR_t*[n];   // message from left to right
    for (int i = 0; i < n; i++) { R[i] = new LLR_t[N]; }
    for (int i = 0; i < n; i++) { for (int j = 0; j < N; j++) { R[i][j] = 0.0; } }
    int* index = new int[N_half];
    for (int i = 0; i < N_half; i++) { index[i] = i+1; }  // index = 1:N/2
    int* index3 = new int[N_half];
    int* index4 = new int[N_half];
    int* index1 = new int[N_half];
    int* index2 = new int[N_half];
    //int MAX = pow(2,LLR_DATA_WIDTH);
    for (int i = 0; i < N_half; i++) { index3[i] = index[i]; index4[i] = index[i]+N_half; index1[i] = 2*index[i]-1; index2[i] = 2*index[i]; }
    // Initialize L and R
    for (int i = 0; i < N; i++) { L[n][i] = llr_quant[i]; }
    for (int i=0; i<N; i++){
        if (A[i] == 1) {
            R[0][i] = 0;  // info bit 
        }
        else {
            R[0][i] = MAX;  // frozen bit // 7.50
        }
    }
    // Iterative BP decoding
    int iter_used = 0;
    for (int k=0; k<t; k++)
    {
        iter_used = k + 1;
        // from left to right.
        for (int i=0; i<n-1; i++)
        {
             for (int j=0; j<N_half; j++)
             {
                LLR_t llr_sum_quant = Qadd<LLR_t>(R[i][index4[j]-1],L[i+1][index2[j]-1]);
                R[i+1][index1[j]-1] = g(s_quant, R[i][index3[j]-1], llr_sum_quant);
                R[i+1][index2[j]-1] = Qadd<LLR_t>(g(s_quant, R[i][index3[j]-1],L[i+1][index1[j]-1]) , R[i][index4[j]-1]);

             }
        }
        // from right to left
        for (int i=(n-1); i>0; i--)
        {
             for (int j=0; j<N_half; j++)
             {
                LLR_t llr_sum_quant = Qadd<LLR_t>(L[i+1][index2[j]-1],R[i][index4[j]-1]);
                L[i][index3[j]-1] = g(s_quant, L[i+1][index1[j]-1], llr_sum_quant);
                L[i][index4[j]-1] = Qadd<LLR_t>(g(s_quant, L[i+1][index1[j]-1], R[i][index3[j]-1]) , L[i+1][index2[j]-1]);
             }
        }
        // Early Termination
        bool b_same = 1;
        for (int i=0; i<N; i++)
        {
            int sign_llr_pre = (llr_pre[i].toDouble() < 0 )? -1 : 1;
            int sign_L = (L[1][i].toDouble() < 0 )? -1 : 1;
            if (sign_llr_pre != sign_L)
            {
                b_same = 0;
                break;
            }
        }
        if (b_same)
        { 
            break;
        }
        else
        {
            for (int i=0; i<N; i++){ llr_pre[i] = L[1][i];}
        }
    }
    if (iter_out != nullptr) {
        *iter_out = iter_used;
    }
    // decision
    for (int j=0; j<N_half; j++){
        int i=0;
        LLR_t llr_sum_quant = Qadd<LLR_t>(L[i+1][index2[j]-1] ,R[i][index4[j]-1]);
        L[i][index3[j]-1] = g(s_quant, L[i+1][index1[j]-1], llr_sum_quant);
        L[i][index4[j]-1] = Qadd<LLR_t>(g(s_quant, L[i+1][index1[j]-1], R[i][index3[j]-1]) , L[i+1][index2[j]-1]);
    }
    for (int i=0; i<N; i++)
    {
        LLR_t llr_dec_quant = Qadd<LLR_t>(L[0][i] ,R[0][i]);
        float llr_dec = llr_dec_quant.toDouble();
        u_out[i] = ((llr_dec > 0)|(llr_dec==0)) ? 0 : 1;
    }

    // free memory
    delete[] llr_quant;
    delete[] llr_pre;
    for (int i = 0; i < n+1; i++) { delete[] L[i]; }
    for (int i = 0; i < n; i++) { delete[] R[i]; }
    delete[] L;
    delete[] R;
    delete[] index;
    delete[] index3;
    delete[] index4;
    delete[] index1;
    delete[] index2;
}


// function y=route(x)
// len = length(x) / 2;
// y = zeros(1,2*len);
// for i = 1:len
//     y(2*i-1) = x(i); 
//     y(2*i) = x(i+len); 
// end
// end

void route(int* x, int* y, int length)
{
    int len = round(length / 2);
    for (int i = 1; i < len+1; i++) {
        y[2*i-2] = x[i-1];
        y[2*i-1] = x[i+len-1];
    }
}



int main(int argc, char* argv[]){
    // int N = 1024;
    // int K = 512;
    const std:: string run_mode = "VAL";
    float code_rate = (float)K/(float)N;
    float EbN0_run = argc > 1 ? std::stof(argv[1]) : 10.0f;
    float EbN0_min = EbN0_run;
    float EbN0_max = EbN0_run;
    float EbN0_step = 0.5;
    float EbN0_design = 2.0; // EbN0 for polar code construction
    float s = 0.9375;
    float t = 15;
    int n_err_frames = 1; 
    int max_frames = 1;
    std::random_device rd;              // 获取随机数种子
	std::mt19937 gen(rd());             // 使用种子初始化mt19937生成器
	std::uniform_int_distribution<> distrib(1, 1000000);
    int fer_len = (int)(EbN0_max-EbN0_min)/EbN0_step+1;
    float* FER = new float[fer_len];
    for (int i = 0; i < fer_len; i++) { FER[i] = 0.0;}
    float* y_file_in = new float[N];
    int* A_Ac = new int[N];
    int* A = new int[K];
    int* Ac = new int[N-K];
    int* u_hat_matlab = new int[N];
    int* matlab_construction = new int[N];
    int* u_route_matlab = new int[N];
    // Only 'y_test_full_1.txt' and 'uhat_test_full_1.txt' are used for validation, other files are useless.r
    std::string file_name_base = string("N") + to_string(N) + string("K")+ to_string(K) + string("INTDWT") + to_string(LLR_DATA_WIDTH-LLR_FRAC_WIDTH-1) + 
    string("FRACDWT")+to_string(LLR_FRAC_WIDTH)+string("MS.txt");
    std::ifstream construction_file("");
    std::ifstream y_file_matlab(string("./input_files/y1")+file_name_base); // y = (1-2x)+n, where n is AWGN, from matlab
    std::ifstream u_hat_file_matlab(string("./input_files/u1_esti")+file_name_base);  // decoding result from matlab
    std::ifstream u_route_file_matlab(string("./input_files/u2")+file_name_base);
    std::ofstream uhat_log("./comparison_files/uhat_log.txt");
    std::ofstream my_construction_log("./comparison_files/my_construction_log.txt");
    std::ofstream u_route_log("./comparison_files/u_route_log.txt");
    std::ofstream iter_frame_log("./comparison_files/iter_frame_log.txt");
    for (int i=0; i<N; i++) {u_route_file_matlab >> u_route_matlab[i];}
    float tmp_design = pow(10, EbN0_design / 10);
    float sigma_sq_design = (float)1 / (float)tmp_design / 2 / code_rate;
    // polar code construction
    std::vector<int>A_vec, Ac_vec, A_Ac_vec;
    A_vec.resize(K); Ac_vec.resize(N-K); A_Ac_vec.resize(N);
    std::vector<double> channels_vec;
    channels_vec.resize(N);
    for (int i = 0; i < N; i++) {A_Ac_vec[i]=0;}
    construct_polar_code_GA(N, K, (float)sqrt(sigma_sq_design), A_vec, Ac_vec, channels_vec);
    for (int i = 0; i < K; i++) {A_Ac_vec[A_vec[i]]=1;}
    for (int i = 0; i < N; i++) { A_Ac[i] = A_Ac_vec[i]; }
    int k_bit = 0;
    for (int i = 0; i < N; i++){
        if (A_Ac[i] == 1) {A[k_bit]=i; k_bit++;}
    }
    // simulation begins
    for (int i_snr=0 ; i_snr<fer_len; i_snr++)
    {
        float nowEbN0 = EbN0_min + i_snr*EbN0_step;
        float tmp = pow(10, nowEbN0 / 10);
		float sigma_sq = (float)1 / (float)tmp / 2 / code_rate;
        int n_err_frame = 0;
        int i_frame = 0;
        for (i_frame=0; i_frame<max_frames; i_frame++){
            if (n_err_frame >= n_err_frames) { break; }
            int* u_in = new int[N];
            int* u_encoded = new int[N];
            int* decoded_bits = new int[N];
            int* decoded_bits_route = new int[N];
            float* llr_in = new float[N];
            float* y = new float[N];
            LLR_t* llr_quant_in = new LLR_t[N];
            LLR_t s_quant = s;
            for (int i = 0; i < N; i++){u_in[i]=0; u_encoded[i]=0;llr_in[i]=0.0;y[i]=0.0;decoded_bits[i]=0;}
            unsigned char* a_data = new unsigned char[K];
            for (int i = 0; i < K; i++){a_data[i] = 0;/*(unsigned char)(distrib(gen) % 2);*/}//(unsigned char)(distrib(gen) % 2);}
            for (int i = 0; i < K; i++){u_in[A[i]] = a_data[i];}
            // Setting a_data and u_in is useless here because we only read y from matlab file and decodes based on y, then compare with u_hat_matlab.
            PolarEncode_xor(u_encoded, u_in, N);
            for (int i = 0; i < N; i++){
                y_file_matlab >> y[i]; // y_file_matlab >> sigma_sq;
                u_hat_file_matlab >> u_hat_matlab[i];
                y[i]=-y[i];
                //std::cout << y[i] << endl;
            }
            for (int i=0; i<N; i++){
                llr_in[i] = 2*y[i]/(sigma_sq);
                llr_quant_in[i] = llr_in[i];
                // std::cout << llr_quant_in[i].toDouble() << endl;
            }
            int max = pow(2,LLR_DATA_WIDTH);
            int iter_frame = 0;
            bp_polar_decoder_MS_standard<LLR_t>(llr_quant_in, A_Ac, decoded_bits, s_quant, t, N, max, &iter_frame);
            iter_frame_log << iter_frame << std::endl;
            route(decoded_bits, decoded_bits_route, N);
            // write decoded_bits_route
            for (int i = 0; i < N; i++){
                u_route_log << decoded_bits_route[i] << std::endl;
            }
            for (int i = 0; i < K; i++){if (decoded_bits[A[i]] != u_hat_matlab[A[i]]){n_err_frame++;  break;}}
            for (int i = 0; i < N; i++){if (decoded_bits_route[i] != u_route_matlab[i]){n_err_frame++; break;}}
            for (int i = 0; i < N; i++){
                uhat_log << u_hat_matlab[i] << " " << decoded_bits[i] << std::endl;
            }
            // if (i_frame%100 == 0) {
            //     std::cout << "EbN0: " << nowEbN0 << " frame: " << i_frame+1 << " n_err_frame: " << n_err_frame << std::endl;
            // }
            delete[] u_in;
            delete[] u_encoded;
            delete[] decoded_bits;
            delete[] llr_in;
            delete[] y;
            delete[] a_data;
            delete[] decoded_bits_route;
        }
        FER[i_snr] = (float)n_err_frame/(float)i_frame;
    }
    // for (int i = 0; i < fer_len; i++) { std::cout << "EbN0:"<< EbN0_min + i*EbN0_step << " FER: " << FER[i] << std::endl; }
    delete[] FER;
    delete[] A;
    delete[] A_Ac;
    delete[] y_file_in;
    delete[] u_hat_matlab;
    delete[] Ac;
    delete[] matlab_construction;
    delete[] u_route_matlab;
    return 0;
}
