# LSCE 指标评估

## LS / MIMO / BP 统一入口

仓库现在提供可扩展的统一指标框架。详细协议、输出约定和新模块接入方法见
[`metrics_framework/README.md`](metrics_framework/README.md)。推荐从仓库根目录运行：

```bash
python -m metrics_framework ls predict 1
python -m metrics_framework mimo evaluate 3
python -m metrics_framework bp predict path/to/config.json
```

安装项目后也可使用等价的 `metrics` 命令。公开模式只有 `predict` 和
`evaluate`；验证是 adapter 的内部动作。纯预测不会读取真实面积或启动 RTL。
`evaluate` 验证失败时 stdout 为空、错误写入 stderr，并返回非零状态。

LS、MIMO 和 BP 的标准配置历史仿真结果与 `wave.vcd` 已归档到
[`simulation_artifacts/`](simulation_artifacts/README.md)。Ubuntu 拉取仓库后可直接
用 GTKWave 查看；模块运行时生成的完整 workspace 仍保持忽略，不会污染 Git。

三个模块可以通过环境变量选择自己的 Python 解释器：`LS_METRICS_PYTHON`、
`MIMO_METRICS_PYTHON` 和 `BP_METRICS_PYTHON`。未设置时优先使用模块自己的
`.venv`，最后使用启动框架的解释器。

本文档是 LS/LSCE 的快速入口，说明环境、顶层文件、配置改法、定点仿真与误差计算函数、输出文件、Bug 修复记录和当前进度。本次接口与维护说明如下。


## nanobind 改造与接口（2026-08-31）

已迁移到 nanobind 并接入评估链。用户完成 Linux 目录整理与 Python 3.10 环境重建后，提供的完整回归日志为 **55 passed、5 warnings，耗时 67.93 秒**：41 项契约测试、8 项原生构建/绑定调用/新旧 C++ 对比、6 项 RTL 回归全部通过。本机 Windows 缺少 Clang 20，未复现原生及完整 RTL 测试；不能将用户 Linux 结果算作本机验证。

调用链：

```text
CLI / run_lsce_evaluations / run_lsce_evaluation
  → load_config → _evaluate_config
  → evaluate_lsce_area → EstLSCE_GUI（现场预测）+ 工作簿/配置真实值
  → simulate_lsce → run_validation → generate_testcase
      → build_reference → nanobind(module.cpp.in) → Clang 20/C++23
      → reference_frames → 原 LSCE::LSCE_ACC
      → Python 写 RTL 输入/参考文件，生成 DUT/TB
      → 一次 Icarus 仿真 → 完整序列匹配 → 返回探针实测时序
  → 汇总并保存 lsce_metrics.json
```

不再通过两个 Python 子进程传递配置，也不回读 JSON 作为计算接口；批量与单 case 共用 `_evaluate_config`。配置由评估入口读取一次并向生成器传递，面积模型仍接收原始外部路径并在原有计时范围内读取配置。预测公式、单位、模型来源、工作簿时间乘 1000、时钟来源均保留。仿真计时仍包围整个 `simulate_lsce`（生成、构建、仿真、测量与保存），不是仅测 `vvp`；删除重复仿真会改变实际耗时，但不改变计时边界。

### 计数与公开接口

范围为完整评估调用链与其维护入口：**公开 Python API 2、C++ 绑定 API 1、CLI 入口 3、关键内部接口 17**。按定义符号计数，调用引用不重复计数；动态模块名不是新 API，CLI 的 `main` 不再算 Python API。内部清单包含跨模块边界及构建/测量维护入口，不是所有 `def` 的数量。原有可导入帮助函数没有删除，但不扩充顶层稳定公开契约。独立旧 `Generation.py`、设计文件的自测 `__main__`、pytest 测试和第三方 API 不计入评估 CLI。

以下位置均相对 LSCE 目录；`E=evaluate_lsce.py`，`B=BehaviorialVerification/lsce_binding.py`，`V=BehaviorialVerification/validate_lsce_latency.py`，`G=BehaviorialVerification/generate_lsce_testcase.py`。

| 类别 | 实际签名与定义 | 输入 → 输出 / 调用关系 |
|---|---|---|
| Python | `E: run_lsce_evaluation(config_filename: str \| Path = DEFAULT_CONFIG, *, clean_previous: bool = True) -> dict[str, Any]` | 配置路径（默认 case1）→ 原四组中文指标；调用 `_evaluate_config` |
| Python | `E: run_lsce_evaluations(config: str \| Path \| None = None) -> dict[str, dict[str, Any]]` | None=case1–case5、编号、外部路径 → `{config_stem: 指标}`；调用相同核心 |
| 绑定 | `bindings/reference.hpp: reference_frames(int n_frames = 10) -> std::map<std::string, std::vector<std::string>>` | Python `reference_frames(n_frames: int = 10) -> dict[str, list[str]]`；正帧数 → 定点输入、控制、完整参考；调用原 `LSCE_ACC` |
| CLI | `E: main() -> None`；`python evaluate_lsce.py [config]` | None/编号/路径 → 原批量结果和指标文件；调用批量 API；配置/构建失败退出 2 |
| CLI | `G: main() -> None`；`python BehaviorialVerification/generate_lsce_testcase.py --config PATH --case N` | 原始配置路径与匹配编号 → 新 RTL/TB/参考工作区；调用 `generate_testcase` |
| CLI | `V: main() -> int`；`python BehaviorialVerification/validate_lsce_latency.py [--config PATH] [--case N] [--skip-run]` | 默认 case1 → 实测结果；正常调用 `run_validation`；显式 skip-run 仅校验/展示历史结果且要求配置快照一致，不是本轮仿真 |

绑定只返回 8 个键：`i_Y`、`i_P`、`o_H`、`i_ctrl_stg` 及各自的 `Decimal_` 前缀版本。前两者每帧 `N_T/P_T` 行；`o_H` 每帧一行；控制在多组时包含流水前缀，单组为空。二进制打包顺序保留旧 C++ 的列倒序、接收通道倒序；十进制字符串只是追溯信息，不参与定点比较。所有容器按值转换为 Python 所有，不返回借用指针；保留 GIL，不并发操作 QuBLAS 随机状态。每次调用重置原 MT19937 种子 1，沿用原 `fill()`，不经 Python 浮点转换。此接口服务于确定性参考帧生成，不提供任意输入矩阵求解 API。

### 17 个关键内部接口

| # | 定义位置与实际签名 | 输入 → 输出；调用关系 |
|---|---|---|
| 1 | `E: load_config(path: Path) -> dict[str, Any]` | UTF-8/BOM JSON → 已验证配置；各入口 → `validate_config` |
| 2 | `E: validate_config(config: dict[str, Any], path: Path) -> dict[str, Any]` | 内存配置与源路径 → 同一配置或 ValueError；入口/验证/生成共用 |
| 3 | `E: _case_id(config_path: Path) -> int` | `config_caseN.json` → 非负编号；评估/生成/验证检查编号一致 |
| 4 | `E: latency_cycles(config: dict[str, Any]) -> int` | 配置 → 原预测延迟公式；核心/验证使用，不能替代探针实测 |
| 5 | `V: run_validation(config_path: Path, case_id: int, *, config: dict \| None = None) -> dict` | 配置/编号 → `case,predicted_latency_cycles,sim_latency_cycles,sim_output_interval_cycles,clock_period_ns,measurement_method`；评估 → 生成/仿真/测量 |
| 6 | `G: generate_testcase(config_path: Path, case_id: int, *, config: dict \| None = None) -> dict[str, list[str]]` | 配置 → 新参考行和当前 case 工作区；验证 → 绑定、RTL、TB |
| 7 | `B: build_reference(config: dict, artifact_dir: Path) -> ModuleType` | 已验证配置/构建记录目录 → 本轮新扩展模块；生成器 → CMake/nanobind/Clang/导入 |
| 8 | `B: generator_context()` | 无参数 → 上下文管理器；暂时设置旧生成器所需搜索路径与 argv，退出恢复 |
| 9 | `B: generator_parameters(config: dict) -> dict` | 已验证配置 → 原 QuType/QuMode/OfMode 与尺寸、流水参数；生成器/编译参数转换共用 |
| 10 | `B: render_parameters(config: dict) -> str` | 配置 → C++ `parameters.hpp` 文本；构建调用，维护编译期参数的源头 |
| 11 | `B: write_reference_files(rows: dict[str, list[str]], workspace: Path, case_id: int) -> None` | 内存参考行 → RTL 输入/比较文件；生成器调用 |
| 12 | `designs/LSCE.py: GenLSCE(ConfigFileName="./config.json", GenRoot="./RTL", *, config=None)` | 保留原路径参数，新增内存配置 → RTL 文件及生成时间（秒）；生成器调用 |
| 13 | `BehaviorialVerification/tb_LSCE.py: ModuleTbLSCE(...)`（完整签名见下） | 原定点/尺寸/时钟参数 → TB 与端口连接；生成器调用 |
| 14 | `BehaviorialVerification/BehavModel_LSCE.py: ModuleCppConfig()` | 无参数 → 生成算法声明与实现 `config.h`；构建调用 |
| 15 | `../../Area_TP_Estimator/Est_LS_CE_M2V/EstLS.py: EstLSCE_GUI(ModelADD, ModelMUL, ModelSU_out, SU_in_db, ConfigFileName="./config.json")` | 现场模型与真实配置路径 → `(area, nmse, TP)`；评估只取 area，辅助旧指标不进入新结果 |
| 16 | `BehavModel_LSCE.py: LSCE::LSCE_ACC<...>(...)`（完整声明见下） | 定点 Y/P 引用 → 写入 H；绑定实现调用，QuBLAS 类型不公开 |
| 17 | `V: measure_rtl_timing(probe_path: Path, expected_path: Path, *, expected_rows: list[str] \| None = None) -> tuple[int, int, list[str]]` | RTL 探针+完整参考 → 实测延迟、间隔、匹配序列；验证调用。传 rows 时不回读参考文件 |

```python
ModuleTbLSCE(N_T:int, N_R:int, P_T:int, P_R:int,
             QU_Y:QuType, QU_P:QuType, QU_H:QuType, QU_M_V:QuType,
             QU_MODE:QuMode, OF_MODE:OfMode, N_PIPELINES:list=[1, 1],
             CLOCK_PERIOD_NS:float=10.0, input_file_dir="../../Input_Files",
             output_file_dir="../../Output_Files", N_FRAMES=50)
```

```cpp
template <size_t N_T, size_t P_T, size_t P_R,
          typename QU_Y, typename QU_P, typename QU_H, typename QU_M_V>
inline void LSCE_ACC(Qu<dim<P_R, N_T>, QU_Y>& i_Y,
                     Qu<dim<N_T>, QU_P>& i_P,
                     Qu<dim<P_R>, QU_H>& o_H);
```

### 修改指南

| 任务 | 修改源文件/符号 | 重新生成、编译与验证 |
|---|---|---|
| 新增/修改绑定 | `bindings/reference.hpp` 添加/修改声明，`reference.cpp` 实现，`module.cpp.in` 的 `NB_MODULE` 中用 `module.def` 注册；若依赖配置，更新 `B:render_parameters` | 每次评估自动重新生成并编译；测试导入、真实调用、生命周期、非法输入、与旧 C++ 全序列对比，再跑 RTL |
| 隐藏绑定 | 从 `module.cpp.in` 删除对应 `module.def` 并移除 Python 调用点；C++ 声明可保留，不要修改构建目录内的 `module.cpp` | 重新生成/编译，确认 Python 属性消失；唯一必需接口不能直接隐藏，否则评估明确失败 |
| 新增配置 | 新建 `configs/config_caseN.json`；`E:load_config/validate_config` 校验；默认批量仍只有 case1–case5 | 显式运行编号或路径；参数决定生成/编译；工作簿须唯一匹配，或分别开启真实面积/综合时间覆盖值 |
| 修改编译期参数 | JSON 的 N_T/N_R/P_T/P_R、四组量化格式、量化/溢出模式、流水级 → `B:generator_parameters/render_parameters`；算法维护源为 `ModuleCppConfig` | 全部重新生成/编译，覆盖多组/单组、符号、位宽、舍入和溢出；完整 RTL 仍要求 P_R==N_R。时钟仅影响 TB/指标，但当前简单策略也会重建 |
| 新增指标 | `E:_evaluate_config` 添加字段；参考 `latency_cycles(config)`、`throughput_kchannels_s(config, period_ns)`；真实测量扩展 `V:run_validation`/探针，不能填预测数冒充实测 | 纯 Python 指标不需改绑定；若新 C++ 输出则重新生成/编译。校验公式、单位、时钟、时间范围和返回结构 |
| 修改面积模型 | 继续使用 `E:evaluate_predicted_area/evaluate_lsce_area`、`EstLSCE_GUI`；实际面积/综合时间使用 `select_actual_area/select_actual_time` 与工作簿规则 | 不需重建绑定；现场模型回归、配置/工作簿来源回归。该模型目录是独立 Git 仓库，不能随外层仓库一起提交 |

绑定改为 nanobind 显式注册：`reference.hpp` 是纯 C++ 声明，`reference.cpp` 保留定点计算，`module.cpp.in` 是唯一注册模板。没有自动扫描或导出未注册声明。CMake 只替换模板里的模块名，不再运行额外的 Clang 解析器。`nanobind/stl/map.h`、`string.h`、`vector.h` 负责按值转换，参数名与默认值在注册模板维护；使用 `.noconvert()` 拒绝把浮点帧数隐式转换为整数。默认保留 GIL、不启用 free-threaded/stable-ABI 构建。上游依据：[构建文档](https://nanobind.readthedocs.io/en/latest/building.html)、[类型转换](https://nanobind.readthedocs.io/en/latest/exchanging.html)。

每次构建使用独立 `_lsce_<uuid>` 模块名和 `.binding_builds/` 目录，**不缓存或复用扩展**，失败没有回退。保留它们是因为 Windows 无法删除仍加载的扩展；退出使用这些模块的 Python 进程后可手动清理 `.binding_builds/`。`workspace/CppModules/binding_build.json` 保存配置、源码（含注册模板）散列、nanobind 版本、编译器、Python ABI、二进制位置及成功/失败状态，配置/编译日志同目录保存。编译器预检失败时尚无构建记录，错误直接返回。

### 最小运行与验证

统一在 Linux、Python 3.10.x、Clang 20 环境运行（现有模型版本为 scikit-learn 1.3.2）：

```bash
export CXX=/usr/bin/clang++-20
uv sync --python 3.10 --extra bindings
uv pip install 'numpy<2' 'scikit-learn==1.3.2'
uv run --no-sync python evaluate_lsce.py 1
uv run --no-sync pytest -q
LSCE_RUN_NATIVE=1 uv run --no-sync pytest -m native -q
LSCE_RUN_RTL=1 uv run --no-sync pytest -m rtl -q
```

`bindings` extra 在 Windows/Linux 均安装 nanobind（锁文件固定 2.15.0），不依赖平台专属绑定生成器。项目、锁文件和 CMake 统一要求 Python 3.10.x；Python 3.11 只保留为历史契约测试记录，不属于当前支持矩阵。面积模型固定使用 scikit-learn 1.3.2。Windows 原生构建还需要 Clang 20、MSVC C++ 工具和 Windows SDK；不能复制 Linux `.venv` 使用，也不能改用 Clang 22/C++20 验收。

面积估计器及模型是独立仓库，不包含在本仓库或 `uv sync` 安装内容中。默认目录仍为相对本文件的 `../../Area_TP_Estimator/Est_LS_CE_M2V`。如果克隆位置多了一层目录，或模型保存在别处，在启动 Python 前指定实际目录：

```bash
export LSCE_AREA_ROOT="$HOME/Desktop/mjj/Area_TP_Estimator/Est_LS_CE_M2V"
test -f "$LSCE_AREA_ROOT/EstLS.py"
LSCE_RUN_RTL=1 "$UV_PROJECT_ENVIRONMENT/bin/python" -m pytest -m rtl -vv -x
```

上面路径仅是原工程布局示例，必须指向自己的真实目录。目录需要 `EstLS.py`、`EstModule.py`、`KeyParam.py`、`PyTU.py`、`model/SU_in.xlsx`、`model/ADD_area.pkl`、`model/pure_MUL_area.pkl` 和 `model/SU_out_FxP_area.pkl`。工作簿真实值仍从同目录 `LSCE结果.xlsx` 读取；只有配置同时显式覆盖真实面积与综合时间时才不需要该表。只加载可信来源的 pickle 模型。缺文件会明确列出目录和缺失项，不搜索其他模型或用预测值代替真实值。

`E:_configured_area_root() -> Path` 是模块内路径辅助函数，不计入关键跨模块接口。它在导入时读取 `LSCE_AREA_ROOT`（支持 `~`，相对路径基于启动目录），统一设置 `AREA_ROOT` 与 `AREA_RESULTS`。改目录只需重启 Python，无需重新生成或编译 C++；应重跑现场面积模型与完整 RTL 回归。未设置变量时保留原有行为，空变量报错。

```python
from evaluate_lsce import run_lsce_evaluation, run_lsce_evaluations
one = run_lsce_evaluation("configs/config_case1.json")
selected = run_lsce_evaluations("3")
all_cases = run_lsce_evaluations()
```

直接检查首个绑定（内部维护用）：

```python
from pathlib import Path
from evaluate_lsce import load_config
from BehaviorialVerification.lsce_binding import build_reference
config = load_config(Path("configs/config_case1.json"))
module = build_reference(config, Path("evaluation_output/binding_check"))
frames = module.reference_frames(10)
assert len(frames["o_H"]) == 10
```

验证记录（2026-08-31）：

- 路径修复回归：本机 Python 3.14 下 41 passed / 14 skipped；新增默认目录兼容、外部目录、空变量、缺文件诊断测试。Python 3.11 下通过 `LSCE_AREA_ROOT` 现场运行五个标准 case 的面积模型及工作簿读取成功；没有模拟面积输出，未运行完整 RTL。
- 通过：Python 3.14 / 3.11 各 37 项契约测试；包括配置非法输入、外部 BOM 配置、参数变化、清理隔离、模板实际生成、全参考序列匹配逻辑。形状/调度测试明确使用 mock，不算 RTL 验证。
- 通过：scikit-learn 1.3.2 现场运行 case1–case5 面积模型和工作簿真实值读取；预测面积分别为 90258.32、122071.89、176565.29、174528.77、161875.33 μm²。外部配置在 `run_simulation=false` 下的单 case、批量、CLI 和时钟修改回归通过，RTL 字段保持 None。
- 通过：五个标准 case 的真实 RTL/TB 生成与 Icarus 编译（含面积模型先加载后的同进程导入顺序）；未运行 vvp，不代表 RTL 功能或时序验证。
- 通过：自有 21 个 Python/生成模板文件无中文注释或 docstring；不改第三方 `pytv/`、QuBLAS、许可证或中文业务字段。算法模板仅删除无用日志流并简化英文注释，算术未变。
- 失败：主动启用 case1 原生回归，在 Clang 版本预检被阻止（本机为 22.1.8）。nanobind 2.15.0 已在 Windows 的隔离 Python 3.11/3.14 环境安装成功。没有伪造成功或回退旧产物。
- 工具链补齐尝试：系统 Clang 为 22.1.8，Visual Studio 附带版本为 22.1.3；官方 Clang 20 压缩包下载约几十 KB/s，预计数小时，已停止。没有替换系统编译器。
- 用户 Linux 验证：Python 3.10.19，设置 `CXX=clang++-20` 与 `LSCE_RUN_NATIVE=1` 后，8 passed / 43 deselected；包括标准 case1–case5 和 parallelism、quantization、single_stage 配置变更。此结果来自用户提供的真实日志，未在本机复跑。
- 用户 RTL 初次验证失败：首个 case 在 `_load_area_evaluator` 导入 `EstLS` 时失败；后续 5 项因 `-x` 未执行。该问题随后通过恢复面积路径修复及统一运行目录解决。
- 用户最终 Linux 验证：在 `~/Desktop/mjj/Generator/LSCE` 使用重建的 `.venv-lsce`（Python 3.10），显式指定两份测试文件并开启 `LSCE_RUN_NATIVE=1 LSCE_RUN_RTL=1`，结果为 55 passed / 5 warnings，67.93 秒。覆盖标准 case1–case5、三组原生配置变更和外部 RTL 配置变更；RTL 回归经真实完整 C++ 序列匹配及探针测量链路，没有用预测值替代 RTL 结果。结果来自用户日志，未在本机复跑。
- 剩余警告：第三方 pyverilog 的无效转义、pytv 的三个配置模块端口/名称提示，以及自有 `designs/Delay.py` 自测入口中路径字符串的无效转义；均未造成此次测试失败。安装包行为未验收，本次按源码运行。测试通过不表示这些警告已经修复。
- 本机未执行：原生编译、扩展导入/真实调用、新旧 C++ 位级对比、完整 RTL。默认套件跳过 8 项原生、6 项 RTL 测试。
- 已解决的测试环境问题：Python 3.11 的临时目录权限冲突通过工作区专属 `--basetemp` 解决；Windows GBK 打印单位字符失败通过 UTF-8 测试输出解决。两者均已重跑。

清理仅重建当前 case 的七个标准 workspace 子目录，删除当前标准成功标记/指标文件；保留其他 case、case 根目录和用户额外文件，并拒绝经符号链接或 junction 重定向的工作区。面积预测计时仍包围原模型入口，真实综合时间绝不用本轮仿真时间替代。

## 1. 当前进度（2026-07-24）

| 功能 | 状态 | 说明 |
|---|---|---|
| 统一单/批量入口 | 已完成 | 支持 case1-case5、单编号和外部 JSON |
| 参数校验 | 已完成 | 支持 UTF-8 BOM、任意非负 case 编号、位宽和并行度校验 |
| 延迟预测 | 已完成 | 根据发送方向分组数和流水级计算 |
| C++ 定点参考 | 已完成 | 每次按当前 JSON 重建输入和参考输出 |
| RTL 功能验证 | 已完成 | 完整 `o_H` 序列必须与 C++ 定点参考一致 |
| RTL 真实延迟/间隔 | 已完成 | 从逐周期 RTL 探针独立测量 |
| 面积预测和真实面积 | 已完成 | 现场调用面积模型；真实值来自配置或工作簿 |
| Throughput | 已完成 | 预测值与 RTL 实测间隔分别计算 |
| 硬件复杂度 | 已完成 | 面积换算 GE 后乘以延迟 |
| 时钟参数传递 | 已完成 | JSON、TB、仿真元数据和 Throughput 使用同一周期 |

### 延迟核心参数约束

| 参数 | 约束 |
|---|---|
| `Number of Transmit Antennas` | 正整数 |
| `Number of Receiving Antennas` | 正整数 |
| `Parallelism T` | 正整数、不得大于 `N_T`，且必须整除 `N_T` |
| `Parallelism R` | 正整数、不得大于 `N_R`，且必须整除 `N_R`；当前完整 RTL 仿真要求 `P_R == N_R` |
| `Pipeline Stages ([Multiplication, Adder Tree])` | 必须包含两个非负整数 |
| `clock.period_ns` | 有限正数 |

### 延迟预测、输出间隔与频率

延迟预测函数为 `evaluate_lsce.py::latency_cycles()`：

```text
STG_T = ceil(N_T / P_T)

当 STG_T > 1：
  predicted_latency_cycles = sum(Pipeline_Stages) + STG_T

当 STG_T = 1：
  predicted_latency_cycles = sum(Pipeline_Stages)
```

预测输出间隔采用发送方向分组数：

```text
predicted_output_interval_cycles = STG_T = ceil(N_T / P_T)
```

RTL 仿真输出间隔在逐周期 `o_H` 探针中匹配相邻完整 C++ 定点参考帧后测得，写入 `sim_output_interval_cycles`。

时钟周期由配置中的 `clock.period_ns` 指定，频率和物理延迟换算为：

```text
clock_frequency_mhz = 1000 / clock_period_ns
physical_latency_ns = latency_cycles × clock_period_ns
```

当前五个标准配置使用：

```text
clock.period_ns = 10.0 ns
clock_frequency_mhz = 100 MHz
```

## 2. 环境配置

### 2.1 Python 环境

要求 Python 3.10.x；Python 3.11 及更高版本会在依赖解析或 CMake 配置阶段明确失败：

```bash
cd Generator/LSCE
uv sync --extra bindings
uv run python -c "import joblib, numpy, openpyxl, pandas, pytest, pyverilog, sklearn; print('python deps ok')"
```

RTL 生成还依赖实验室提供的 `pytv`：

```bash
uv pip install -e /path/to/pytv
uv run python -c "import pytv; print(pytv.__file__)"
```

面积模型由 `pyproject.toml` 中的 pandas、openpyxl、joblib 和 scikit-learn 加载。现有模型由 scikit-learn 1.3.2 保存；正式复现建议使用相同版本。

### 2.2 Ubuntu 系统依赖

完整 C++/RTL 流程需要：

```bash
sudo apt update
sudo apt install -y libarmadillo-dev libblas-dev liblapack-dev iverilog
```

Ubuntu 22.04 默认 Clang 14 不满足当前 QuBLAS/C++23 代码。安装并固定 Clang 20：

```bash
cd /tmp
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh 20

sudo update-alternatives --install /usr/bin/clang clang /usr/bin/clang-20 200
sudo update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-20 200
sudo update-alternatives --set clang /usr/bin/clang-20
sudo update-alternatives --set clang++ /usr/bin/clang++-20
export CXX=/usr/bin/clang++-20
```

检查：

```bash
"$CXX" --version
"$CXX" -std=c++23 -x c++ -fsyntax-only /dev/null
iverilog -V
vvp -V
```

新绑定构建明确使用 C++23；旧对照脚本的 `-std=c++2b` 同样表示 C++23，不能降为 C++20。

## 3. 顶层文件和函数

从 `evaluate_lsce.py` 启动完整评估。

## 4. 运行方式和顶层返回结果

运行 case1-case5：

```bash
uv run python evaluate_lsce.py
```

只运行 case3：

```bash
uv run python evaluate_lsce.py 3
```

直接指定配置文件：

```bash
uv run python evaluate_lsce.py configs/config_case3.json
```

从 Python 调用：

```python
from evaluate_lsce import run_lsce_evaluation, run_lsce_evaluations

one = run_lsce_evaluation("configs/config_case3.json")
all_cases = run_lsce_evaluations()
case3 = run_lsce_evaluations("3")
```

单配置顶层函数返回：

```text
{
  "延迟": {
    "预测结果 (cycles)", "仿真结果 (cycles)", "误差 (%)",
    "预测时间 (ms)", "仿真时间 (ms)", "速度提升倍数 (×)"
  },
  "面积": {
    "预测结果 (μm²)", "真实结果 (μm²)", "误差 (%)",
    "预测时间 (ms)", "综合时间 (ms)", "速度提升倍数 (×)"
  },
  "Throughput": {
    "预测结果 (kChannels/s)", "仿真结果 (kChannels/s)"
  },
  "硬件复杂度": {
    "预测结果 (GE·cycles)", "真实结果 (GE·cycles)", "误差 (%)",
    "GE基准单元", "1 GE面积 (μm²)"
  }
}
```

## 5. 配置文件名和参数修改

### 5.1 文件名规则

标准配置位于：

```text
configs/config_case1.json
...
configs/config_case5.json
```

开启真实 RTL 仿真时，文件名必须严格为 `config_caseN.json`，其中 `N` 是非负整数。配置名决定 testcase 和默认输出目录：

```text
config_case7.json
→ BehaviorialVerification/sim/Testcase7/
→ evaluation_output/config_case7/lsce_metrics.json
```

不传参数只批量运行 case1-case5；新增 case6 后需显式运行：

```bash
uv run python evaluate_lsce.py 6
```


预测 Throughput 位于 `throughput_kchannels_s()`：

```text
predicted_throughput_kChannels_s
= 1e6 / STG_T / clock_period_ns / N_R
```

仿真 Throughput 使用 RTL 实测的 `sim_output_interval_cycles` 替代 `STG_T`。

### 5.3 面积真实值来源

预测面积始终现场调用：

```text
Area_TP_Estimator/Est_LS_CE_M2V/EstLS.py::EstLSCE_GUI()
```

工作簿真实值位于：

```text
Area_TP_Estimator/Est_LS_CE_M2V/LSCE结果.xlsx
```

当配置开关为 `false` 时，程序按 `P_T`、`N_T`、`P_R`、四组量化格式和流水级精确匹配唯一一行。修改这些参数后若工作簿没有对应记录，评估会报错；可以补充工作簿记录，或显式启用配置中的真实面积/时间。


## 8. 输出文件说明

最终指标：

```text
evaluation_output/config_caseN/lsce_metrics.json
```

真实仿真产物：

```text
BehaviorialVerification/sim/TestcaseN/
├── config_snapshot.json              # 本轮完整配置快照
├── behavioral_o_H_reference.txt      # C++ 定点参考输出
├── rtl_o_H_latency_<N>cycles.txt     # 从逐周期 RTL 探针提取的匹配输出
├── latency_check.txt                 # 预测/实测延迟、输出间隔、时钟和来源
├── simulation_result.json            # 机器可读仿真结果
├── wave.vcd                          # 波形
└── workspace/
    ├── Generated_RTL/TestcaseN/      # 按本轮配置生成的 RTL
    ├── RTL/TestcaseN/                # 仿真使用的 DUT 和 testbench
    ├── CppModules/                   # 本轮绑定构建记录和日志
    ├── Input_Files/TestcaseN/        # 定点输入
    ├── Comparison_Files/TestcaseN/   # C++ 参考输出
    └── Output_Files/TestcaseN/       # RTL 输出
```

`config_snapshot.json` 用于确认结果对应哪组参数。重新运行会重建所选 case 的标准 `workspace/` 内容并覆盖同名结果，但保留 `TestcaseN` 根目录、其他 case 和用户额外文件。

当前 `evaluate_lsce.py` 统一流程使用 `BehaviorialVerification/sim/TestcaseN/workspace/Generated_RTL/`。

## 9. Bug 修复记录

### 2026-07-23

- 修复用预测公式冒充 RTL 仿真延迟的问题；实测值改为从完整 C++ 参考序列在逐周期 RTL 探针中的位置得到。
- 修复配置、testbench 和指标时钟来源不一致；五个标准配置统一为 `clock.period_ns=10.0`，TB 生成 `#5.0` 半周期。
- 增加 TB 时钟反向解析和 1 ps 精度校验，避免波形时钟与指标换算不一致。
- 修复面积预测使用历史表格“自动评估结果”的问题；现在每次现场调用 `EstLSCE_GUI()` 并记录真实执行时间。
- 分离真实面积和真实综合时间的来源开关，修复工作簿 `time` 秒/毫秒单位混用。
- 修复公共 `sim/`、`third_party_validation/` 和基准目录并存造成的结果来源不唯一；统一到 `BehaviorialVerification/sim/TestcaseN/`。
- 修复单 case 运行可能清理其他 case 或用户文件的问题；只重建本 case 的标准工作区。
- 将 `QuBLAS.h` 等稳定依赖移出临时生成目录，避免清理后 C++ 无法重建。新绑定直接包含维护依赖头，不复制修改它。
- 修复外部配置回退读取项目内同编号 JSON 的问题；实际配置路径现在贯穿生成和验证链路。
- 增加 UTF-8 BOM、非负 case 编号、并行度、位宽、流水级和时钟参数校验。

### 2026-07-24

- 确认 Ubuntu 默认 Clang 14 无法正确编译当前 QuBLAS/C++23 代码，固定验收环境为 Clang 20。
- 编译器选择顺序改为 `CXX`、`clang++-20`、`clang++`；正式运行建议显式设置 `CXX=/usr/bin/clang++-20`。
- 明确 `-std=c++2b` 与 `-std=c++23` 是同一语言标准的不同参数名，禁止通过降到 C++20 规避错误。
- 固化模型预测时间、本轮 RTL 仿真时间和 DC/工作簿参考综合时间三类口径，避免互相替代。

## 10. 当前限制

- 真实 RTL 仿真暂时要求 `P_R == N_R`；`P_R < N_R` 只覆盖一个接收分组。
- 配置参数若无法在 `LSCE结果.xlsx` 唯一匹配真实面积/综合时间，需要补表或启用配置覆盖值。
- 完整回归必须在具备 Clang 20、Icarus Verilog、`pytv` 和 Python 面积模型依赖的环境运行。
- scikit-learn 版本不同可能出现模型反序列化警告；正式复现建议使用 1.3.2。
- 顶层旧 `RTL/` 目录仍被兼容入口引用，暂不能直接删除。
