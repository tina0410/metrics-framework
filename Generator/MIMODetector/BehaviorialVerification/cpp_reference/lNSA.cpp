#include <iostream>
#include <armadillo>  
#include <cmath>
#include "PE.h"
using namespace std;
using namespace arma;

const uword   k             = 3;
const uword   Tx            = 8;
const uword   Rx            = 128;
const uword   QAM           = 16;
const uword   Qn            = 4;
const uword   lNSA_ITER     = 3;
const uword   test_num      = 3;
const uword bit_per_sym     = 2; 
constexpr double SNR = 14;
constexpr double TxE = Tx * Rx;
double const Nv      = TxE / (std::pow(10, SNR / 10) * std::log2(QAM) * Tx);
double const Nv_r    = Nv / 2;


double get_Es0(uword QAM) {
    switch (QAM) {
        case 16:   return 10;
        case 64:   return 42;
        case 256:  return 170;
        default:   throw std::invalid_argument("Invalid QAM!");
    }
}

//const vec symbols = {-7, -5, -3, -1, 1, 3, 5, 7};
const vec symbols = {-3, -1, 1, 3};
// const std::string bits_r[] = {
//     "000", "001", "011", "010", 
//     "110", "111", "101", "100"
// };
// const std::string bits_i[] = {
//     "000", "001", "011", "010",
//     "110", "111", "101", "100" 
// };
const std::string bits_r[] = {
    "00", "01", "11", "10"
};
const std::string bits_i[] = {
    "00", "01", "11", "10" 
};
arma::vec MMSE(mat A, mat tilde_H, vec tilde_y){
    return inv(A) * tilde_H.t() * tilde_y;
}

arma::vec lNSA(double a, mat D_inv, mat H, vec y){
 
    arma::vec y_MF = H.t() * y;

    arma::vec x_prev = D_inv * y_MF;
    arma::vec x_current;

    //  (i = 2 到 k)
    for (int i = 2; i <= k; ++i) {

        arma::vec b_i = H * x_prev;
        arma::vec d_i = H.t() * b_i;
        x_current = D_inv * y_MF + x_prev - (a * D_inv * x_prev + D_inv * d_i);

        x_prev = x_current;
    }

    return x_current; 
}
int main() {
    std::random_device rd;
    std::mt19937 generator(rd());
    std::uniform_int_distribution<int> dist(0, Qn-1);
    std::normal_distribution<double> normal(0.0, 1.0);
    double Es0 = get_Es0(QAM);

    arma::cx_mat H = arma::randn<arma::cx_mat>(Rx, Tx) * std::sqrt(0.5);

    cx_vec Cons(QAM);  
    for (uword i = 0; i < Qn; ++i) {
        for (uword j = 0; j < Qn; ++j) {
            Cons(i * Qn + j) = cx_double(symbols(i), symbols(j)) / std::sqrt(Es0);
        }
    }
    
    cx_vec y(Rx, fill::zeros);
    cx_vec x(Tx, arma::fill::zeros);
    std::string x_bits(Tx * bit_per_sym * 2, '0');
    std::string xhat_bits(Tx * bit_per_sym * 2, '0');
    std::string xhat_bits_lNSA(Tx * bit_per_sym * 2, '0');
    std::string xhat_bits_lNSAq(Tx * bit_per_sym * 2, '0');
    int error_MMSE=0;
    int error_lNSA=0;
    int error_lNSAq=0;
    for(uword tn=0; tn<test_num; ++tn){

        
        // 生成QAM信号
        for (uword i = 0; i < Tx; ++i) {
            int x_r_id = dist(generator); 
            int x_i_id = dist(generator); 

        
            x(i) = cx_double(symbols(x_r_id), symbols(x_i_id)) / std::sqrt(Es0);

            x_bits.replace(2* i * bit_per_sym, bit_per_sym, bits_r[x_r_id]);      
            x_bits.replace((2 * i + 1)* bit_per_sym , bit_per_sym, bits_i[x_i_id]);  
            

            for (uword r = 0; r < Rx; ++r) {
        
                y(r) = cx_double(normal(generator) * std::sqrt(Nv_r), normal(generator) * std::sqrt(Nv_r));

        
                for (uword c = 0; c < Tx; ++c) {
                    y(r) += H(r, c) * x(c);
                }
            }
        }
        
        mat tilde_H = join_vert(join_horiz(real(H), -imag(H)),join_horiz(imag(H),  real(H)));
        
        vec tilde_y = join_vert(real(y), imag(y));

        mat eye_mat = eye(2 * Tx, 2 * Tx);
        mat A = tilde_H.t() * tilde_H + (Nv / Es0) * eye_mat;

        arma::vec diag_elements = A.diag();//obtain D^-1
        if (any(diag_elements == 0)) {
            throw std::invalid_argument("矩阵对角线含有零元素，无法求逆");
        }
        arma::mat D = arma::diagmat(diag_elements);
        arma::mat inv_D = arma::diagmat(1.0 / diag_elements);

        double frobenius_sq = arma::accu(arma::square(inv_D * A));
        double frobenius_inv_sq = 1.0 / frobenius_sq;
        double lambda = Tx * frobenius_inv_sq;
        
        arma::mat invD = lambda * inv_D;
        double a = Nv / Es0;
        vec tilde_x(2*Tx, arma::fill::zeros);
        vec tilde_x_lNSAq(2*Tx, arma::fill::zeros);
        vec tilde_x_lNSA(2*Tx, arma::fill::zeros);

        tilde_x = MMSE(A, tilde_H, tilde_y);
        tilde_x_lNSA = lNSA(a, invD, tilde_H, tilde_y);
        tilde_x_lNSAq = lNSAq(a, invD, tilde_H, tilde_y,tn);

        // arma::vec Rex_lNSAq = tilde_x_lNSAq.subvec(0, Tx-1);                  
        // arma::vec Imx_lNSAq = tilde_x_lNSAq.subvec(Tx, 2*Tx-1);                
        // arma::cx_vec xhat_lNSAq = arma::cx_vec(Rex_lNSAq, Imx_lNSAq); 

        // arma::vec Rex_lNSA = tilde_x_lNSA.subvec(0, Tx-1);                  
        // arma::vec Imx_lNSA = tilde_x_lNSA.subvec(Tx, 2*Tx-1);                
        // arma::cx_vec xhat_lNSA = arma::cx_vec(Rex_lNSA, Imx_lNSA); 
        
        // arma::vec Rex = tilde_x.subvec(0, Tx-1);                  
        // arma::vec Imx = tilde_x.subvec(Tx, 2*Tx-1);                
        // arma::cx_vec xhat_MMSE = arma::cx_vec(Rex, Imx); 

        // uvec indices(Tx);
        // uvec indices_lNSA(Tx);
        // uvec indices_lNSAq(Tx);
        // for (uword i= 0; i < Tx; ++i) {
        //     // 计算与所有星座点的距离
        //     vec distances_lNSAq(QAM);
        //     for (uword k = 0; k < QAM; ++k) {
        //         distances_lNSAq(k) = norm(xhat_lNSAq(i) - Cons(k));
        //     }
        //     indices_lNSAq(i) = distances_lNSAq.index_min();
        // }
        // for (uword i= 0; i < Tx; ++i){
        //     xhat_bits_lNSAq.replace(2* i * bit_per_sym, bit_per_sym, bits_r[indices_lNSAq(i)/Qn]);      // Re
        //     xhat_bits_lNSAq.replace((2 * i + 1)* bit_per_sym , bit_per_sym, bits_i[indices_lNSAq(i)%Qn]);  // Im
        // }
        
        // for (size_t i = 0; i < x_bits.size(); ++i) {
        //     if (xhat_bits_lNSAq[i] != x_bits[i]) {
        //         error_lNSAq++;
        //     }
        // }
        // double BER_lNSAq = 1.0 * error_lNSAq / static_cast<double>(bit_per_sym * 2 * Tx)/(tn+1);

        // for (uword i= 0; i < Tx; ++i) {
        //     // 计算与所有星座点的距离
        //     vec distances_lNSA(QAM);
        //     for (uword k = 0; k < QAM; ++k) {
        //         distances_lNSA(k) = norm(xhat_lNSA(i) - Cons(k));
        //     }
        //     indices_lNSA(i) = distances_lNSA.index_min();
        // }
        // for (uword i= 0; i < Tx; ++i){
        //     xhat_bits_lNSA.replace(2* i * bit_per_sym, bit_per_sym, bits_r[indices_lNSA(i)/Qn]);      // Re
        //     xhat_bits_lNSA.replace((2 * i + 1)* bit_per_sym , bit_per_sym, bits_i[indices_lNSA(i)%Qn]);  // Im
        // }
        
        // for (size_t i = 0; i < x_bits.size(); ++i) {
        //     if (xhat_bits_lNSA[i] != x_bits[i]) {
        //         error_lNSA++;
        //     }
        // }
        // double BER_lNSA = 1.0 * error_lNSA / static_cast<double>(bit_per_sym * 2 * Tx)/(tn+1);

        // for (uword i= 0; i < Tx; ++i) {
        //     // 计算与所有星座点的距离
        //     vec distances(QAM);
        //     for (uword k = 0; k < QAM; ++k) {
        //         distances(k) = norm(xhat_MMSE(i) - Cons(k));
        //     }
        //     indices(i) = distances.index_min();
        // }
        // for (uword i= 0; i < Tx; ++i){
        //     xhat_bits.replace(2* i * bit_per_sym, bit_per_sym, bits_r[indices(i)/Qn]);      // Re
        //     xhat_bits.replace((2 * i + 1)* bit_per_sym , bit_per_sym, bits_i[indices(i)%Qn]);  // Im
        // }
        
        // for (size_t i = 0; i < x_bits.size(); ++i) {
        //     if (xhat_bits[i] != x_bits[i]) {
        //         error_MMSE++;
        //     }
        // }
        // double BER = 1.0 * error_MMSE / static_cast<double>(bit_per_sym * 2 * Tx)/(tn+1);
        // //std::cout << x << '\n';
        // //std::cout << xhat_MMSE << '\n';
        // //std::cout << "Eb/Nv = " << 10 * std::log10(Es0/Nv)<<'\n';
        // //std::cout << "D = " << std::scientific << std::log(a) / std::log(2.0) <<std::log(tilde_y.elem(arma::find(tilde_y > 0)).min()) / std::log(2.0)<<'\n';
        // std::cout << "BER = " << std::scientific << BER<<'\n';
        // std::cout << "BER_lNSA = " << std::scientific << BER_lNSA<<'\n';
        // std::cout << "BER_lNSAq = " << std::scientific << BER_lNSAq<<'\n';
    }
    return 0;
}