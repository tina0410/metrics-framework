# PUSCH 信道估计器 —— 面积评估程序（打包版）

## 1. 功能

输入 PUSCH 信道估计器的协议 / 架构 / 量化 / 实现配置，输出其 RTL 在
SMIC 65nm HD-LVT（TT, 1.0V, 25C，10MHz 约束）下的**综合面积估算值（um^2）**。

- **单 case 样例**：`python example_single_case.py`（见第 4 节）
- 单设计 API：`Est_PUSCH.Est_Top(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, protocol, architecture, quants, arithmetic, implementation)`
- 批量入口：`Est_PUSCH.main()` —— 读取同目录 `param.xlsx` 的 `parameters` 表

## 2. 目录内容

```
Est_PUSCH.py              主评估程序（Est_Top 及全部 Est_* 模块面积函数）
EstModule.py              基础算子面积模型（ADD / SUB / MUL / AdderTree），依赖 model/*.pkl
KeyParam.py               EstModule.py 的特征提取（不可分割的依赖）
model/                    ADD_area.pkl / pure_MUL_area.pkl / SU_out_FxP_area.pkl / SU_in.xlsx
basic_modules/            生成器基础模块（PyTV 风格），import 时会被加载
helpers/                  config_space / port_helpers / emit_helpers
top_api.py                ProtocolSpec / ArchitectureConfig / ... 与 resolve_top_config
dmrs_config.py            DMRS 端口 / RE 映射、CDM 组配置
analyze_timing.py         流水线深度 / 控制图分析
delay_budget.py           组合逻辑延迟预算（COST_* 常量）
lmmse_matrix_gen.py       LMMSE 系数矩阵与导频位置生成
v_*.py                    与生成器同源的结构定义
PyTU.py / constants.py    定点类型与全局常量
param.xlsx                测试用例表（50 组配置）
result.xlsx               评估结果表（24 组：逐模块 真实 vs 评估）
example_single_case.py    单 case 使用样例
README.md / requirements.txt
```

## 3. 依赖

```bash
pip install -r requirements.txt      # numpy pandas joblib openpyxl verithon
```

`pytv`（PyTV，pip 包名 `verithon`）必需：评估函数复用生成器结构定义，import 时会连带加载。
Python 3.8+（验证环境 3.12）。

## 4. 单 case 使用样例

```bash
python example_single_case.py            # param.xlsx 中 design_id=1
python example_single_case.py 14         # 指定 design_id
python example_single_case.py --demo     # 不读 Excel，用代码构造 case（演示 API）
```

输出示例：

```
case        : design_id=1 (from param.xlsx)
estimated   : 2754237.4 um^2
reference   : 2459651.9 um^2
rel. error  : +12.0%
```

两种写法：
- `case_from_table(design_id)`：读 `param.xlsx` 一行 → `Est_PUSCH._top_inputs_from_row(row)` → 5 个配置对象；
- `demo_case()`：用 `top_api` 的 `ProtocolSpec / ArchitectureConfig / ArithmeticConfig /
  ImplementationConfig` 与 `PyTU.QuType` 直接构造（不依赖 Excel）。

## 5. result.xlsx（评估结果表）

24 组**有 TOP 综合真值**的设计的逐模块对照，由本包**同一版本**程序生成（单位 um^2）。

| 列 | 含义 |
|---|---|
| `design_id` | `design1` … `design48`，对应 `PUSCH/RTL<id>` |
| `TOP_真实 / TOP_评估 / TOP_相对误差` | 顶层总面积：综合真值 / 本程序估算 / 相对误差 =(估−真)/真 |
| `<模块>_真实 / _评估 / _相对误差` | 11 个模块：CDM_CTRL、CFG_LATCH、CONTROLLER、C_INIT_GENERATION、FREQ_INTERP、LS、LS_BUF、PORT_ENABLE、TIME_INTERP、Y_PATH_REDUCE、Y_RB_ALIGN。`_真实` = TOP 层次报告里该模块**全部实例**的面积之和；`_评估` = 该模块对 TOP 的贡献（已含实例数与标定因子） |
| `其它逻辑_真实 / _评估 / _相对误差` | TOP 顶层未归入上述模块的零散单元（胶合逻辑） |

- 一致性：每行 `Σ模块_真实 + 其它逻辑_真实 = TOP_真实`，`Σ模块_评估 + 其它逻辑_评估 = TOP_评估`；
- 总体精度：MAE 6.9%、中位误差 −0.8%、19/24 在 ±10% 内、22/24 在 ±20% 内；
- 某设计不存在的模块留空（如 LS_BUF 只有 design30/46 有）；
- 明细说明见 `result.xlsx` 的「说明」sheet。

## 6. param.xlsx 的列说明（重要）

| 列 | 含义 |
|---|---|
| `area` | **TOP 综合真值**（um^2），仅 24 组有效设计有值，来源 `PUSCH/RTLx/Rep_RTLx.txt` |
| `Est`  | **历史遗留列，本包中为空，请勿使用** |

工程目录 `Est_PUSCH/param.xlsx` 原先在该列残留 7 个早期版本的陈旧值（design 1/3/6/8/11/12/14，与真值偏差
−27%~−84%），**已清理**（该列保留表头、内容为空，与 `PUSCH/param.xlsx` 一致）。
程序输出请以 `Est_PUSCH.main()` 生成的 `param_estimation_results.xlsx` 或本包 `result.xlsx` 为准。
`area` 为空的行（26 组）是未做 TOP 综合的设计，评估程序会自动跳过。

## 7. 其它用法

```python
import sys
_argv = sys.argv[:]; sys.argv = [sys.argv[0]]      # PyTV 会解析 sys.argv，先隔离
import numpy as np, pandas as pd, joblib
import Est_PUSCH as E
sys.argv = _argv

md = "model"
SU_in_db = pd.read_excel(f"{md}/SU_in.xlsx", sheet_name="SU_in")
Sub_db   = pd.read_excel(f"{md}/SU_in.xlsx", sheet_name="Sub")
Model_ADD = joblib.load(f"{md}/ADD_area.pkl")
Model_MUL = joblib.load(f"{md}/pure_MUL_area.pkl")
Model_SU_out = joblib.load(f"{md}/SU_out_FxP_area.pkl")

params = pd.read_excel("param.xlsx", sheet_name="parameters")
row = params[params["design_id"] == 1].iloc[0]
inputs = E._top_inputs_from_row(row)               # 5 个配置对象
area = float(np.asarray(E.Est_Top(Model_ADD, Sub_db, Model_MUL, Model_SU_out, SU_in_db, *inputs)).ravel()[0])
print(f"area = {area:.0f} um^2")
```

`parameters` 表的列定义：`design_id, num_RB_min/max, num_symbols_min/max, is_ECP, dmrs_Uplink,
dmrs_Type, is_double_dmrs, is_enhanced, dmrs_typeA_pos, additional_DMRS_range, antenna_ports,
slot_index_format, rb_parallelism, fi_lmmse_parallelism, freq_interp, time_interp, input_mode,
switchable_ports, fi_re_parallelism, ti_re_parallelism, fi/ti_lmmse_real_coeff, fi/ti_lmmse_coeff_source,
Y, H_LS, H_FI, H_TI, FI_LMMSE_COEFF, TI_LMMSE_COEFF, ls_quant_mode, ls_overflow_mode,
ti_lmmse_f_d_norm, ti_lmmse_w_coeffs, fi_lmmse_tau_rms/snr_linear/channel_model/delay_spread/scs,
sram_macro, production_observation_layouts, area`。

## 8. 模型的结构规则与标定（维护须知）

1. **有效 occasion 规则**（TI LMMSE core 系数列 / PILOT_SRAM_BANK 的 occasion bank / pre-FI 寄存器堆）：
   系数来源为 SRAM 时用 `max_occasions`；为 ROM 时常数系数列会被综合裁掉，只保留
   `max len(get_pilot_symbol_positions(l0,dbl,n_add,n_sym))` 列（分别 16/16、22/26、14/18 命中）。
2. **TI LMMSE core 乘法器缩放**：复数系数 0.52、ROM 常数乘法 0.72（16 组报告标定）。
3. **FREQ_INTERP 输出 FxMatch 块**：`RB_PARALLELISM*12*2` 路定点匹配器，按量化格式拟合（旧 1.3744 因子已取消）。
4. **C_INIT_GENERATION stage-3 乘法器**：按第一操作数位宽标定（5→0.90, 8→0.87, 9→0.52, 12→0.43）。
5. **LS 子树**：fdCDM/tdCDM 运行时可选时 ×0.74，固定时 ×1.16；**CFG_LATCH** ×1.3846。
6. 已补齐的空壳函数：`Y_PATH_REDUCE / Y_RB_ALIGN / PORT_ENABLE / CDM_CTRL / Counter / SRAM / LS_BUF / FxMatch`。

## 9. 精度与已知限制（24 组 TOP 综合真值）

- MAE 6.9%，中位误差 −0.8%，19/24 在 ±10% 内、22/24 在 ±20% 内。
- 剩余误差集中在 LS（48%）与 TIME_INTERP（45%）：来自"TOP 上下文裁剪"——同一份 RTL 作为子模块综合时
  面积小于独立综合值（LS 比值 0.39~1.00，只能按 fdCDM/tdCDM 是否运行时可选分成两支）。
  这部分**无法由配置参数预测**，需 DC 侧对照实验才能继续收敛。
- `production_observation`（`production_observation_layouts != None` 的分支）未包含，本交付不使用该路径。

## 10. 未打包内容

`Est.xlsx`、`param_estimation_results.xlsx`（中间/分析表）、`EstLS.py`（另一套架构的旧脚本，主流程未引用）、
`__pycache__`、`v_core_lmmse_interp.py`（仅生成器用，评估函数内部已实现对应结构）。
