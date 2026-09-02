# LSCE 模块

LS 模块的固定根目录是 `Generator/LSCE`。统一框架会在独立进程中以该目录为
工作目录运行 LS adapter；模块源码、配置、环境和仿真文件不再散落在仓库根目录。

## 目录

```text
Generator/LSCE/
├── configs/                         # config_case1..5.json
├── designs/                         # LSCE RTL 生成器
├── BehaviorialVerification/
│   ├── BehavModel_LSCE.py           # 原始 C++ 算法与 main.cpp 生成器
│   ├── lsce_reference.py            # 独立 C++ 编译/运行适配层
│   ├── generate_lsce_testcase.py    # C++ 参考、RTL、testbench 生成
│   ├── validate_lsce_latency.py     # Icarus 实测与完整序列匹配
│   └── sim/TestcaseN/               # 本机运行时产物（Git 忽略）
├── evaluate_lsce.py                 # 原 LS Python API/兼容 CLI
└── pyproject.toml                   # LS 独立 Python 3.10 环境
```

## 无 binding 的验证链

LS 不再构建或导入 nanobind Python 扩展。一次 RTL 验证按以下顺序执行：

```text
LS adapter validate
  → generate_lsce_testcase
  → ModuleCppConfig 生成 config.h
  → ModuleCppRun 生成 main.cpp
  → Clang 20 / C++23 编译独立 LSCE.out
  → 运行 LSCE.out 生成 RTL 输入与 C++ 定点参考
  → 生成 LSCE RTL 和 testbench
  → Icarus iverilog + vvp
  → 从逐周期探针匹配完整 C++ 输出序列
  → 返回实测 latency cycles 和 output interval
```

这里没有 Python/C++ binding、CMake、Ninja 或 Python ABI 依赖。仍要求 Clang 20，
因为原 QuBLAS 算法使用 C++23。

## Ubuntu 环境

```bash
cd ~/Desktop/mjj/Generator/LSCE
python3.10 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .

export CXX=/usr/bin/clang++-20
iverilog -V
vvp -V
```

面积模型仍由仓库级 adapter 指向
`Area_TP_Estimator/Est_LS_CE_M2V`。如放在其他位置，运行前设置：

```bash
export LSCE_AREA_ROOT=/absolute/path/to/Est_LS_CE_M2V
```

模型由 scikit-learn 1.3.2 保存，LS 环境固定使用相同版本，避免反序列化版本警告。

## 运行

推荐从仓库根目录使用统一入口：

```bash
python -m metrics_framework ls predict 1
python -m metrics_framework ls evaluate 1
```

旧模块入口仍可在 LS 目录运行：

```bash
cd Generator/LSCE
python evaluate_lsce.py predict 1
python evaluate_lsce.py evaluate 1
```

`predict` 不编译 C++、不运行 Icarus，也不读取真实面积。`evaluate` 只有在 JSON
未提供完整真实延迟时才启动 RTL 链。

## 仿真产物

运行时文件固定保存到：

```text
Generator/LSCE/BehaviorialVerification/sim/TestcaseN/
├── config_snapshot.json
├── behavioral_o_H_reference.txt
├── rtl_o_H_latency_<N>cycles.txt
├── latency_check.txt
├── simulation_result.json
├── wave.vcd
└── workspace/
    ├── CppModules/
    │   ├── include/config.h
    │   ├── include/QuBLAS.h
    │   ├── main.cpp
    │   ├── LSCE.out
    │   └── reference_build.json
    ├── Generated_RTL/TestcaseN/
    ├── RTL/TestcaseN/
    ├── Input_Files/TestcaseN/
    ├── Comparison_Files/TestcaseN/
    └── Output_Files/TestcaseN/
```

这些运行时文件保持 Git 忽略。标准配置的可移植历史波形和截图另存于仓库根目录
`simulation_artifacts/ls/`。

## 测试

```bash
cd Generator/LSCE
python -m pytest -q
LSCE_RUN_NATIVE=1 python -m pytest -m native -q
LSCE_RUN_RTL=1 python -m pytest -m rtl -q
```

默认测试不要求本机具备 Clang/Icarus；native 和 RTL 测试必须在完整 Ubuntu
工具链中显式开启。
