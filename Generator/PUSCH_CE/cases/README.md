# PUSCH_CE metrics cases

These five inputs are the area-estimation baseline for the unified metrics
framework.  Each JSON contains only the TOP generation parameters consumed by
`Est_Top()` plus the same optional actual-area/time overrides used by MIMO.

| Metrics case | Reference build ID | FI | TI | Runtime RBs | Predicted latency | Actual TOP area |
| --- | --- | --- | --- | ---: | ---: | --- |
| config1 | `127987b564a4` | nn | nn | 24 | 388 cycles | pending |
| config2 | `2106b2c89b5e` | linear | linear | 24 | 388 cycles | pending |
| config3 | `e1ba44dfdb4c` | lmmse | lmmse | 24 | 762 cycles | pending |
| config4 | `c5ee8f1109c4` | nn | lmmse | 24 | 390 cycles | pending |
| config5 | `a630789da489` | lmmse | linear | 24 | 664 cycles | pending |

`area.source_build_id` and `area.source_case_id` preserve the source selection
from `explore_20260809_large.json`. Actual areas remain unset until the updated
build-ID-to-area results are supplied. Once populated,
`area.use_config_actual_area` is set to true and `area.actual_area_um2` becomes
the validation reference.

The area case JSON files remain limited to generator/area inputs. Runtime
points for latency and throughput live in `tests/latency_cases.json`.
Latency uses the accepted-`start` through first `slot_ce_done` boundary.
Throughput counts useful complex `H_TI` bits observed under RTL
`ti_data_valid` and divides one slot's bits by the interval between two
adjacent `slot_ce_done` pulses:

```bash
python latency_interface.py cases/config1.json
python throughput_interface.py cases/config1.json
python tests/validate_pusch_ce_latency.py cases/config1.json --simulator verilator
```

Run both commands in the PUSCH_CE Python 3.13 environment on Ubuntu. RTL
validation uses Verilator; the unified `ce evaluate` adapter explicitly selects
it and does not use Icarus/iverilog.

Implementation order after review:

1. Area prediction and workbook/JSON reference lookup.
2. Latency formula and RTL measurement (`start` to `slot_ce_done`).
3. Bit throughput prediction and RTL-derived throughput.
4. Hardware complexity in GE-cycles, derived consistently with other modules.

Hardware complexity uses the same definition and 65 nm standard-cell source
as LS, MIMO, and BP:

```text
GE-cycles = area_um2 / area(LVT_NAND2HDV0) * latency_cycles
```

The repository's reference NAND2 area is 1.12 um2. Prediction combines the
predicted area and latency; validation combines the workbook/JSON area and RTL
latency. No additional case input or independent RTL run is required.
