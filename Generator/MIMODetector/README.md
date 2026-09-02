# MIMO Detector 指标评估

本文档是 MIMO Detector 的快速入口，说明环境、顶层文件、配置改法、定点仿真与误差计算函数、输出文件、Bug 修复记录和当前进度。更完整的实现背景与波形复核方法见 [操作文档.md](./操作文档.md)。

## 1. 当前进度（2026-08-11）

| 功能 | 状态 | 说明 |
|---|---|---|
| 延迟预测 | 已完成 | 根据天线数、迭代次数和加法树流水级计算 |
| C++ 定点参考 | 已完成 | 每次按当前 JSON 重新生成输入和参考输出 |
| RTL 功能验证 | 已完成 | RTL 输出必须与 C++ 定点参考逐项一致 |
| RTL 真实延迟 | 已完成 | 从 VCD 时钟边沿定位完整输出向量 |
| Throughput | 已完成 | 分别输出预测值和 RTL 实测值 |
| 时钟参数传递 | 已完成 | JSON、TB、VCD 和指标统一使用 `clock.period_ns` |
| 面积预测/参考面积 | 已完成 | 现场调用 INSA 模型，并按完整结构参数匹配历史 DC 参考值 |
| 硬件复杂度 | 已完成 | 预测值使用预测延迟；真实值仅在 RTL 实测延迟可用时输出 |

### 延迟核心参数约束

| 参数 | 约束 |
|---|---|
| `Number of Transmit Antennas` | 正整数 |
| `Number of Receiving Antennas` | 正整数 |
| `Iterations` | 当前只支持 1、2、3 |
| `Adder Tree Pipelines` | 当前顶层校验要求正整数 |
| `Interface Reset Active Low` | 布尔值 |

### 延迟预测、输出间隔与频率

延迟预测函数为

```text
predicted_latency_cycles
= (Iterations + 1) × (N_T + Adder_Tree_Pipelines)
  + 4 × Iterations - 1
```

预测输出间隔由 `evaluate_mimo.py::predicted_output_interval_cycles()` 给出：

```text
predicted_output_interval_cycles = N_T
```

RTL 仿真输出间隔不直接采用预测值，而是由 `validate_mimo_timing.py::measure_rtl_timing()` 测量相邻完整输出向量首分量之间的时钟周期差。只有所有相邻帧间隔一致时，才写入 `sim_output_interval_cycles`。

时钟周期由配置中的 `clock.period_ns` 指定，频率换算为：

```text
clock_frequency_mhz = 1000 / clock_period_ns
physical_latency_ns = latency_cycles × clock_period_ns
```

当前标准配置使用：

```text
clock.period_ns = 10.0 ns
clock_frequency_mhz = 100 MHz
```


## 2. 环境配置

### 2.1 Python 环境

要求 Python 3.10 或更高版本。项目使用 `pyproject.toml` 管理依赖：

```bash
cd Generator/MIMODetector
uv sync
uv run python -c "import joblib, numpy, openpyxl, pandas, pytest, sklearn, sympy, pyverilog; print('python deps ok')"
```

RTL 生成器还依赖实验室提供的 `pytv`。如果它没有作为公开包安装，需要从本地源码安装：

```bash
uv pip install -e /path/to/pytv
uv run python -c "import pytv; print(pytv.__file__)"
```

### 2.2 Ubuntu 系统依赖

完整 C++/RTL 流程需要 Armadillo、BLAS、LAPACK、Icarus Verilog 和 Clang 20：

```bash
sudo apt update
sudo apt install -y libarmadillo-dev libblas-dev liblapack-dev iverilog
```

Ubuntu 22.04 默认 Clang 14 不能作为验收环境。安装并固定 Clang 20：

```bash
cd /tmp
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh 20

sudo update-alternatives --install /usr/bin/clang clang /usr/bin/clang-20 200
sudo update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-20 200
sudo update-alternatives --set clang /usr/bin/clang-20
sudo update-alternatives --set clang++ /usr/bin/clang++-20
```

检查环境：

```bash
clang++ --version
clang++ -std=c++23 -x c++ -fsyntax-only /dev/null
iverilog -V
vvp -V
```

项目语义是 C++23。代码仅允许在编译器参数名称上从 `-std=c++23` 回退到等价旧称 `-std=c++2b`，不允许把语言标准降为 C++20。

## 3. 顶层文件和函数

从 `evaluate_mimo.py` 启动完整评估。

指标计算通过三个可独立导入的接口模块接入顶层流程：

| 文件 | 接口 | 作用 |
|---|---|---|
| `latency_interface.py` | `evaluate_latency()` | 根据天线数、迭代次数和加法树流水级计算预测延迟，并对接可选 RTL 实测延迟 |
| `throughput_interface.py` | `evaluate_throughput()` | 根据天线数、QAM、输出间隔和时钟周期计算预测/仿真吞吐率 |
| `hardware_complexity_interface.py` | `evaluate_hardware_complexity()` | 从标准单元文件读取 1 GE 面积，根据面积和延迟计算预测/真实复杂度 |

三个接口采用统一聚合返回结构并保留未舍入数值，`evaluate_mimo.py` 只负责调用、结果字段映射和显示精度。

## 4. 运行方式和顶层返回结果

运行全部标准配置 `config_case1.json` 至 `config_case5.json`：

```bash
uv run python evaluate_mimo.py
```

只运行 case5：

```bash
uv run python evaluate_mimo.py 5
```

直接指定配置文件：

```bash
uv run python evaluate_mimo.py configs/config_case5.json
```

单配置顶层函数返回：

```text
{
  "延迟": {
    "预测结果 (cycles)", "仿真结果 (cycles)", "误差 (%)",
    "预测时间 (ms)", "仿真时间 (ms)", "速度提升倍数 (×)"
  },
  "面积": {
    "预测结果 (μm²)", "真实结果 (μm²)", "误差 (%)", "预测时间 (ms)",
    "综合时间 (ms)", "速度提升倍数 (×)", "真实结果类型", "参考表行"
  },
  "Throughput": {
    "预测结果 (Gbps)", "仿真结果 (Gbps)"
  },
  "硬件复杂度": {
    "预测结果 (GE·cycles)", "真实结果 (GE·cycles)", "误差 (%)",
    "GE基准单元", "1 GE面积 (μm²)"
  }
}
```

面积预测每次现场调用 `Area_TP_Estimator/Est_INSA_MMSE/mimo_area_interface.py`。
“真实结果”与“综合时间”来自 `lNSA结果260721_fixed.xlsx` 的历史 DC 记录，
结果中明确标记为历史参考值。未运行 RTL 时，真实硬件复杂度仍为 `null`。

## 5. 配置文件名和参数修改

### 5.1 文件名规则

标准配置放在 `configs/`，命名为：

```text
config_case1.json
config_case2.json
...
config_caseN.json
```

开启 RTL 仿真时，文件名必须能解析出非负整数 case 编号。推荐严格使用 `config_caseN.json`，这样配置、`TestcaseN`、仿真结果和最终指标可以一一对应。

不传参数时只批量运行 case1-case5；新增 case6 后需显式运行：

```bash
uv run python evaluate_mimo.py 6
```




修改配置后必须重新运行对应 case。程序会重建该 case 的 `workspace/`，确保旧 RTL、旧输入和旧参考不会混入新结果。


## 6. 误差计算位置

### 6.1 功能输出误差

`BehaviorialVerification/validate_mimo_timing.py::validate_case()` 中要求：

```text
actual RTL output == expected C++ fixed-point output
```

任一分量不一致即抛出错误，整次 RTL 仿真无效。

### 6.2 指标百分比误差

延迟误差在 `evaluate_mimo.py::run_mimo_evaluation()` 中计算：

```text
延迟误差 (%) = (RTL实测延迟 - 预测延迟) / 预测延迟 × 100%
```

这是有符号误差：正值表示预测偏小，负值表示预测偏大。只有 `flow.run_simulation=true` 时才计算。

面积误差使用预测面积与历史 DC 参考面积计算。硬件复杂度定义为：

```text
预测硬件复杂度 = 预测面积 / GE基准单元面积 × 预测延迟周期
真实硬件复杂度 = DC参考面积 / GE基准单元面积 × RTL实测延迟周期
```

`GE基准单元面积` 由 `hardware_complexity_interface.py` 从共享的
`Area_TP_Estimator/65nm Standard Cells Area.txt` 读取；当前
`LVT_NAND2HDV0` 为 `1.12 μm²`，不在评估主流程中硬编码。

因此只有 `flow.run_simulation=true` 且 RTL 验证成功时，真实硬件复杂度和误差才有值。

## 8. 输出文件说明

最终指标：

```text
evaluation_output/config_caseN/mimo_metrics.json
```

真实仿真产物：

```text
BehaviorialVerification/sim/TestcaseN/
├── config_snapshot.json              # 本轮完整配置快照
├── behavioral_output_reference.txt  # C++ 定点参考输出
├── rtl_output.txt                    # RTL 输出
├── latency_check.txt                 # 延迟、输出间隔、时钟摘要
├── simulation_result.json            # 机器可读仿真结果和测量方法
├── wave.vcd                          # 波形
└── workspace/
    ├── Generated_RTL/                # 按本轮配置生成的 RTL
    ├── RTL/                          # 仿真使用的 DUT 和 testbench
    ├── CppModules/                   # 本轮 C++ 定点程序和可执行文件
    ├── Input_Files/                  # 定点输入
    ├── Comparison_Files/             # C++ 参考输出
    ├── Output_Files/                 # RTL 输出
    └── Log_Files/                    # 比对日志
```

重新运行只重建所选 `TestcaseN/workspace/` 和同名标准结果，不删除其他 case，也保留 case 根目录中的用户附加分析文件。

## 9. Bug 修复记录

### 2026-07-23

- 修复评估默认 `50 ns` 与原 testbench `10 ns` 不一致；统一由 `clock.period_ns` 驱动 JSON、TB、VCD 和指标。
- 修复半周期被取整的问题，`10 ns` 现在稳定生成 `forever #5.0`，小数周期也可保留。
- 增加 TB 时钟反向校验，配置与生成波形相差超过 1 ps 时直接失败。
- 修复 `PyTB.py` 中损坏的 `ba    #/ @(posedge en);` 生成文本。
- 明确 `QAM Order=16`，并与固定 C++ 参考源交叉检查，避免错误沿用 64-QAM 面积脚本假设。
- 修复把 `control_n`、预测公式或绝对时间常量当作完成信号的问题；真实延迟改为 VCD 中完整输出向量匹配。
- 修复把首帧延迟当作吞吐间隔的问题；使用 3 帧输出独立测得相邻完整向量间隔。
- 纠正不适用的 `2×N_T` 候选输出间隔；当前结构预测和实测均为 `N_T`。
- 将活动仿真目录统一到 `BehaviorialVerification/sim/TestcaseN/`，稳定 C++ 源和 `QuBLAS.h` 移出会被清理的临时目录。

### 2026-07-24

- 修复 `Iterations=1` 时 C++ 定点模板仍无条件初始化第二轮变量，导致 `i_data_H2`、`i_data_D4`、`i_data_D5`、`i_data_HT3` 未声明的编译错误；这些初始化现在仅在 `Iterations >= 2` 时生成。
- 在 C++ 编译前增加 `i_data_*` 声明完整性检查，同类模板错误会直接报告缺失变量名。

- 确认 Clang 14/C++20 不是可行环境，固定 Ubuntu 验收环境为 Clang 20 和 C++23。
- `test_PE.py` 增加 C++23 参数探测；仅允许 `c++23` 与等价旧称 `c++2b` 之间回退。
- 精简最终 Throughput 为预测值和仿真值两项，详细测量元数据继续保存在 `simulation_result.json`。
- 修复精简输出时误删内部 `period_ns` 导致的 `NameError`，恢复时钟校验和 Throughput 计算。

### 2026-08-11

- 接入 INSA 单配置面积接口，按 Tx、Rx、流水级、迭代次数和全部量化格式匹配参考表。
- 面积模型在独立 Python 子进程运行，避免与 RTL 生成器的同名模块冲突。
- 历史重复记录仅在 DC 面积一致时接受；综合时间取匹配运行的中位数，并保留参考行号。
- Windows 生成的 Verilog 注释可能使用本地编码；时钟解析仅提取 ASCII 语法并容忍注释字节。

## 10. 当前限制

- 面积“真实结果”和“综合时间”是 INSA 工作簿历史参考值，不代表本轮重新运行 DC。
- `Iterations > 3` 不受支持，因为当前生成器只提供 `x1` 至 `x4`。
- 完整回归必须在具备 Clang 20、Armadillo/BLAS/LAPACK 和 Icarus Verilog 的 Ubuntu 环境运行。
- MIMO 顶层没有通用 `o_valid/done`，延迟终点必须继续使用完整输出向量匹配，不能改用内部控制信号。
- Throuput还没验证
