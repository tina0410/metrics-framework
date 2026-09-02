#!/usr/bin/env python3
"""
PredIter.py — 读取 results.xlsx，以前三列为自变量（Eb/N0, N, code_rate），
最后一列 Iter 为因变量，训练机器学习模型，保存到 .pkl，并提供预测函数。

模型: 物理特征 + PolynomialFeatures + RidgeCV。
      训练数据覆盖 EbN0 2-12 dB，模型在范围内准确。

指标：MAPE, RRSE, R (Pearson)
"""

import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

warnings.filterwarnings("ignore")

# ── 全局常量 ──────────────────────────────────────────────
DATA_FILE    = Path(__file__).parent / "results.xlsx"
MODEL_FILE   = Path(__file__).parent / "pred_iter_model.pkl"
RAW_FEATURES = ["Eb/N0 (dB)", "码长 N", "码率 R"]
TARGET_NAME  = "Iter"
RANDOM_SEED  = 42


# ================================================================
#  特征工程
# ================================================================

def build_features(raw: np.ndarray) -> np.ndarray:
    """
    物理特征。EbN0 依赖通过 1/(EbN0+offset) 保证外推单调性。
    """
    ebn0  = raw[:, 0]
    N     = raw[:, 1]
    rate  = raw[:, 2]

    inv_shifted = 1.0 / (ebn0 + 1.0)          # 1/(EbN0+1)
    log2_N      = np.log2(N)
    inv_sq      = inv_shifted ** 2
    log2N_x_inv = log2_N * inv_shifted
    rate_x_inv  = rate * inv_shifted

    return np.column_stack([inv_shifted, log2_N, rate, inv_sq, log2N_x_inv, rate_x_inv])


FEATURE_NAMES = ["inv_shifted", "log2_N", "rate", "inv_sq", "log2N_x_inv", "rate_x_inv"]


def _raw_to_feat(ebn0_db, N, code_rate):
    return build_features(np.array([[ebn0_db, N, code_rate]], dtype=np.float64))


# ================================================================
#  指标
# ================================================================

def _rrse(y_true, y_pred):
    return float(np.sqrt(np.sum((y_true-y_pred)**2) / np.sum((y_true-np.mean(y_true))**2)))

def _r_score(y_true, y_pred):
    return float(np.corrcoef(y_true, y_pred)[0, 1])

def _mape(y_true, y_pred):
    return float(mean_absolute_percentage_error(y_true, y_pred))

def evaluate(y_true, y_pred):
    return {"MAPE": _mape(y_true, y_pred), "RRSE": _rrse(y_true, y_pred), "R": _r_score(y_true, y_pred)}


# ================================================================
#  训练 & 保存
# ================================================================

def train(data_path=DATA_FILE, model_path=MODEL_FILE):
    df = pd.read_excel(data_path)
    X_raw = df[RAW_FEATURES].values.astype(np.float64)
    y = df[TARGET_NAME].values.astype(np.float64)
    X = build_features(X_raw)

    print(f"数据: {X.shape[0]} 行, EbN0={X_raw[:,0].min():.0f}~{X_raw[:,0].max():.0f} dB")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED)

    # deg=2 保证外推不过度振荡 (deg=3 在外推区不可靠)
    poly = PolynomialFeatures(degree=2, include_bias=True)
    X_train_poly = poly.fit_transform(X_train)
    X_test_poly = poly.transform(X_test)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train_poly)
    X_test_s = scaler.transform(X_test_poly)

    # RidgeCV 自动选 alpha
    model = RidgeCV(alphas=np.logspace(-3, 3, 13), cv=5, scoring="r2")
    model.fit(X_train_s, y_train)

    y_pred_test = model.predict(X_test_s)
    m = evaluate(y_test, y_pred_test)
    cv = cross_val_score(model, X_train_s, y_train, cv=5, scoring="r2")
    m["CV_R2_mean"] = float(np.mean(cv))
    m["CV_R2_std"] = float(np.std(cv))
    m["alpha"] = float(model.alpha_)
    m["n_features"] = X_train_poly.shape[1]

    print(f"  特征数: {m['n_features']}  alpha: {m['alpha']:.4f}")
    print(f"  测试集 MAPE: {m['MAPE']*100:.2f}%  R: {m['R']:.4f}  CV_R2: {m['CV_R2_mean']:.4f}")

    bundle = {
        "model": model, "poly": poly, "scaler": scaler,
        "feature_names": FEATURE_NAMES, "raw_features": RAW_FEATURES,
        "target_name": TARGET_NAME, "best_model": "Ridge",
        "metrics": m,
    }
    with open(model_path, "wb") as f:
        pickle.dump(bundle, f)
    print(f"  → {model_path}")
    return m


# ================================================================
#  预测
# ================================================================

def predict_iter(ebn0_db, N, code_rate, model_path=MODEL_FILE):
    with open(model_path, "rb") as f:
        b = pickle.load(f)
    X = _raw_to_feat(ebn0_db, N, code_rate)
    return float(np.clip(b["model"].predict(b["scaler"].transform(b["poly"].transform(X)))[0], 1.0, 15.0))


def predict_batch(inputs, model_path=MODEL_FILE):
    with open(model_path, "rb") as f:
        b = pickle.load(f)
    X = build_features(np.array(inputs, dtype=np.float64))
    return np.clip(b["model"].predict(b["scaler"].transform(b["poly"].transform(X))), 1.0, 15.0)


# ================================================================
#  main
# ================================================================

if __name__ == "__main__":
    # metrics = train()

    # ================================================================
    #  单 case 预测示例
    # ================================================================
    # print("\n" + "=" * 60)
    # print("  单 Case 预测")
    # print("=" * 60)

    # ---- 修改这三个参数即可预测任意点 ----
    ebn0  = 12.0       # Eb/N0 (dB)
    N     = 256       # 码长
    rate  = 2.0 / 3.0  # 码率
    # ------------------------------------

    pred = predict_iter(ebn0, N, rate)
    print(f"  Eb/N0 = {ebn0} dB")
    print(f"  码长 N = {N}")
    print(f"  码率 R = {rate:.4f}")
    print(f"  → 预测平均迭代次数 = {pred:.2f}")

    # ================================================================
    #  N=256, EbN0=8-12 关键验证
    # ================================================================
    # print("\n── N=256, EbN0=8-12 验证 ──")
    # truth = {
    #     8: {1/3:2.9942, 0.5:2.6948, 2/3:2.3484},
    #     9: {1/3:2.7760, 0.5:2.3542, 2/3:2.1123},
    #     10:{1/3:2.4739, 0.5:2.1259, 2/3:2.0290},
    #     11:{1/3:2.2195, 0.5:2.0340, 2/3:2.0051},
    #     12:{1/3:2.0694, 0.5:2.0064, 2/3:2.0003},
    # }
    # errs = []
    # for e in [8,9,10,11,12]:
    #     for r in [1/3,0.5,2/3]:
    #         p = predict_iter(e,256,r); t=truth[e][r]
    #         errs.append(abs(p-t)/t*100)
    #         print(f"  EbN0={e:3.0f} rate={r:.2f} true={t:.4f} pred={p:.4f} err={errs[-1]:.1f}%")
    # print(f"  → MAPE: {np.mean(errs):.1f}%")

    # # ── 全数据集 ──
    # print("\n── 全数据集 (100点) ──")
    # df = pd.read_excel(DATA_FILE)
    # Xa = df[RAW_FEATURES].values.astype(np.float64)
    # ya = df[TARGET_NAME].values
    # yp = predict_batch([(r[0],int(r[1]),float(r[2])) for r in Xa])
    # for lo,hi in [(2,4),(4.5,6),(8,12)]:
    #     m = (Xa[:,0]>=lo)&(Xa[:,0]<=hi)
    #     if m.sum(): print(f"  EbN0 {lo}-{hi}: MAPE={_mape(ya[m],yp[m])*100:.1f}% ({m.sum()}点)")
    # print(f"  整体 MAPE: {_mape(ya,yp)*100:.2f}%  R: {_r_score(ya,yp):.4f}")

    # print("\n✓ 完成")
