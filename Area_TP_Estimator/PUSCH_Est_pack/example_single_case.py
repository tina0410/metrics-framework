#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PUSCH 信道估计器面积评估 —— 单 case 使用样例

用法::

    python example_single_case.py            # 用 param.xlsx 中 design_id=1 的用例
    python example_single_case.py 14         # 指定 design_id
    python example_single_case.py --demo     # 不读 Excel，直接用代码构造一个 case（演示 API）

输出：估算面积（um^2）；param.xlsx 的 area 列（TOP 综合真值）非空时，同时打印真值与相对误差。
"""
import argparse
import os
import sys

# PyTV 在 import 时会解析 sys.argv，先隔离再恢复
_argv = sys.argv[:]
sys.argv = [sys.argv[0]]
import numpy as np
import pandas as pd
import joblib
from PyTU import QuType, QuMode, OfMode
from top_api import (ProtocolSpec, ArchitectureConfig, ArithmeticConfig,
                     ImplementationConfig, QuantKey)
import Est_PUSCH as E
sys.argv = _argv

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(ROOT, "model")


def load_models():
    """载入基础算子的价格模型（与 main() 用的是同一套）。"""
    su_io = os.path.join(MODEL_DIR, "SU_in.xlsx")
    return (pd.read_excel(su_io, sheet_name="SU_in"),
            pd.read_excel(su_io, sheet_name="Sub"),
            joblib.load(os.path.join(MODEL_DIR, "ADD_area.pkl")),
            joblib.load(os.path.join(MODEL_DIR, "pure_MUL_area.pkl")),
            joblib.load(os.path.join(MODEL_DIR, "SU_out_FxP_area.pkl")))


def evaluate(inputs, models):
    """inputs = (protocol, architecture, quants, arithmetic, implementation)"""
    su, sub, m_add, m_mul, m_su = models
    area = E.Est_Top(m_add, sub, m_mul, m_su, su, *inputs)
    return float(np.asarray(area).ravel()[0])


def case_from_table(design_id):
    """方式 1：从 param.xlsx（测试用例表）取一行，转成评估输入。"""
    params = pd.read_excel(os.path.join(ROOT, "param.xlsx"), sheet_name="parameters")
    hit = params.loc[params["design_id"] == design_id]
    if hit.empty:
        raise SystemExit("param.xlsx has no design_id=%s" % design_id)
    row = hit.iloc[0]
    real = row.get("area", None)
    real = float(real) if isinstance(real, (int, float)) and not pd.isna(real) else None
    return E._top_inputs_from_row(row), real


def demo_case():
    """方式 2：不依赖 Excel，直接用 API 构造一个 case。"""
    protocol = ProtocolSpec(
        pusch={"num_RB_range": (134, 152), "num_symbols_range": (8, 9), "is_ECP": True},
        dmrs={"dmrs_Uplink": True, "dmrs_Type": "Hybrid", "is_double_dmrs": True,
              "is_enhanced": True, "dmrs_typeA_pos": "pos3", "additional_DMRS_range": [0, 1]},
        antenna_ports=[10, 12],
        slot_index_format=QuType(4, 0, False),
    )
    architecture = ArchitectureConfig(
        rb_parallelism=16, fi_lmmse_parallelism=16,
        freq_interp="linear", time_interp="nn", input_mode="B",
        switchable_ports=True, fi_re_parallelism=12, ti_re_parallelism=12,
        fi_lmmse_real_coeff=True, ti_lmmse_real_coeff=True,
    )
    quants = {
        QuantKey.Y: QuType(12, 4, True),
        QuantKey.H_LS: QuType(13, 4, True),
        QuantKey.H_FI: QuType(16, 6, True),
        QuantKey.H_TI: QuType(14, 2, True),
        QuantKey.FI_LMMSE_COEFF: QuType(13, 8, True),
        QuantKey.TI_LMMSE_COEFF: QuType(14, 8, True),
    }
    arithmetic = ArithmeticConfig(ls_quant_mode=QuMode.TRN.TCPL, ls_overflow_mode=OfMode.SAT.SMGN)
    implementation = ImplementationConfig(
        ti_lmmse_f_d_norm=0.03896180463861419,
        fi_lmmse_tau_rms=4.950130549230062, fi_lmmse_snr_linear=167.070466029302,
        fi_lmmse_channel_model=None, fi_lmmse_delay_spread=2.252540628915613e-07, fi_lmmse_scs=15000.0,
    )
    return (protocol, architecture, quants, arithmetic, implementation), None


def main():
    ap = argparse.ArgumentParser(description="PUSCH estimator area evaluation - single case demo")
    ap.add_argument("design_id", nargs="?", type=int, default=1, help="design_id in param.xlsx")
    ap.add_argument("--demo", action="store_true", help="build the case in code (no Excel)")
    args = ap.parse_args()

    models = load_models()
    if args.demo:
        inputs, real = demo_case()
        label = "demo (code-built case, same config as design_id=1)"
    else:
        inputs, real = case_from_table(args.design_id)
        label = "design_id=%d (from param.xlsx)" % args.design_id

    area = evaluate(inputs, models)
    print("case        : %s" % label)
    print("estimated   : %.1f um^2" % area)
    if real is not None:
        print("reference   : %.1f um^2" % real)
        print("rel. error  : %+.1f%%" % (100.0 * (area - real) / real))


if __name__ == "__main__":
    main()
