"""PUSCH CE end-to-end latency prediction and RTL comparison.

The prediction boundary is the rising edge which accepts ``start`` through
the first rising edge which asserts ``slot_ce_done``.  Coefficient SRAM load
time is deliberately outside that boundary; validation holds
``coeff_load_done`` high before accepting ``start``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import re
import sys
import time
from typing import Any, Mapping


DEFAULT_LATENCY_CASES = Path(__file__).resolve().parent / "tests" / "latency_cases.json"


@dataclass(frozen=True)
class LatencyRuntime:
    """Runtime protocol values selected inside a generated design range."""

    num_rbs: int
    num_symbols: int
    dmrs_type: int
    is_double_dmrs: bool
    dmrs_type_a_pos: str
    n_additional_dmrs: int
    clock_period_ns: float = 10.0


@dataclass(frozen=True)
class LatencyTiming:
    """Structural timing constants derived by the RTL generator."""

    rb_parallelism: int
    ti_re_parallelism: int
    early_ls_drain: int
    ti_pipeline_depth: int
    has_pre_fi_buf: bool
    fi_window_size: int
    fi_cycles_per_occ: int
    fi_cycles_per_occ_single: int


_DMRS_POSITIONS = {
    ("single", 0): ((range(4, 15), (0,)),),
    ("single", 1): (
        (range(4, 8), (0,)), (range(8, 10), (0, 7)),
        (range(10, 13), (0, 9)), (range(13, 15), (0, 11)),
    ),
    ("single", 2): (
        (range(4, 8), (0,)), (range(8, 10), (0, 7)),
        (range(10, 13), (0, 6, 9)), (range(13, 15), (0, 7, 11)),
    ),
    ("single", 3): (
        (range(4, 8), (0,)), (range(8, 10), (0, 7)),
        (range(10, 12), (0, 6, 9)), (range(12, 15), (0, 5, 8, 11)),
    ),
    ("double", 0): ((range(4, 15), (0,)),),
    ("double", 1): (
        (range(4, 10), (0,)), (range(10, 13), (0, 8)),
        (range(13, 15), (0, 10)),
    ),
}


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a positive integer") from error
    if not math.isfinite(numeric) or not numeric.is_integer() or numeric <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(numeric)


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a nonnegative integer")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a nonnegative integer") from error
    if not math.isfinite(numeric) or not numeric.is_integer() or numeric < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return int(numeric)


def resolve_dmrs_positions(runtime: LatencyRuntime) -> list[int]:
    """Resolve the same Type-A table used by ``v_pilot_symbol_detection``."""

    if runtime.dmrs_type not in (1, 2):
        raise ValueError("latency.runtime.dmrs_type must be 1 or 2")
    if runtime.dmrs_type_a_pos not in ("pos2", "pos3"):
        raise ValueError("latency.runtime.dmrs_typeA_pos must be pos2 or pos3")
    symbol_kind = "double" if runtime.is_double_dmrs else "single"
    entries = _DMRS_POSITIONS.get((symbol_kind, runtime.n_additional_dmrs), ())
    l0 = 2 if runtime.dmrs_type_a_pos == "pos2" else 3
    for durations, raw_positions in entries:
        if runtime.num_symbols in durations:
            return [l0 if position == 0 else position for position in raw_positions]
    raise ValueError(
        "no legal Type-A DMRS placement for "
        f"double={runtime.is_double_dmrs}, add={runtime.n_additional_dmrs}, "
        f"num_symbols={runtime.num_symbols}"
    )


def predict_from_terms(
    timing: LatencyTiming,
    runtime: LatencyRuntime,
) -> dict[str, Any]:
    """Predict latency using constants which correspond directly to RTL."""

    p = _positive_int(timing.rb_parallelism, "rb_parallelism")
    ti_re_parallelism = _positive_int(
        timing.ti_re_parallelism, "ti_re_parallelism"
    )
    if 12 % ti_re_parallelism:
        raise ValueError("ti_re_parallelism must divide 12")
    if not math.isfinite(runtime.clock_period_ns) or runtime.clock_period_ns <= 0:
        raise ValueError("latency.clock_period_ns must be greater than zero")

    positions = resolve_dmrs_positions(runtime)
    last_dmrs_symbol = max(positions) + int(runtime.is_double_dmrs)
    if last_dmrs_symbol >= runtime.num_symbols:
        raise ValueError("the last DMRS symbol is outside the PUSCH allocation")

    rb_beats = math.ceil(runtime.num_rbs / p)
    re_groups = 12 // ti_re_parallelism
    before_ti = (
        (last_dmrs_symbol + 1) * rb_beats
        + 1  # registered ctrl_sym_switch boundary
        + _positive_int(timing.early_ls_drain, "early_ls_drain")
    )
    ti_drain = max(_nonnegative_int(
        timing.ti_pipeline_depth, "ti_pipeline_depth"
    ) + 1, 2)

    if not timing.has_pre_fi_buf:
        branch = "post_fi"
        sweep_cycles = rb_beats * p * re_groups
        fi_cycles = 0
        window_count = 0
        cycles_per_window = 0
        ti_cycles = sweep_cycles + ti_drain
    else:
        window_size = _positive_int(timing.fi_window_size, "fi_window_size")
        if window_size % p:
            raise ValueError("fi_window_size must be divisible by rb_parallelism")
        window_count = math.ceil(runtime.num_rbs / window_size)
        occurrence_count = runtime.n_additional_dmrs + 1
        if runtime.is_double_dmrs:
            branch = "pre_fi"
            fi_per_occ = _positive_int(
                timing.fi_cycles_per_occ, "fi_cycles_per_occ"
            )
        else:
            branch = (
                "pre_fi_hybrid_single"
                if timing.fi_cycles_per_occ_single != timing.fi_cycles_per_occ
                else "pre_fi"
            )
            fi_per_occ = _positive_int(
                timing.fi_cycles_per_occ_single,
                "fi_cycles_per_occ_single",
            )
        sweep_cycles = window_size * re_groups
        fi_cycles = occurrence_count * fi_per_occ
        cycles_per_window = fi_cycles + sweep_cycles
        ti_cycles = window_count * cycles_per_window + ti_drain

    predicted_cycles = before_ti + ti_cycles
    return {
        "predicted_cycles": predicted_cycles,
        "predicted_time_ns": predicted_cycles * runtime.clock_period_ns,
        "formula_case": branch,
        "breakdown": {
            "rb_beats_per_symbol": rb_beats,
            "last_dmrs_symbol": last_dmrs_symbol,
            "cycles_before_ti": before_ti,
            "ti_sweep_cycles": sweep_cycles,
            "fi_cycles_per_window": fi_cycles,
            "fi_window_count": window_count,
            "cycles_per_window": cycles_per_window,
            "ti_drain_cycles": ti_drain,
            "ti_total_cycles": ti_cycles,
        },
    }


def runtime_from_config(config: Mapping[str, Any]) -> LatencyRuntime:
    section = config.get("latency")
    if not isinstance(section, Mapping):
        raise ValueError("latency must be an object")
    runtime = section.get("runtime")
    if not isinstance(runtime, Mapping):
        raise ValueError("latency.runtime must be an object")
    period = float(section.get("clock_period_ns", 10.0))
    return LatencyRuntime(
        num_rbs=_positive_int(runtime.get("num_RBs"), "latency.runtime.num_RBs"),
        num_symbols=_positive_int(
            runtime.get("num_symbols"), "latency.runtime.num_symbols"
        ),
        dmrs_type=_positive_int(
            runtime.get("dmrs_type"), "latency.runtime.dmrs_type"
        ),
        is_double_dmrs=bool(runtime.get("is_double_dmrs")),
        dmrs_type_a_pos=str(runtime.get("dmrs_typeA_pos")),
        n_additional_dmrs=_nonnegative_int(
            runtime.get("n_additional_dmrs"),
            "latency.runtime.n_additional_dmrs",
        ),
        clock_period_ns=period,
    )


def load_case_config(
    config_path: str | Path,
    latency_cases_path: str | Path = DEFAULT_LATENCY_CASES,
) -> dict[str, Any]:
    """Combine an area/generator case with its test-owned runtime selection."""

    path = Path(config_path).expanduser().resolve()
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    cases_path = Path(latency_cases_path).expanduser().resolve()
    cases = json.loads(cases_path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict) or not isinstance(cases, dict):
        raise ValueError("configuration and latency cases must be JSON objects")
    try:
        latency = cases[path.stem]
    except KeyError as error:
        raise LookupError(f"no latency runtime is defined for {path.stem}") from error
    if not isinstance(latency, dict):
        raise ValueError(f"latency runtime for {path.stem} must be an object")
    combined = dict(config)
    combined["latency"] = latency
    return combined


def _validate_runtime_for_build(
    config: Mapping[str, Any], runtime: LatencyRuntime
) -> None:
    protocol = config["protocol"]
    architecture = config["architecture"]
    rb_min, rb_max = map(int, protocol["num_RB_range"])
    sym_min, sym_max = map(int, protocol["num_symbols_range"])
    if not rb_min <= runtime.num_rbs <= rb_max:
        raise ValueError("latency runtime num_RBs is outside the generated range")
    if not sym_min <= runtime.num_symbols <= sym_max:
        raise ValueError("latency runtime num_symbols is outside the generated range")
    if protocol["dmrs_Type"] != "Hybrid" and runtime.dmrs_type != protocol["dmrs_Type"]:
        raise ValueError("latency runtime dmrs_type differs from the static build")
    if protocol["is_double_dmrs"] != "Hybrid" and (
        runtime.is_double_dmrs is not bool(protocol["is_double_dmrs"])
    ):
        raise ValueError("latency runtime double-DMRS mode differs from the static build")
    if protocol["dmrs_typeA_pos"] != "Hybrid" and (
        runtime.dmrs_type_a_pos != protocol["dmrs_typeA_pos"]
    ):
        raise ValueError("latency runtime Type-A position differs from the static build")
    if runtime.n_additional_dmrs not in protocol["additional_DMRS_range"]:
        raise ValueError("latency runtime additional-DMRS value is not generated")
    if protocol["is_ECP"] is True and runtime.num_symbols > 12:
        raise ValueError("extended CP permits at most 12 PUSCH symbols")
    if architecture["input_mode"] == "A" and (
        runtime.num_rbs % int(architecture["rb_parallelism"])
    ):
        raise ValueError("INPUT_MODE A requires num_RBs divisible by rb_parallelism")


def _parse_qutype(text: Any):
    match = re.fullmatch(
        r"\s*QuType\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(True|False)\s*\)\s*",
        str(text),
    )
    if match is None:
        raise ValueError(f"invalid QuType expression: {text!r}")
    from basic_modules.PyTU import QuType

    return QuType(int(match.group(1)), int(match.group(2)), match.group(3) == "True")


def timing_from_config(config: Mapping[str, Any]) -> LatencyTiming:
    """Ask the RTL generator for the exact structural timing constants."""

    protocol = config["protocol"]
    architecture = config["architecture"]
    quants = config["quantization"]
    from v_top import _prepare_top_context

    y = _parse_qutype(quants["Y"])
    h_ls = _parse_qutype(quants["H_LS"])
    h_fi = _parse_qutype(quants["H_FI"])
    fi_coeff = _parse_qutype(quants["FI_LMMSE_COEFF"])
    context = _prepare_top_context(
        pusch_params={
            "num_RB_range": protocol["num_RB_range"],
            "num_symbols_range": protocol["num_symbols_range"],
            "is_ECP": protocol["is_ECP"],
        },
        puschdmrs_params={
            "dmrs_Uplink": protocol["dmrs_Uplink"],
            "dmrs_Type": protocol["dmrs_Type"],
            "is_double_dmrs": protocol["is_double_dmrs"],
            "is_enhanced": protocol["is_enhanced"],
            "dmrs_typeA_pos": protocol["dmrs_typeA_pos"],
            "additional_DMRS_range": protocol["additional_DMRS_range"],
        },
        Y=y,
        RB_PARALLELISM=int(architecture["rb_parallelism"]),
        ANTENNA_PORTS=list(protocol["antenna_ports"]),
        H_interp_f_DWT=2 * h_fi.DWT,
        freq_interp_method=architecture["freq_interp"],
        time_interp_method=architecture["time_interp"],
        switchable_ports=bool(architecture["switchable_ports"]),
        INPUT_MODE=architecture["input_mode"],
        QU_H_LS=h_ls,
        LMMSE_INTERP_PARALLELISM=int(architecture["fi_lmmse_parallelism"]),
        TI_LMMSE_COEFF_SOURCE=architecture["ti_lmmse_coeff_source"],
        FI_LMMSE_COEFF_SOURCE=architecture["fi_lmmse_coeff_source"],
        FI_LMMSE_COEFF_DWT=fi_coeff.DWT,
        FI_LMMSE_REAL_COEFF=bool(architecture["fi_lmmse_real_coeff"]),
        FI_RE_PARALLELISM=int(architecture["fi_re_parallelism"]),
        TI_RE_PARALLELISM=int(architecture["ti_re_parallelism"]),
    )
    return LatencyTiming(
        rb_parallelism=int(architecture["rb_parallelism"]),
        ti_re_parallelism=int(architecture["ti_re_parallelism"]),
        early_ls_drain=int(context["EARLY_LS_DRAIN"]),
        ti_pipeline_depth=int(context["TI_PIPELINE_DEPTH"]),
        has_pre_fi_buf=bool(context["HAS_PRE_FI_BUF"]),
        fi_window_size=int(context["FI_WINDOW_SIZE"]),
        fi_cycles_per_occ=int(context["FI_CYCLES_PER_OCC"]),
        fi_cycles_per_occ_single=int(context["FI_CYCLES_PER_OCC_SINGLE"]),
    )


def predict_latency(config: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = runtime_from_config(config)
    _validate_runtime_for_build(config, runtime)
    timing = timing_from_config(config)
    result = predict_from_terms(timing, runtime)
    result["prediction_time_ms"] = (time.perf_counter() - started) * 1000.0
    result["runtime"] = asdict(runtime)
    result["timing"] = asdict(timing)
    return result


def evaluate_latency(
    config: Mapping[str, Any],
    *,
    actual_cycles: int | None = None,
    simulation_time_ms: float | None = None,
) -> dict[str, Any]:
    prediction = predict_latency(config)
    if actual_cycles is None:
        return {
            **prediction,
            "actual_cycles": None,
            "actual_time_ns": None,
            "error_percent": None,
            "simulation_time_ms": simulation_time_ms,
            "speedup": None,
        }
    actual = _positive_int(actual_cycles, "actual latency")
    predicted = int(prediction["predicted_cycles"])
    period = float(prediction["runtime"]["clock_period_ns"])
    prediction_time = float(prediction["prediction_time_ms"])
    return {
        **prediction,
        "actual_cycles": actual,
        "actual_time_ns": actual * period,
        "error_percent": abs(predicted - actual) / actual * 100.0,
        "simulation_time_ms": simulation_time_ms,
        "speedup": (
            simulation_time_ms / prediction_time
            if simulation_time_ms is not None and prediction_time > 0
            else None
        ),
    }


__all__ = [
    "LatencyRuntime",
    "LatencyTiming",
    "load_case_config",
    "evaluate_latency",
    "predict_from_terms",
    "predict_latency",
    "resolve_dmrs_positions",
    "runtime_from_config",
    "timing_from_config",
]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} CONFIG", file=sys.stderr)
        return 1
    try:
        path = Path(sys.argv[1]).expanduser().resolve()
        config = load_case_config(path)
        sys.stdout.write(json.dumps(predict_latency(config), ensure_ascii=False))
        return 0
    except (FileNotFoundError, KeyError, LookupError, RuntimeError, ValueError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
