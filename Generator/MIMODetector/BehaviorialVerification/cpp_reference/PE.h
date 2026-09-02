#ifndef PE_H  
#define PE_H
#include <armadillo>

using namespace arma;

arma::vec lNSAq(double a, mat D, mat H, vec y,uword test_num);
#endif