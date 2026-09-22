# PUSCH_CE metrics cases

These five inputs are the area-estimation baseline for the unified metrics
framework.  Each JSON contains only the TOP generation parameters consumed by
`Est_Top()` plus the same optional actual-area/time overrides used by MIMO.

| Metrics case | Area design | FI | TI | Actual TOP area (um^2) |
| --- | ---: | --- | --- | ---: |
| config1 | 1 | linear | nn | 2459651.869512 |
| config2 | 3 | nn | nn | 3039317.125335 |
| config3 | 12 | linear | lmmse | 9029318.125515 |
| config4 | 27 | linear | linear | 735939.116292 |
| config5 | 48 | nn | linear | 15405761.41958 |

When `area.use_config_actual_area` is false, the interface matches all TOP
generation parameters against `param.xlsx` and reads the matched row's `area`
value.  If `area.use_config_actual_area` is true, `area.actual_area_um2` is used
instead.  This is the same precedence as the MIMO area interface.

The area case JSON files remain limited to generator/area inputs. Runtime
points for latency live in `tests/latency_cases.json`; prediction and RTL
validation read the same entry and use the accepted-`start` through
`slot_ce_done` boundary:

```bash
python latency_interface.py cases/config1.json
python tests/validate_pusch_ce_latency.py cases/config1.json
```

Run both commands in the PUSCH_CE Python 3.13 environment. RTL validation also
requires Verilator, or select Icarus with `--simulator icarus`.

Implementation order after review:

1. Area prediction and workbook/JSON reference lookup.
2. Latency formula and RTL measurement (`start` to `slot_ce_done`).
3. Bit throughput prediction and RTL-derived throughput.
4. Hardware complexity in GE-cycles, derived consistently with other modules.
