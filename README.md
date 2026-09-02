# 可扩展硬件指标评估框架

仓库根目录只负责统一 CLI、协议、批量调度、完整性检查和结果渲染。LS、MIMO、
BP 是彼此隔离的模块，每个模块拥有自己的源码目录、Python 环境和 RTL 工作区。

| 模块 | 模块根目录 | 运行时仿真目录 |
|---|---|---|
| LS | `Generator/LSCE` | `Generator/LSCE/BehaviorialVerification/sim` |
| MIMO | `Generator/MIMODetector` | `Generator/MIMODetector/BehaviorialVerification/sim` |
| BP | `BPPredIter/BP_Evaluation` | `BPPredIter/BP_Evaluation/sim` |

## 统一入口

```bash
python -m metrics_framework <ls|mimo|bp> predict [配置编号或路径]
python -m metrics_framework <ls|mimo|bp> evaluate [配置编号或路径]
```

- `predict` 只执行预测，stdout 只包含 `prediction.json`。
- `evaluate` 执行预测与内部验证；验证完整时 stdout 只包含
  `evaluation.json`。
- 验证数据不足时 stdout 为空，stderr 给出原因并返回退出码 2。
- 批量 evaluate 是原子的，任一 case 失败时不输出部分 JSON。

框架本身是轻量安装，不安装三个模块的模型或 RTL 依赖：

```bash
python3.10 -m venv .venv-framework
. .venv-framework/bin/activate
python -m pip install -e .
```

模块解释器默认从各模块的 `.venv` 选择，也可以分别设置
`LS_METRICS_PYTHON`、`MIMO_METRICS_PYTHON` 和 `BP_METRICS_PYTHON`。

## 模块文档与历史证据

- LS 环境、独立 C++ 参考程序和 RTL 链：
  [`Generator/LSCE/README.md`](Generator/LSCE/README.md)
- 框架协议和新模块注册：
  [`metrics_framework/README.md`](metrics_framework/README.md)
- 三模块标准配置的历史波形、截图和结果：
  [`simulation_artifacts/README.md`](simulation_artifacts/README.md)

新模块只需实现内部 `predict`/`validate` adapter 并在
`metrics_framework/registry.json` 注册，不需要重新实现 CLI、批量、错误处理或
JSON 展示逻辑。
