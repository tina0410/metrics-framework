"""Generate pipelined and combinational ADD RTL for timing verification."""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[2]
PYTV_ROOT = PROJECT_ROOT / "Generator" / "LSCE" / "BehaviorialVerification"
DESIGNS_ROOT = ROOT / "designs"
sys.path[:0] = [str(PYTV_ROOT), str(DESIGNS_ROOT)]

# The bundled PyTV version parses argv while being imported.  Hide this
# wrapper's positional arguments from it, then restore them for our CLI.
_wrapper_argv = sys.argv[:]
try:
    sys.argv = [sys.argv[0]]
    from Add import ModuleAdd  # noqa: E402
    from PyTU import QuType  # noqa: E402
    from pytv.ModuleLoader import moduleloader  # noqa: E402
finally:
    sys.argv = _wrapper_argv


def _qu_type(config: dict, name: str) -> QuType:
    value = config[name]
    return QuType(
        int(value["bitwidth"]),
        int(value["fractional_width"]),
        bool(value["signed"]),
    )


def generate(config_path: Path, rtl_dir: Path) -> dict[str, object]:
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    rtl_dir.mkdir(parents=True, exist_ok=True)
    for path in rtl_dir.glob("*.v"):
        path.unlink()

    qu_in_1 = _qu_type(config, "input_1")
    qu_in_2 = _qu_type(config, "input_2")
    qu_out = _qu_type(config, "output")
    n_pipeline = int(config["n_pipeline"])
    if_rst_n = config.get("if_rst_n", False)

    moduleloader.reset()
    moduleloader.set_language_mode("VERILOG")
    moduleloader.set_root_dir(str(rtl_dir))
    moduleloader.set_naming_mode("SEQUENTIAL")
    moduleloader.disEnableWarning()
    with contextlib.redirect_stdout(sys.stderr):
        ModuleAdd(
            QU_IN_1=qu_in_1,
            QU_IN_2=qu_in_2,
            QU_OUT=qu_out,
            N_PIPELINES=n_pipeline,
            IF_RST_N=if_rst_n,
        )
        pipelined = sorted(rtl_dir.glob("Add*.v"))[-1]
        ModuleAdd(
            QU_IN_1=qu_in_1,
            QU_IN_2=qu_in_2,
            QU_OUT=qu_out,
            N_PIPELINES=0,
            IF_RST_N=False,
        )
        combinational = sorted(rtl_dir.glob("Add*.v"))[-1]

    if pipelined == combinational:
        raise RuntimeError("PyTV did not generate distinct ADD reference modules")
    result = {
        "pipelined_top": pipelined.stem,
        "combinational_top": combinational.stem,
        "rtl_files": [str(path) for path in sorted(rtl_dir.glob("*.v"))],
    }
    (rtl_dir / "rtl_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: generate_add_rtl.py CONFIG RTL_DIR", file=sys.stderr)
        raise SystemExit(1)
    try:
        generate(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(2) from error
