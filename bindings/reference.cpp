#include "reference.hpp"
#include "parameters.hpp"
#include "config.h"
#include <sstream>
#include <stdexcept>

std::map<std::string, std::vector<std::string>> reference_frames(int n_frames) {
    if (n_frames <= 0) {
        throw std::invalid_argument("n_frames must be a positive integer");
    }
    // Match the initial state of each legacy standalone reference process.
    QuBLAS::gen.seed(1);
    QuBLAS::UniRand.reset();
    QuBLAS::NormRand.reset();
    using namespace lsce_parameters;
    constexpr size_t STG_T = fxp::ceil_div(N_T, P_T);
    std::map<std::string, std::vector<std::string>> rows;
    for (const auto* name : {"i_Y", "i_P", "o_H", "i_ctrl_stg"}) {
        rows[name];
        rows[std::string("Decimal_") + name];
    }
    Qu<dim<P_R, N_T>, QU_Y> y;
    Qu<dim<N_T>, QU_P> p;
    Qu<dim<P_R>, QU_H> h;
    fxp::Bits<2> control;
    if constexpr (STG_T > 1) {
        for (int i = 0; i < N_PIPELINES[0] + N_PIPELINES[1]; ++i) {
            rows["i_ctrl_stg"].push_back("00");
            rows["Decimal_i_ctrl_stg"].push_back("0");
        }
    }
    for (int frame = 0; frame < n_frames; ++frame) {
        y.fill();
        p.fill();
        for (size_t stage = 0; stage < STG_T; ++stage) {
            std::ostringstream y_bits, p_bits, y_decimal, p_decimal;
            for (size_t v = P_T; v > 0; --v) {
                const size_t t = stage * P_T + v - 1;
                p_bits << p[t].toString();
                p_decimal << p[t].toDouble() << " ";
                for (size_t r = P_R; r > 0; --r) {
                    y_bits << y[r - 1, t].toString();
                    y_decimal << y[r - 1, t].toDouble() << " ";
                }
            }
            rows["i_Y"].push_back(y_bits.str());
            rows["i_P"].push_back(p_bits.str());
            rows["Decimal_i_Y"].push_back(y_decimal.str());
            rows["Decimal_i_P"].push_back(p_decimal.str());
            if constexpr (STG_T > 1) {
                control = stage == 0 ? 1 : 2;
                rows["i_ctrl_stg"].push_back(control.toString());
                rows["Decimal_i_ctrl_stg"].push_back(stage == 0 ? "1" : "2");
            }
        }
        LSCE::LSCE_ACC<N_T, P_T, P_R, QU_Y, QU_P, QU_H, QU_M_V>(y, p, h);
        std::ostringstream h_bits, h_decimal;
        for (size_t r = P_R; r > 0; --r) {
            h_bits << h[r - 1].toString();
            h_decimal << h[r - 1].toDouble() << " ";
        }
        rows["o_H"].push_back(h_bits.str());
        rows["Decimal_o_H"].push_back(h_decimal.str());
    }
    return rows;
}
