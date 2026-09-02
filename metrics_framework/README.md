# 统一指标框架

该框架统一 LS、MIMO 和 BP 的面积、延迟、吞吐率与硬件复杂度评估，同时让各模块保留独立 Python 和 RTL 工具环境。

## 命令

```bash
python -m metrics_framework <ls|mimo|bp> predict [配置编号或路径]
python -m metrics_framework <ls|mimo|bp> evaluate [配置编号或路径]
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
- `prediction.json` 和 `evaluation.json` 末尾均包含 `自动评估总时间 (ms)`。预测模式累计四项预测时间；评估模式累计四项预测时间、延迟RTL仿真时间、面积DC综合时间以及指标校验/误差计算时间。两种模式均不包含模型或工作簿读取、adapter启动、文件保存和屏幕打印时间。
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

新增模块步骤：

1. 实现纯预测函数，禁止读取真实值或运行 RTL。
2. 实现纯验证函数，返回面积、综合时间、延迟、仿真时间、吞吐率输入和硬件复杂度真实值。
3. 使用 `adapters/common.py` 的 `run_cli` 封装协议。
4. 在 `registry.json` 注册模块和独立解释器环境变量。
5. 增加预测隔离、JSON 验证覆盖、验证失败零 stdout、完整 evaluation 快照测试。

MIMO 的面积项目与 RTL 项目存在同名旧模块，因此其 adapter 使用额外的 area worker 子进程；新模块存在类似命名或 ABI 冲突时也应使用同样的隔离方式。
