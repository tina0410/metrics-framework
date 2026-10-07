# 统一指标框架

该框架统一 LS、MIMO、BP、PUSCH_CE，以及 Abs、Delay、FxMatch、MUX、Neg、Sub、AdderTree、Comp、CompTree、SxMatch、Counter、CAdd、CSub、CMul、CNorm、ADD 和 MUL 的指标评估，同时让各模块保留独立 Python 和 RTL 工具环境。每个基础模块的五个默认配置取自各自的 DC 面积报告。

## 命令

```bash
python -m metrics_framework <ls|mimo|bp|ce|abs|delay|fxmatch|mux|neg|sub|addertree|comp|comptree|add|mul> predict [配置编号或路径]
python -m metrics_framework <ls|mimo|bp|ce|abs|delay|fxmatch|mux|neg|sub|addertree|comp|comptree|add|mul> evaluate [配置编号或路径]
```

安装根项目后可将 `python -m metrics_framework` 替换为 `metrics`。省略配置时运行模块清单中的五个默认 case；单 case 直接输出指标对象，批量输出 `{配置名称: 指标对象}`。
`ce` 是 `pusch_ce` 的简写，两者使用同一 adapter、case 和输出目录。
PUSCH_CE 的历史表只提供真实面积而不提供 DC 综合耗时，因此标准 case
不会伪造“综合时间”和“速度提升倍数”；配置显式提供该时间后才显示这两项。

验收表的 Excel/`evaluation_output` 汇总、`Result.md` 或 `Result.docx` 自动填写方法，见 [验收结果表自动填写](../docs/result_table_filler.md)。

旧入口也接受新模式，例如：

```bash
python Generator/LSCE/evaluate_lsce.py predict 1
python Generator/MIMODetector/evaluate_mimo.py evaluate 2
python BPPredIter/BP_Evaluation/evaluate_bp.py predict 3
```

不带 `predict/evaluate` 的旧调用保持原有兼容行为。

## 输出契约

- `predict` 每次调用都会先删除旧 `prediction.json`，启动新的隔离 adapter 进程并重新执行各项预测、重新计时；旧预测文件和其中的时间绝不作为本轮输入。成功后只写入并打印本轮 `prediction.json`，其中只有预测值、预测时间和 GE 信息，不包含 `null` 对比字段。
- `evaluate` 将默认基础模块配置直接传入其原有 RTL 功能测试链，重新生成并运行 testbench；测试成功后才输出延迟和完整 `evaluation.json`。其中延迟周期由配置的流水级数给出，并由本轮 RTL 功能测试校验输出对齐。已有仿真结果文件、VCD、RTL 或可执行文件绝不作为本次输入复用。
- `prediction.json` 和 `evaluation.json` 的预测、仿真、综合及总评估时间统一使用毫秒（`ms`）。
- 四项指标分别输出 `预测时间 (ms)`。统一 CLI/API 的面积和延迟分别启动全新的单指标预测程序，由父进程在创建预测进程前开始计时、在进程退出后结束；包含进程创建、Python 解释器启动、模块导入、配置读取、模型/资源表加载、初始化、预测计算和预测程序结果输出。两项分别计时，不累计另一项预测。Throughput 和硬件复杂度仍只统计各自计算时间。低层 Python 预测函数内的计时用于诊断，包含模型加载但不代表完整程序耗时。
- 只有 `prediction.json` 末尾包含 `自动评估总时间 (ms)`，累计面积、延迟两个预测程序的完整耗时及 Throughput、硬件复杂度的计算时间；不包含外层 CLI/adapter 调度、验证参考表读取、RTL 仿真、DC 综合、误差计算、最终文件保存和打印；`evaluation.json` 不输出总时间。
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

面积的非 `null` 字段直接使用，字段不足时按完整参数精确匹配对应 `Area_TP_Estimator` DC 报告。默认五个基础模块配置以报告行参数为准，RTL 验证入口直接接收这些配置，而不再要求它们等于历史固定测试向量。配置的 `actual_cycles` 和 `output_interval_cycles` 仅作为一致性断言；`simulation_time_ms` 不作为本轮时间来源。旧的 `use_config_actual_area`、`actual_area_um2`、`actual_time_ms` 和 `synthesis_time_ms` 仍受支持。

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

基础模块 `FxMatch`、`Delay`、`Neg`、`Abs`、`MUX`、`SxMatch`、`Counter`、
`CAdd`、`CSub`、`CMul`、`CNorm`、`Add`、`Sub`、`Mul`、`Comp`、`CompTree` 和
`AdderTree` 已全部登记。设计源统一位于
`Generator/BasicModules/<Module>`，测试入口位于各模块自己的 `tests` 子目录。
目前 Abs/Delay/FxMatch/MUX/Neg/Sub/AdderTree/Comp/CompTree/SxMatch/Counter/CAdd/CSub/CMul/CNorm/Add/Mul 为 `active`；其余模块是 `registered`，调用指标评估时会明确
报告 adapter 和评估配置尚未接入，不会返回伪造指标。

### 基础模块完整指标评估

除 ADD、MUL 外，Abs、AdderTree、CAdd、CMul、CNorm、CSub、Comp、CompTree、
Counter、Delay、FxMatch、MUX、Neg、Sub 和 SxMatch 也已接入统一完整指标。每个模块
在 `Area_TP_Estimator/<Module>/` 下保留独立的 `est` 与 `report` 文件夹，不共享或
覆盖其他模块的模型、评估函数和 DC 报告。

- 面积预测直接调用 `est/Est_<Module>.py`；模型文件从同一模块的 `est/model`
  加载。运行环境需要 `joblib`、`numpy` 和 `scikit-learn`。
- 真实面积与综合时间按完整结构参数从 `report/test.xlsx` 或 `report/basic.xlsx`
  精确匹配，综合时间由秒转换为毫秒。找不到唯一 DC 行时不会选择近邻或复用其他
  配置，调用方必须通过 `validation.area.actual_um2` 以及
  `synthesis_time_ms`/`reported_speedup` 提供验证数据。
- 吞吐率与 ADD/MUL 使用相同口径：
  `effective_Gbps = output_bits / (clock.period_ns × output_interval_cycles)`；预测间隔
  为 1 cycle，验证使用 RTL 返回的输出间隔（旧测试结果未记录时按 1 cycle）。
- 定点硬件复杂度为 `area / GE_area × max(1, latency_cycles)`，GE 基准为
  `LVT_NAND2HDV0 = 1.12 μm²`。`max(1, ...)` 使组合模块按一个观察周期计量；
  MUX 或单输入树等纯直通结构允许面积与复杂度为 0。
- `evaluate` 的终端字段与 ADD/MUL 一致，包含延迟、面积、Throughput、硬件复杂度、
  预测/验证时间、误差及可计算的速度提升倍数。延迟验证仍运行各模块原有 pytest、
  C++ 黄金模型与 RTL/Icarus 链；组合逻辑的 0-cycle 延迟是合法结果。

完整 RTL 验证所需工具依模块而异，通常包括 Python `pytest`、PyVerilog、PyTV、
`clang++` 或 `g++`、`iverilog` 和 `vvp`。
新增模块步骤：

1. 实现纯预测函数，禁止读取真实值或运行 RTL。
2. 实现纯验证函数，返回面积、综合时间、延迟、仿真时间、吞吐率输入和硬件复杂度真实值。
3. 使用 `adapters/common.py` 的 `run_cli` 封装协议。
4. 在 `registry.json` 注册模块和独立解释器环境变量。
5. 增加预测隔离、JSON 验证覆盖、验证失败零 stdout、完整 evaluation 快照测试。

全指标 adapter 另外实现 `predict_metric(config_path, config, metric)`，分别执行 `area` 或 `latency`，并让 `predict(..., prepared=...)` 仅组合已取得的预测值及派生指标。`adapters/common.py` 启动 `prediction_worker.py`，从单指标程序启动前到退出后计时。仅延迟 adapter 可保留原接口，由 worker 单独运行其 `predict`。

MIMO 的面积项目与 RTL 项目存在同名旧模块，因此其 adapter 使用额外的 area worker 子进程；新模块存在类似命名或 ABI 冲突时也应使用同样的隔离方式。

### ADD 评估与 RTL 验证

ADD 配置使用 `input_1`、`input_2`、`output` 定义定点位宽、分数位宽和符号，`n_pipeline` 定义流水级数。统一指标要求正延迟和正复杂度，因此 ADD 评估配置要求 `n_pipeline >= 1`；五个默认 case 均保持 `n_pipeline = 1`，并固定使用 `10 ns` 时钟周期。

- 延迟预测值为 `n_pipeline` cycles。验证从 `Generator/BasicModules/Add/tests` 调用测试链，并从 `Generator/BasicModules/Add` 加载 `ModuleAdd`、`FxMatch` 和 `Delay`；`ModuleCppConfig/ModuleCppRun + QuBLAS` 仍用作行为参考。
- 原 C++ 链连续生成三帧输入和黄金输出，Icarus Verilog 运行原 testbench 后，统一验证器逐帧比较 RTL 输出文件，并从标准 VCD 的 `Input_rdy`、`Output_rdy` 和时钟边沿测量 `sim_latency_cycles` 与 `sim_output_interval_cycles`；真实延迟必须等于 `n_pipeline`。
- ADD 的 `仿真时间 (ms)` 统计完整验证链耗时，计时范围包含 C++参考文件生成、PyTV RTL/testbench 生成、C++与Icarus编译、`vvp` 运行、逐帧比较和结果解析；它不是 Verilog 波形覆盖的几十个仿真 cycle 所对应的物理时间。
- 吞吐率按有效输出 bit 计算，`effective_Gbps = output.bitwidth / (clock.period_ns × output_interval_cycles)`。预测按每拍输出一帧；仿真值继续从三帧 `Output_rdy` 的 VCD 时间戳实测输出间隔，再乘每帧的 `output.bitwidth`。默认 ADD `config_case2` 的输出宽度为 2 bit、时钟周期为 10 ns，因此预测值和当前实测值均为 `0.2 Gbps`。
- 面积预测校验并使用 `Area_TP_Estimator/Est/model/ADD_area.pkl` 的等价轻量系数；真实面积及综合时间按参数从 `ADD.xlsx` 精确匹配。自定义配置在工作簿中没有对应 DC 行时，需通过 `validation.area` 提供真实面积与综合时间。

运行 `evaluate` 前需确保 `clang++` 或 `g++`、`iverilog` 和 `vvp` 位于 `PATH`。生成的 RTL、C++输入/参考文件和仿真证据保存在 `Generator/BasicModules/Add/sim/<配置名>/`，其中 `simulation_result.json` 记录实测延迟、输出间隔、匹配帧数、参考链来源以及参与编译的 RTL 文件。

### MUL 评估与 RTL 验证

MUL 使用与 ADD 相同的定点配置字段。5 个标准配置统一使用 `10 ns` 时钟周期。延迟预测值和 RTL 实测值均为 `n_pipeline` cycles，且统一评估要求 `n_pipeline >= 1`。

- 验证复用 MUL 原有的 PyTB 测试台、PyTV RTL 生成器与 QuBLAS C++ 黄金模型，然后使用 Icarus Verilog 执行 RTL 仿真；功能结果逐帧对比，延迟和输出间隔从 VCD 时钟边沿上的完整输入/输出序列独立测量。
- 吞吐率按有效输出 bit 计算：`effective_Gbps = output.bitwidth / (clock.period_ns × output_interval_cycles)`。预测输出间隔为 1 cycle，RTL 验证则从相邻有效输出实测该间隔。
- 面积预测与当前 `Est.py::Est_MUL` 保持等价，使用 `pure_MUL_area.pkl`、`SU_out_FxP_area.pkl` 和 `SU_in.xlsx` 的轻量表示，面积单位为 `μm²`。真实面积从 `MUL0912.xlsx` 的 `dc综合结果` 列精确查表。
- `MUL0912.xlsx` 的 `time` 列以秒记录，adapter 查表后转换为框架统一的 `ms`。硬件复杂度仍为 `area / GE_area × latency`，单位 `GE·cycles`。
- 工作簿只有一个共享的 `sign_in` 列；两输入符号性不同的自定义配置需在 `validation.area` 中提供真实面积和综合时间。

MUL 的 RTL、测试链和仿真证据均聚合在 `Generator/BasicModules/Mul`。运行完整验证前需确保 `clang++` 或 `g++`、`iverilog` 和 `vvp` 位于 `PATH`。`simulation_result.json` 会记录测量方法、匹配帧数、延迟、输出间隔、时钟周期及物理延迟。

### 复数基础模块评估

SxMatch、Counter、CAdd、CSub、CMul 和 CNorm 均提供五个规范配置，并在
`evaluate` 时运行对应目录下原有的 pytest RTL 测试。延迟预测依据流水级数
（Counter 按寄存器行为使用一周期公式），面积、Throughput 和定点硬件复杂度
使用上文统一口径，终端格式与 ADD/MUL 一致。
