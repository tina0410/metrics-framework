# 验收结果表自动填写脚本

`tools/fill_result_table.py` 用于在 VS Code 远端重新生成评估数据、汇总指标，并逐模块填写 `Result.docx`。

## 指标口径

- 面积预测偏差：保留 Word 表格中已经填写的值。
- 延迟预测偏差：对 5 个有效 `evaluation_output` case 的绝对误差取算术平均值。
- 定点计算复杂度预测偏差：按面积预测偏差填写，并逐 case 核对 JSON 中面积误差和硬件复杂度误差是否一致。
- 预测时间：单元格顺序为 `面积秒/延迟秒`，两项分别取最短时间。面积优先使用模块 Excel，缺失时使用 `evaluation_output`；延迟使用 `evaluation_output`。
- 速度提升：单元格顺序为 `面积倍数/延迟倍数`，两项分别取最小值，即最差速度提升。Excel 没有直接提供倍数时，逐行计算 `综合时间/评估时间`。

## 远端运行

先确认远端依赖（各模块所需 Python 环境、Icarus Verilog、C/C++ 编译器等）已经按 `metrics_framework/README.md` 配置。随后在仓库根目录运行：

```bash
python tools/fill_result_table.py \
  --repo-root . \
  --generate \
  --input-docx /path/to/Result.docx \
  --output-docx /path/to/Result_filled.docx \
  --report-json /path/to/result_metrics.json
```

如果在 VS Code 工作区使用与 Word 内容一致的 `Result.md`，可直接原地更新：

```bash
python tools/fill_result_table.py \
  --repo-root . \
  --generate \
  --input-md Result.md \
  --output-md Result.md \
  --report-json result_metrics.json
```

`--generate` 会对其他模块执行批量 `evaluate`；PUSCH_CE 的 5 个 case 单独调用 `Generator/PUSCH_CE/tests/validate_pusch_ce_latency.py`，运行 RTL 仿真取得真实延迟，并保存 `evaluation_output/configN/latency_evaluation.json`。这条路径不查询 PUSCH_CE 面积参数表，仍可计算延迟偏差、预测时间和延迟速度提升。面积性能缺少来源时显示 `-`。所有模块都要求 5 个有效延迟评估 case；生成失败时脚本停止且不输出半成品表格。

只汇总已有数据时可省略 `--generate`。排查不完整数据时可临时加 `--allow-partial`，此模式会在 JSON 报告中记录告警，并以 `-` 标记缺失项，不应作为正式验收结果。

DOCX 模式始终写入新文件；Markdown 模式可通过相同的输入输出路径原地更新。输出表格中的面积和延迟顺序也会写入报告的 `metric_order` 字段。
