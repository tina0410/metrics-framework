# 统一指标框架

该框架统一 LS、MIMO、BP、Abs、ADD 和 MUL 的指标评估，同时让各模块保留独立 Python 和 RTL 工具环境。Abs 当前先接入延迟指标。

## 命令

```bash
python -m metrics_framework <ls|mimo|bp|abs|add|mul> predict [配置编号或路径]
python -m metrics_framework <ls|mimo|bp|abs|add|mul> evaluate [配置编号或路径]
```

安装根项目后可将 `python -m metrics_framework` 替换为 `metrics`。省略配置时运行模块清单中的五个默认 case；单 case 直接输出指标对象，批量输出 `{配置名称: 指标对象}`。

旧入口也接受新模式，例如：

```bash
python Generator/LSCE/evaluate_lsce.py predict 1
python Generator/MIMODetector/evaluate_mimo.py evaluate 2
python BPPredIter/BP_Evaluation/evaluate_bp.py predict 3
```

不带 `predict/evaluate` 的旧调用保持原有兼容行为。

## 输出契约

- `predict` 只写入并打印 `prediction.json`，其中只有预测值、预测时间和 GE 信息，不包含 `null` 对比字段。
- `evaluate` 验证完整时写入并打印 `evaluation.json`，展示结构与各模块原有 `*_metrics.json` 一致。
- `prediction.json` 和 `evaluation.json` 的预测、仿真、综合及总评估时间统一使用毫秒（`ms`）。
- 四项指标分别输出 `预测时间 (ms)`，计时从所需模型/工作簿加载完成后开始，到该指标的预测函数运行结束。
- 只有 `prediction.json` 末尾包含 `自动评估总时间 (ms)`，只累计延迟、面积、Throughput、硬件复杂度四项 predict 时间，不包含模型或工作簿读取、RTL仿真、DC综合、误差计算、adapter启动、文件保存和屏幕打印时间；`evaluation.json` 不计算或输出总时间。
- `evaluation.json` 的延迟分区保留 `仿真时间 (ms)`，面积分区保留 `综合时间 (ms)`，用于展示验证链耗时并计算速度提升倍数。
- 验证数据不完整时不生成 `evaluation.json`，stdout 完全为空，stderr 说明原因，退出码为 2。
- adapter 或框架自身出现未预期错误时 stdout 同样为空，退出码为 1。
- 批量 evaluate 是原子的：任一 case 失败，整个批次不打印部分 JSON；已经完成的 case 文件仍保留。
- 失败 case 的预测协议结果和错误记录保存在 `evaluation_output/<case>/diagnostics/`。

模型、生成器和仿真程序的普通输出不会混入 stdout；stdout 因此始终可以直接交给 JSON 解析器。

## JSON 验证数据

真实值可逐字段写入模块原配置：

```json
{
  "validation": {
    "area": {
      "actual_um2": 91814.8,
      "synthesis_time_ms": 103954.488,
      "reported_speedup": null
    },
    "latency": {
      "actual_cycles": 8,
      "simulation_time_ms": 3075.854,
      "output_interval_cycles": 4,
      "reported_speedup": null
    }
  }
}
```

非 `null` 字段直接使用；面积字段不足时读取对应 `Area_TP_Estimator` DC 结果，延迟或输出间隔不足时运行 RTL/C++ 验证。旧的 `use_config_actual_area`、`actual_area_um2`、`actual_time_ms` 和 `synthesis_time_ms` 仍受支持。

如果验证时间缺失但存在 `reported_speedup`，框架用该倍数和本轮预测时间恢复展示所需时间；两类数据都存在时以本轮计算倍数为准。

## Python API

```python
from metrics_framework import evaluate, predict

prediction = predict("ls", "1")
evaluation = evaluate("mimo", "configs/config_case3.json")
```

API 返回的对象与写入文件、成功时的 stdout JSON 相同。`evaluate` 验证不足时抛出 `EvaluationUnavailable`。

## 模块注册和接入

模块在 `registry.json` 中注册，字段包括：

- `root`：模块工作目录；
- `source`：基础模块的唯一设计源文件；
- `status`：`active` 表示已可评估，`registered` 表示已纳入框架但指标 adapter 待接入；
- `adapter`：协议脚本；
- `command`：独立进程命令，可使用 `{python}`、`{adapter}`、`{action}` 和
  `{config}` 占位符；省略动作或配置占位符时框架自动追加；
- `config_dir`、`config_pattern`、`default_cases`：配置解析规则；
- `python_env`：解释器覆盖环境变量；
- `output_root`：标准结果目录。

adapter 接受两个内部动作：

```text
python adapter.py predict CONFIG
python adapter.py validate CONFIG
```

成功时 stdout 必须只有一个协议 JSON，包含 `protocol_version`、`status`、
`module`、`action`、配置路径、规范化配置 SHA-256、证据路径和未舍入
`metrics`。每项指标通过 `source` 标记 `model`、`formula`、`config`、
`dc_reference`、`rtl` 或 `derived` 来源。日志写 stderr。验证数据或工具不可用
返回 2；未预期程序错误返回 1。

基础模块 `FxMatch` 、`Delay`、`Neg`、`Abs`、`SxMatch`、`Counter`、`CAdd`、
`CSub`、`CMul`、`CNorm`、`MUX`、`Add`、`Sub`、
`Mul`、`Comp`、`CompTree` 和 `AdderTree` 已全部登记。设计源统一位于
`Generator/BasicModules/<Module>`，测试入口位于各模块自己的 `tests` 子目录。
目前 Abs/SxMatch/Counter/CAdd/CSub/CMul/CNorm/Add/Mul 为 `active`；其余模块是 `registered`，调用指标评估时会明确
报告 adapter 和评估配置尚未接入，不会返回伪造指标。

### SxMatch 延迟评估

SxMatch 的五个配置对应 `Generator/BasicModules/SxMatch/tests/test_SxMatch.py`
中的五个参数组合；量化与溢出策略采用测试已有的 `TRN.TCPL` 和 `WRP.TCPL`。
模块的 FxMatch 转换为组合逻辑，之后由 `ModuleDelay(..., N_CLK=n_pipeline)`
输出，因此预测公式为 `latency_cycles = N_CLK = n_pipeline`。配置允许 0-cycle
组合延迟；`evaluate` 对每个 case 单独调用匹配的 pytest RTL scoreboard 测试，
并以配置中的流水深度作为该测试验证的 RTL 延迟。

面积和硬件复杂度暂显示为 `null`，Throughput 不输出。预测与评估输出均与 Abs
一致，并包含预测公式、仿真值和延迟误差。运行原 tests 需要 Python `pytest`、
PyTV，以及 `iverilog`、`vvp`；测试所需的临时 `modules` 包由框架从模块目录构造，
不依赖外部 ZIP。

### Counter 延迟评估

Counter 的五个配置分别对应 `Generator/BasicModules/Counter/tests/test_Counter.py`
的已覆盖位宽、步进、复位、同步清零和 wrap 组合。计数值及可选 wrap 标志都在
时钟上升沿寄存，预测公式为
`latency_cycles = 1 (posedge-registered count/wrap output)`。`evaluate` 对应运行
一个原生 pytest 测试，由 RTL scoreboard 连续验证 80 个计数周期；测试通过后，
将寄存器更新延迟作为仿真值并计算误差。

面积及硬件复杂度为 `null`，不显示 Throughput；输出格式与 Abs 相同。`evaluate`
需要 Python `pytest`、PyTV、`iverilog` 和 `vvp`。

### CAdd 延迟评估

CAdd 使用五个配置，前四项逐一对应
`Generator/BasicModules/CAdd/tests/test_CAdd.py` 中的四种定点格式与流水深度；
第五项重复 case1 的合法参数组合，保持默认五配置接口。实部、虚部分别调用
ModuleAdd，二者共用 `N_CLK` 流水延迟，预测公式为
`latency_cycles = N_CLK = n_pipeline`。`evaluate` 运行选定 pytest RTL scoreboard，
逐帧检查打包的复数输出；0-cycle 组合延迟有效，误差按仿真与预测 cycles 计算。

面积和硬件复杂度显示为 `null`，不输出 Throughput，终端结构与 Abs 一致。运行
tests 需要 Python `pytest`、PyTV、`iverilog` 和 `vvp`。

### CSub 延迟评估

CSub 使用与 CAdd 对应的四种定点格式和流水级数，另有一个使用 `TRN.SMGN` 与
`SAT.TCPL` 策略的第五配置；这五组参数均来自
`Generator/BasicModules/CSub/tests/test_CSub.py` 的参数组合。模块对实部、虚部
分别实例化 Sub，并共用 `N_CLK` 输出流水，因此预测公式为
`latency_cycles = N_CLK = n_pipeline`。`evaluate` 对每个配置运行原 pytest RTL
scoreboard，检查复数打包输出后报告仿真延迟和误差。0-cycle 配置有效。

CSub 暂不计算面积和硬件复杂度（显示 `null`），也不输出 Throughput；输出格式与
Abs 一致。需要 Python `pytest`、PyTV、`iverilog` 和 `vvp`。

### CMul 延迟评估

CMul 前四个配置对应原 tests 的四种定点格式/流水组合，`METHOD="4mul"`；第五个
配置使用同一合法参数组合，但选用 tests 覆盖的 `METHOD="3mul"`，并启用另一组
量化/溢出策略。两种结构都保持精确中间乘积，仅在输出转换处按
`N_CLK` 延迟，因此预测公式为 `latency_cycles = N_CLK = n_pipeline`。每次
`evaluate` 都单独运行 `test_CMul.py` 中与配置匹配的 RTL scoreboard；组合延迟
0-cycle 是合法值。

面积和硬件复杂度目前为 `null`，不输出 Throughput；预测/评估终端格式与 Abs
一致。运行 tests 需要 Python `pytest`、PyTV、`iverilog` 和 `vvp`。

### Abs 延迟评估

Abs 提供五个默认配置，对应 `Generator/BasicModules/Abs/tests/test_Abs.py`
中的规范测试用例。延迟预测公式为
`latency_cycles = N_CLK = n_pipeline`；`evaluate` 会运行对应测试用例的 C++ 黄金模型、RTL 生成、Icarus
仿真和逐帧输出比较，并将测试所验证的流水深度作为仿真值。组合逻辑的 0-cycle
延迟是合法结果，预测值与仿真值均为 0 时误差为 0%。

Abs 当前仅接入延迟指标；面积和硬件复杂度相关字段保留为 `null`，Throughput
不在 Abs 输出中展示。这些未接入指标不会阻止 `predict`
或 `evaluate` 输出延迟结果。Ubuntu 环境需提供
`clang++`、`iverilog` 和 `vvp`。

新增模块步骤：

1. 实现纯预测函数，禁止读取真实值或运行 RTL。
2. 实现纯验证函数，返回面积、综合时间、延迟、仿真时间、吞吐率输入和硬件复杂度真实值。
3. 使用 `adapters/common.py` 的 `run_cli` 封装协议。
4. 在 `registry.json` 注册模块和独立解释器环境变量。
5. 增加预测隔离、JSON 验证覆盖、验证失败零 stdout、完整 evaluation 快照测试。

MIMO 的面积项目与 RTL 项目存在同名旧模块，因此其 adapter 使用额外的 area worker 子进程；新模块存在类似命名或 ABI 冲突时也应使用同样的隔离方式。

### ADD 评估与 RTL 验证

ADD 配置使用 `input_1`、`input_2`、`output` 定义定点位宽、分数位宽和符号，`n_pipeline` 定义流水级数。统一指标要求正延迟和正复杂度，因此 ADD 评估配置要求 `n_pipeline >= 1`，五个默认 case 均保持 `n_pipeline = 1`。

- 延迟预测值为 `n_pipeline` cycles。验证从 `Generator/BasicModules/Add/tests` 调用测试链，并从 `Generator/BasicModules/Add` 加载 `ModuleAdd`、`FxMatch` 和 `Delay`；`ModuleCppConfig/ModuleCppRun + QuBLAS` 仍用作行为参考。
- 原 C++ 链连续生成三帧输入和黄金输出，Icarus Verilog 运行原 testbench 后，统一验证器逐帧比较 RTL 输出文件，并从标准 VCD 的 `Input_rdy`、`Output_rdy` 和时钟边沿测量 `sim_latency_cycles` 与 `sim_output_interval_cycles`；真实延迟必须等于 `n_pipeline`。
- ADD 的 `仿真时间 (ms)` 统计完整验证链耗时，计时范围包含 C++参考文件生成、PyTV RTL/testbench 生成、C++与Icarus编译、`vvp` 运行、逐帧比较和结果解析；它不是 Verilog 波形覆盖的几十个仿真 cycle 所对应的物理时间。
- 吞吐率复用上述同一次 RTL 仿真结果。预测值按每拍处理一帧计算：`predicted_Gframes/s = 1 / clock.period_ns`；仿真值按实测输出间隔计算：`actual_Gframes/s = 1 / (clock.period_ns × sim_output_interval_cycles)`。默认 ADD 的输出间隔为 1 cycle，因此预测值和仿真值一致。流水级数影响首帧延迟，但只要流水线能每拍接收数据，就不降低稳态吞吐率。
- `Gframes/s` 表示每秒十亿帧，`Gbps` 表示每秒十亿比特，两者物理意义不同。只有明确每帧包含的有效比特数后，才能按 `Gbps = Gframes/s × bits_per_frame` 换算。
- 面积预测校验并使用 `Area_TP_Estimator/Est/model/ADD_area.pkl` 的等价轻量系数；真实面积及综合时间按参数从 `ADD.xlsx` 精确匹配。自定义配置在工作簿中没有对应 DC 行时，需通过 `validation.area` 提供真实面积与综合时间。

运行 `evaluate` 前需确保 `clang++` 或 `g++`、`iverilog` 和 `vvp` 位于 `PATH`。生成的 RTL、C++输入/参考文件和仿真证据保存在 `Generator/BasicModules/Add/sim/<配置名>/`，其中 `simulation_result.json` 记录实测延迟、输出间隔、匹配帧数、参考链来源以及参与编译的 RTL 文件。

### MUL 评估与 RTL 验证

MUL 使用与 ADD 相同的定点配置字段。延迟预测值和 RTL 实测值均为 `n_pipeline` cycles，且统一评估要求 `n_pipeline >= 1`。

- 验证复用 MUL 原有的 PyTB 测试台、PyTV RTL 生成器与 QuBLAS C++ 黄金模型，然后使用 Icarus Verilog 执行 RTL 仿真；功能结果逐帧对比，延迟和输出间隔从 VCD 时钟边沿上的完整输入/输出序列独立测量。
- 吞吐率沿用 MUL 仿真中连续帧的时序语义：`Gframes/s = 1 / (clock.period_ns × output_interval_cycles)`。预测输出间隔为 1 cycle，RTL 验证则从相邻有效输出实测该间隔。
- 面积预测使用 `pure_MUL_area.pkl`、`SU_out_FxP_area.pkl` 和 `SU_in.xlsx` 的等价轻量表示，面积单位为 `μm²`。真实面积从 `MUL.xlsx` 的 DC 综合结果列精确查表。
- `MUL.xlsx` 的 `time` 列以秒记录，adapter 查表后转换为框架统一的 `ms`。硬件复杂度仍为 `area / GE_area × latency`，单位 `GE·cycles`。
- 工作簿只有一个共享的 `sign_in` 列；两输入符号性不同的自定义配置需在 `validation.area` 中提供真实面积和综合时间。

MUL 的 RTL、测试链和仿真证据均聚合在 `Generator/BasicModules/Mul`。运行完整验证前需确保 `clang++` 或 `g++`、`iverilog` 和 `vvp` 位于 `PATH`。`simulation_result.json` 会记录测量方法、匹配帧数、延迟、输出间隔、时钟周期及物理延迟。

### CNorm 延迟评估

CNorm 五个配置覆盖原 `tests/test_CNorm.py` 中的四种输入/输出格式、复位与流水深度组合；第五组复用第一组格式并选择测试覆盖的 `TRN.SMGN`、`SAT.TCPL` 策略。CNorm 将复数输入拆分为实部和虚部，分别取绝对值后求和，输出流水由 `N_CLK` 控制，因此预测公式为 `latency_cycles = N_CLK = n_pipeline`。每个配置单独运行对应 pytest RTL scoreboard，报告仿真延迟和误差，0-cycle 组合延迟合法。

面积和硬件复杂度为 `null`，不输出 Throughput，终端结构与 Abs 一致。运行 CNorm 原测试还需要 `Generator/jigger-basic-library(1).zip` 中的 `modules` 包，以及 Python `pytest`、PyTV、`iverilog` 和 `vvp`；评估时通过 zipimport 加载原测试依赖，不会将生成或仿真产物提交到仓库。
