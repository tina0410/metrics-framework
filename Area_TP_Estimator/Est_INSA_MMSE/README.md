# Est_INSA_MMSE
INSA MMSE 检测模块面积评估

## MIMO 单配置面积接口

`mimo_area_interface.py` 直接接收 `Generator/MIMODetector/configs` 使用的
JSON 配置，复用当前面积模型并根据 `INSA.xlsx` 的 `INSA`
工作表按全部结构参数匹配历史 DC 面积和综合时间：

```bash
python mimo_area_interface.py path/to/config_case1.json
```

Python 调用入口为 `evaluate_mimo_area(config_path)`。返回值中的
`predicted_area_um2` 和 `prediction_time_ms` 是本轮现场预测；
`actual_area_um2` 与 `synthesis_time_ms` 来自参考工作簿，
`actual_value_kind` 固定为 `historical_dc_reference`，不得解释为本轮综合结果。
若参考表存在结构参数和 DC 面积完全相同的重复测量，接口保留全部
`reference_excel_rows`，综合时间取这些历史运行的中位数；若面积不一致则拒绝返回。
