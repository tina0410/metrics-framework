import json
from pathlib import Path

from metrics_framework.adapters.pusch_ce import validate_scaffold_config
from metrics_framework.core import Registry, resolve_configs


EXPECTED_SECTIONS = {
    "protocol",
    "architecture",
    "quantization",
    "arithmetic",
    "implementation",
    "area",
}


def test_pusch_ce_scaffold_is_registered_with_five_cases():
    spec = Registry().get("pusch_ce")
    assert spec.status == "registered"
    assert spec.default_cases == (1, 2, 3, 4, 5)
    assert spec.config_pattern == "config{case}.json"
    assert spec.adapter is not None and spec.adapter.is_file()
    assert spec.capabilities == {
        "area",
        "latency",
        "throughput",
        "hardware_complexity",
    }

    configs = resolve_configs(spec, None)
    assert len(configs) == 5
    for path in configs:
        config = json.loads(path.read_text(encoding="utf-8"))
        validate_scaffold_config(config)
        assert set(config) == EXPECTED_SECTIONS
        assert config["area"] == {
            "use_config_actual_area": False,
            "actual_area_um2": None,
            "use_config_actual_time": False,
            "actual_time_ms": None,
        }
