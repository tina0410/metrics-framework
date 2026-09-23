# 可扩展硬件指标评估框架

仓库根目录负责统一 CLI、协议、批量调度、完整性检查和结果渲染。每个硬件模块保留
独立的源码目录、Python 环境和 RTL 工作区，避免模型、生成器和仿真依赖相互冲突。

## 模块与状态

| 模块 | 模块根目录 | 运行时仿真目录 | 统一指标状态 |
| --- | --- | --- | --- |
| LS | `Generator/LSCE` | `Generator/LSCE/BehaviorialVerification/sim` | `active` |
| MIMO | `Generator/MIMODetector` | `Generator/MIMODetector/BehaviorialVerification/sim` | `active` |
| BP | `BPPredIter/BP_Evaluation` | `BPPredIter/BP_Evaluation/sim` | `active` |
| ADD | `Generator/BasicModules/Add` | `Generator/BasicModules/Add/sim` | `active` |
| MUL | `Generator/BasicModules/Mul` | `Generator/BasicModules/Mul/sim` | `active` |
| PUSCH_CE (`ce`) | `Generator/PUSCH_CE` | `Generator/PUSCH_CE/tests/sim` | `active` |

`active` 模块可以直接使用统一 `predict/evaluate` 命令。PUSCH_CE 已完成面积、
延迟、有效 bit 吞吐率和 GE·cycles 硬件复杂度四项指标；命令使用简写 `ce`，
同时保留 `pusch_ce` 兼容名称。

## 统一入口

```bash
python -m metrics_framework <ls|mimo|bp|ce|add|mul> predict [配置编号或路径]
python -m metrics_framework <ls|mimo|bp|ce|add|mul> evaluate [配置编号或路径]
```

安装后也可使用：

```bash
metrics <ls|mimo|bp|ce|add|mul> predict [配置编号或路径]
metrics <ls|mimo|bp|ce|add|mul> evaluate [配置编号或路径]
```

- `predict` 只执行预测，stdout 只包含 `prediction.json` 内容。
- `evaluate` 执行预测和内部验证；验证完整时 stdout 只包含
  `evaluation.json` 内容。
- 验证数据不足时 stdout 为空，stderr 说明原因，退出码为 2。
- 批量 `evaluate` 是原子操作：任一 case 失败时不输出部分 JSON。
- `registered` 模块不会返回伪造指标，而是明确报告尚未开放统一评估。

## 环境设置

### 1. 框架环境 `.venv-framework`

该环境只运行统一 CLI 和调度代码，不安装各模块的模型或 RTL 依赖。
框架支持 Python 3.10 及以上。

Linux / WSL：

```bash
python3.10 -m venv .venv-framework
source .venv-framework/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell：

```powershell
py -3.10 -m venv .venv-framework
.\.venv-framework\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

不要把 PUSCH_CE 的 Verithon、cocotb、numpy/scipy 等依赖安装到
`.venv-framework`。统一框架通过独立子进程调用模块解释器。

### 2. PUSCH_CE 独立环境

PUSCH_CE 生成器和 TOP 仿真链按项目要求使用 **Python 3.13**。可以在
`.venv-framework` 仍处于激活状态时创建模块环境；下面的命令显式使用
Python 3.13，不会把依赖写入框架环境。

Linux / WSL：

```bash
python3.13 -m venv Generator/PUSCH_CE/.venv
Generator/PUSCH_CE/.venv/bin/python -m pip install --upgrade pip
Generator/PUSCH_CE/.venv/bin/python -m pip install -r Generator/PUSCH_CE/requirements.txt
export PUSCH_CE_METRICS_PYTHON="$PWD/Generator/PUSCH_CE/.venv/bin/python"
```

Windows PowerShell：

```powershell
py -3.13 -m venv Generator\PUSCH_CE\.venv
.\Generator\PUSCH_CE\.venv\Scripts\python.exe -m pip install --upgrade pip
.\Generator\PUSCH_CE\.venv\Scripts\python.exe -m pip install -r Generator\PUSCH_CE\requirements.txt
$env:PUSCH_CE_METRICS_PYTHON = "$PWD\Generator\PUSCH_CE\.venv\Scripts\python.exe"
```

`PUSCH_CE_METRICS_PYTHON` 是统一框架的解释器覆盖变量。未设置时，框架会
默认查找 `Generator/PUSCH_CE/.venv/bin/python`（Windows 为
`Generator\PUSCH_CE\.venv\Scripts\python.exe`）。

PUSCH_CE 的 Python 依赖统一记录在
[`Generator/PUSCH_CE/requirements.txt`](Generator/PUSCH_CE/requirements.txt)。RTL 仿真还需
系统工具：

```bash
# Debian / Ubuntu / WSL
sudo apt update
sudo apt install -y verilator yosys
verilator --version
yosys -V
```

Verilator 和 Yosys 不是 Python 包，不能通过 `pip` 写入任何虚拟环境。

### 3. 其他模块解释器

各模块默认使用自身根目录下的 `.venv`，也可分别设置：

```text
LS_METRICS_PYTHON
MIMO_METRICS_PYTHON
BP_METRICS_PYTHON
ADD_METRICS_PYTHON
MUL_METRICS_PYTHON
PUSCH_CE_METRICS_PYTHON
```

## PUSCH_CE 命令

统一预测和评估：

```bash
python -m metrics_framework ce predict 1
python -m metrics_framework ce evaluate 1
```

也可通过以下内部单项入口排查各子链。

延迟预测：

```bash
Generator/PUSCH_CE/.venv/bin/python \
  Generator/PUSCH_CE/latency_interface.py \
  Generator/PUSCH_CE/cases/config1.json
```

延迟 RTL 验证（从 `start` 被接受到 `slot_ce_done` 拉高）：

```bash
Generator/PUSCH_CE/.venv/bin/python \
  Generator/PUSCH_CE/tests/validate_pusch_ce_latency.py \
  Generator/PUSCH_CE/cases/config1.json
```

面积预测：

```bash
Generator/PUSCH_CE/.venv/bin/python \
  Area_TP_Estimator/PUSCH_Est_pack/pusch_ce_area_interface.py \
  predict Generator/PUSCH_CE/cases/config1.json
```

5 个面积 case 保持只包含生成器/面积模型输入；延迟运行时点独立保存在
`Generator/PUSCH_CE/tests/latency_cases.json`，预测和 RTL 验证共用同一份数据。

Windows PowerShell 执行上述命令时，将解释器路径替换为：

```text
.\Generator\PUSCH_CE\.venv\Scripts\python.exe
```

## 测试

框架回归：

```bash
python -m pytest test_metrics_framework.py -q
```

PUSCH_CE 四项指标接口回归：

```bash
python -m pytest \
  test_pusch_ce_framework.py \
  test_pusch_ce_latency.py \
  test_pusch_ce_throughput.py \
  test_pusch_ce_hardware_complexity.py \
  Area_TP_Estimator/PUSCH_Est_pack/test_pusch_ce_area_interface.py \
  -q
```

## 模块文档与历史证据

- PUSCH_CE 生成器、Verilator/Yosys 和 TOP 测试：
  [`Generator/PUSCH_CE/README.md`](Generator/PUSCH_CE/README.md)
- PUSCH_CE 五个指标 case：
  [`Generator/PUSCH_CE/cases/README.md`](Generator/PUSCH_CE/cases/README.md)
- LS 环境、独立 C++ 参考程序和 RTL 链：
  [`Generator/LSCE/README.md`](Generator/LSCE/README.md)
- 框架协议和新模块注册：
  [`metrics_framework/README.md`](metrics_framework/README.md)
- 标准配置的历史波形、截图和结果：
  [`simulation_artifacts/README.md`](simulation_artifacts/README.md)

新模块只需实现内部 `predict`/`validate` adapter，并在
`metrics_framework/registry.json` 注册，不需要重新实现 CLI、批量调度、错误处理或
JSON 展示逻辑。
