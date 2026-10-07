# 验收结果表自动填写

`tools/fill_result_table.py` 从模块 Excel 和 `evaluation_output` 汇总验收指标，填写 `Result.docx` 或 `Result.md` 的 19 个模块行。脚本本身只依赖 Python 标准库；加上 `--generate` 后，评估命令仍需要各模块的 Python、RTL 仿真和编译环境。

## 指标口径

- 面积预测偏差：保留输入表格中已经填写的值，不重新计算或覆盖。Excel 中的 `MAPE` 可作为原始核对来源。
- 延迟预测偏差：取有效评估 case 的绝对误差算术平均值。普通模块默认要求 5 个有效 case；PUSCH_CE 当前**仅使用 `config1`**，所以该行使用单个 case 的误差，不取 5 个 case 平均值。
- 定点计算复杂度预测偏差：复制输入表格中的面积预测偏差；当同一评估 JSON 同时提供面积与复杂度误差时，逐 case 按 `--complexity-tolerance` 核对。
- 预测时间：单元格顺序为 `面积秒/延迟秒`。面积优先取模块 Excel 中的最短时间，缺失时取 `evaluation_output`；延迟取 `evaluation_output` 中的最短时间。JSON 的毫秒值会换算为秒。这里填写的是预测时间，不是 RTL 编译或仿真时间。
- 速度提升：单元格顺序为 `面积倍数/延迟倍数`，分别取有效值中的最小值（最差倍数）。面积 Excel 未直接给出倍数时，按同一行的 `综合时间/评估时间` 计算；Excel 不足时使用评估 JSON。PUSCH_CE 的面积倍数允许缺省并显示 `-`；其他普通模块在严格模式下缺少倍数会报错。大倍数由脚本以 `e` 记法输出，例如 `1.22e5`。

## 在 VS Code 远端运行

先按 [`metrics_framework/README.md`](../metrics_framework/README.md) 配置评估环境，并在仓库根目录运行。已有完整评估结果时，不加 `--generate` 即可只汇总数据：

```bash
python tools/fill_result_table.py \
  --repo-root . \
  --input-md Result.md \
  --output-md Result_filled.md \
  --report-json result_metrics.json
```

需要重新生成全部模块的评估数据时，加 `--generate`。`--python` 可以指定运行各模块评估命令的解释器；默认使用当前 Python：

```bash
python tools/fill_result_table.py \
  --repo-root . \
  --generate \
  --input-md Result.md \
  --output-md Result.md \
  --report-json result_metrics.json
```

只重新生成指定模块时，可加 `--modules`，参数接受表格名称或注册表 key。例如：

```bash
python tools/fill_result_table.py \
  --repo-root . \
  --generate --modules pusch_ce \
  --python .venv-framework313/bin/python \
  --input-md Result.md \
  --output-md Result.md \
  --report-json result_metrics.json
```

`--modules` **只限制重新生成的模块**，汇总填表仍处理全部 19 行；其他模块必须已有完整的 `evaluation_output` 和所需 Excel 数据，否则严格模式会报错。普通模块运行统一框架的批量 `evaluate`。PUSCH_CE 则单独运行面积预测和 `config1` 的 Verilator/cocotb RTL 延迟验证，分别写入 `Generator/PUSCH_CE/evaluation_output/config1/area_prediction.json` 和 `latency_evaluation.json`；面积预测时间从前者读取。使用的 Python 必须能导入 `cocotb_tools`，并且系统需要 Verilator。该延迟验证的仿真时间包括 RTL 生成、编译和测试，但填表的“延迟预测时间”只取 JSON 中的 `prediction_time_ms`。PUSCH_CE 历史数据未提供 DC 综合耗时，若面积速度提升没有其他有效来源，该单项显示 `-`。

填写 Word 三线表时改用 `--input-docx` 和 `--output-docx`：

```bash
python tools/fill_result_table.py \
  --repo-root . \
  --input-docx /path/to/Result.docx \
  --output-docx /path/to/Result_filled.docx \
  --report-json result_metrics.json
```

DOCX 输出必须是不同于输入的新文件，以保留原件；Markdown 可以通过相同输入、输出路径原地更新。`--generate` 在生成阶段出错时停止，不写半成品表格。只排查不完整数据时可用 `--allow-partial`：缺失项以 `-` 标记，告警写入 JSON 报告，不应作为正式验收结果。报告还包含逐模块来源、有效延迟 case 数，以及 `metric_order` 中的面积/延迟顺序。
