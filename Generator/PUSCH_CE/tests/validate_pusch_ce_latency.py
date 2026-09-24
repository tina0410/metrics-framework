#!/usr/bin/env python3
"""Generate PUSCH CE RTL and measure latency plus bit throughput."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import xml.etree.ElementTree as ET


PUSCH_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
if str(PUSCH_ROOT) not in sys.path:
    sys.path.insert(0, str(PUSCH_ROOT))


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("configuration must be a JSON object")
    return value


def _restore_mode(container, dotted_name: str):
    family, member = dotted_name.split(".", 1)
    return getattr(getattr(container, family), member)


def _semantic_config(config: dict):
    from basic_modules.PyTU import OfMode, QuMode
    from latency_interface import _parse_qutype
    from top_api import (
        ArchitectureConfig,
        ArithmeticConfig,
        ImplementationConfig,
        ProtocolSpec,
        QuantKey,
    )

    p = config["protocol"]
    a = config["architecture"]
    q = config["quantization"]
    implementation = config["implementation"]
    protocol = ProtocolSpec(
        pusch={
            "num_RB_range": p["num_RB_range"],
            "num_symbols_range": p["num_symbols_range"],
            "is_ECP": p["is_ECP"],
        },
        dmrs={
            "dmrs_Uplink": p["dmrs_Uplink"],
            "dmrs_Type": p["dmrs_Type"],
            "is_double_dmrs": p["is_double_dmrs"],
            "is_enhanced": p["is_enhanced"],
            "dmrs_typeA_pos": p["dmrs_typeA_pos"],
            "additional_DMRS_range": p["additional_DMRS_range"],
        },
        antenna_ports=p["antenna_ports"],
        slot_index_format=_parse_qutype(p["slot_index_format"]),
    )
    architecture = ArchitectureConfig(
        rb_parallelism=int(a["rb_parallelism"]),
        fi_lmmse_parallelism=int(a["fi_lmmse_parallelism"]),
        freq_interp=a["freq_interp"],
        time_interp=a["time_interp"],
        input_mode=a["input_mode"],
        switchable_ports=bool(a["switchable_ports"]),
        fi_re_parallelism=int(a["fi_re_parallelism"]),
        ti_re_parallelism=int(a["ti_re_parallelism"]),
        fi_lmmse_real_coeff=bool(a["fi_lmmse_real_coeff"]),
        ti_lmmse_real_coeff=bool(a["ti_lmmse_real_coeff"]),
        fi_lmmse_coeff_source=a["fi_lmmse_coeff_source"],
        ti_lmmse_coeff_source=a["ti_lmmse_coeff_source"],
    )
    quants = {key: _parse_qutype(q[key.value]) for key in QuantKey}
    arithmetic = ArithmeticConfig(
        ls_quant_mode=_restore_mode(QuMode, config["arithmetic"]["ls_quant_mode"]),
        ls_overflow_mode=_restore_mode(
            OfMode, config["arithmetic"]["ls_overflow_mode"]
        ),
    )
    physical = ImplementationConfig(**implementation)
    return protocol, architecture, quants, arithmetic, physical


def _load_generators():
    """Import PyTV generators without exposing this script's CLI arguments."""

    original_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        from pytv.ModuleLoader import moduleloader
        from top_api import ModuleTOP
    finally:
        sys.argv = original_argv
    return moduleloader, ModuleTOP


def _generate(config: dict, output_dir: Path) -> list[Path]:
    moduleloader, ModuleTOP = _load_generators()

    output_dir.mkdir(parents=True, exist_ok=True)
    moduleloader.reset()
    moduleloader.set_root_dir(str(output_dir))
    moduleloader.set_language_mode("verilog")
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()
    moduleloader.set_debug_mode(False)
    with contextlib.redirect_stdout(io.StringIO()):
        ModuleTOP(*_semantic_config(config))
    sources = sorted(output_dir.glob("*.v"))
    if not sources:
        raise RuntimeError("PUSCH CE generator produced no Verilog")
    return sources


def _find_top(sources: list[Path]) -> str:
    candidates = [path.stem for path in sources if "TOP" in path.stem.upper()]
    if not candidates:
        raise RuntimeError("generated PUSCH CE TOP module was not found")
    return candidates[0]


def simulate(config_path: Path, *, simulator: str, build_root: Path) -> dict:
    from cocotb_tools.runner import get_runner
    from latency_interface import load_case_config

    config = load_case_config(config_path)
    case_root = build_root / config_path.stem
    rtl_root = case_root / "rtl"
    if rtl_root.exists():
        shutil.rmtree(rtl_root)
    started = time.perf_counter()
    sources = _generate(config, rtl_root)
    top = _find_top(sources)
    result_path = case_root / "latency_result.json"
    results_xml = case_root / "results.xml"
    runner = get_runner(simulator)
    build_args = ["--timing", "-Wno-fatal"] if simulator == "verilator" else []
    runner.build(
        sources=sources,
        hdl_toplevel=top,
        build_dir=case_root / "sim_build",
        always=True,
        build_args=build_args,
    )
    environment = {
        "PUSCH_CE_LATENCY_CONFIG_JSON": json.dumps(config),
        "PUSCH_CE_LATENCY_RESULT": str(result_path),
    }
    runner.test(
        hdl_toplevel=top,
        test_module="testbench_latency",
        test_dir=TEST_ROOT,
        build_dir=case_root / "sim_build",
        results_xml=str(results_xml),
        extra_env=environment,
    )
    root = ET.parse(results_xml).getroot()
    if root.findall(".//failure") or root.findall(".//error"):
        raise RuntimeError(f"cocotb latency probe failed; see {results_xml}")
    rtl_result = _load(result_path)
    simulation_time_ms = (time.perf_counter() - started) * 1000.0
    from latency_interface import evaluate_latency
    from throughput_interface import evaluate_throughput

    evaluation = evaluate_latency(
        config,
        actual_cycles=int(rtl_result["actual_cycles"]),
        simulation_time_ms=simulation_time_ms,
    )
    throughput = evaluate_throughput(
        config,
        actual_interval_cycles=int(rtl_result["throughput_interval_cycles"]),
        actual_output_bits=int(rtl_result["throughput_output_bits"]),
        simulation_time_ms=simulation_time_ms,
    )
    return {
        "latency": evaluation,
        "throughput": throughput,
        "rtl": {
            **rtl_result,
            "simulation_time_ms": simulation_time_ms,
            "result_path": str(result_path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--simulator", default=os.environ.get("SIM", "verilator"))
    parser.add_argument("--build-root", type=Path, default=TEST_ROOT / "sim")
    args = parser.parse_args()
    try:
        result = simulate(
            args.config.expanduser().resolve(),
            simulator=args.simulator,
            build_root=args.build_root.expanduser().resolve(),
        )
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
        return 0
    except (FileNotFoundError, LookupError, RuntimeError, ValueError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
