# BP 指标评估简明说明

BP评估已经接入PolarDecoder真实RTL延迟。最终 `bp_metrics.json` 中的延迟仿真结果来自 `sim_latency_cycles`；C++迭代次数只记录在“round前迭代次数”中。

当前版本只保证Ubuntu环境和 `TypeI` 架构。

## 1. 修改配置文件

默认配置文件位于 `BPPredIter/BP_Evaluation/config/`：

- `config1.json` 至 `config5.json` 是默认批量配置。
- 可以继续增加 `config6.json`、`config7.json` 等文件。
- 用户配置必须使用小写下划线字段；不要把程序生成的标题式 `rtl_config.json` 直接作为用户配置。

配置示例：

```json
{
  "decoder": {
    "hardware_architecture": "TypeI",
    "decoding_algorithm": "MS",
    "code_length": 256,
    "parallelism": 16,
    "data_width": 5,
    "code_rate": 0.5,
    "ebn0_db": 10.0
  },
  "clock": {
    "period_ns": 20.0
  },
  "area": {
    "use_config_actual_area": false,
    "actual_area_um2": null,
    "synthesis_time_ms": null
  },
  "flow": {
    "run_simulation": true,
    "output_dir": "../evaluation_output/config6"
  }
}
```

主要配置项：

- `run_simulation`：旧入口是否运行C++定点仿真和RTL正确性验证；统一入口由 `predict/evaluate` 模式决定。
- `clock.period_ns`：时钟周期，标准配置统一为 `20.0 ns`。
- `parallelism`：并行度 `M`，会改变真实RTL延迟；要求 `M <= N`、`N % M == 0`，建议使用2的幂。
- `use_config_actual_area=false`：从面积工作簿精确匹配DC综合面积和综合时间。
- `use_config_actual_area=true`：使用配置中的 `actual_area_um2`，该值必须大于0；此时跳过面积表匹配。
- `synthesis_time_ms`：手工真实面积模式下可选填写的综合时间，单位为毫秒；填写正数后计算速度提升倍数，留为 `null` 时综合时间和速度提升倍数均为 `null`。

面积预测始终由现有 `Esttop()` 计算，并记录本次预测时间。面积表模式支持：

```text
Area_TP_Estimator/Est_Polar_BP_Decoder/area.xlsx
Area_TP_Estimator/Est_Polar_BP_Decoder/BP.xlsx
```

worksheet可以是 `ALL` 或 `BP`，按 `Architecture/Algorithm/N/M/Data Width` 精确匹配。

### 当前输入限制

`ebn0_db` 和各case的 `MS/SMS` 暂时保持原配置，不作为当前版本的可调参数。

`N/K/Data Width` 只能映射现有 `input_files/` 中的7组基准输入，其中 `K = round(N × code_rate)`：

| N | K | Data Width | INTDWT | FRACDWT |
|---:|---:|---:|---:|---:|
| 1024 | 512 | 5 | 3 | 1 |
| 1024 | 512 | 7 | 4 | 2 |
| 1024 | 512 | 8 | 4 | 3 |
| 1024 | 512 | 12 | 3 | 8 |
| 256 | 128 | 5 | 3 | 1 |
| 256 | 16 | 5 | 3 | 1 |
| 64 | 32 | 5 | 3 | 1 |

其他组合不会自动生成输入。例如 `N=4、K=2、Data Width=2` 当前不可运行。

## 2. Ubuntu下配置uv环境

进入项目目录：

```bash
cd ~/Desktop/mjj/BPPredIter/BP_Evaluation
```

创建虚拟环境并安装依赖：

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
```

检查Python依赖：

```bash
python -c "import numpy, pandas, sklearn, openpyxl; print('dependencies OK')"
```

正式仿真需要Clang 20/C++23和Icarus Verilog；查看波形可安装GTKWave。

## 3. 运行主函数

不指定参数时，默认依次运行 `config1.json` 至 `config5.json`：

```bash
uv run python evaluate_bp.py
```

指定任意正整数配置编号，只运行对应配置：

```bash
uv run python evaluate_bp.py 3   # config/config3.json
uv run python evaluate_bp.py 6   # config/config6.json
```

也可以直接指定配置文件：

```bash
uv run python evaluate_bp.py config/config6.json
```

数字简写只负责定位 `config/configN.json`，对应文件必须存在。

单case运行只更新自身结果，不删除其他case。默认输出结构：

```text
BPPredIter/BP_Evaluation/
├── evaluation_output/configN/bp_metrics.json
└── sim/configN/
    ├── config_snapshot.json
    ├── rtl_config.json
    ├── latency_output.txt
    ├── simulation_result.json
    ├── simulation.log
    ├── wave.vcd
    └── workspace/
```

`bp_metrics.json` 不输出“仿真证据”和“真实值来源”字段；`simulation_result.json` 等仿真材料仍作为独立文件保留。

查看某个配置的波形：

```bash
gtkwave sim/config3/wave.vcd
```
