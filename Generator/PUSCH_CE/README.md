# 5G NR PUSCH Channel Estimator — RTL Generator & TOP Test Suite

This directory is a self-contained delivery of the **TOP RTL generator** and
its **end-to-end bit-exact test suite**. It reproduces, in a clean tree, the
complete "generate → lint → compile → simulate → compare against the C model"
flow.

## 0. Environment

Python 3.13. All Python dependencies are declared in
[`requirements.txt`](requirements.txt); install them into a dedicated
environment and run everything from **this directory** inside it:

```bash
conda create -n pytv python=3.13
conda run -n pytv pip install -r requirements.txt
```

| Package | Purpose |
| --- | --- |
| numpy, scipy | numerical / coefficient generation |
| verithon | Verilog emission (provides the `pytv` import package) |
| rich | test dashboard / structured logging |
| pytest, pytest-xdist | test runner |
| cocotb, cocotb-test | simulator bridge |
| typing_extensions | `@override` used by the TOP runner |

### Verilator

`requirements.txt` does **not** cover Verilator — it is a system-level
simulator that pip cannot install. The TOP test suite uses it as the default
simulator, so install it separately.

**Debian / Ubuntu (apt):**

```bash
sudo apt update
sudo apt install -y verilator
verilator --version   # >= 5.0 recommended
```

**Source install (any Linux / WSL, latest release):**

```bash
sudo apt install -y make autoconf flex bison  # build deps
git clone https://github.com/verilator/verilator
cd verilator
autoconf && ./configure && make -j$(nproc)
sudo make install
verilator --version
```

**macOS (Homebrew):**

```bash
brew install verilator
```

After installing, confirm cocotb can reach it:

```bash
conda run -n pytv python -c "import cocotb_tools.runner; print('cocotb OK')"
```

The TOP suite runs a **Yosys lint gate** before simulation (it fails the
build when `yosys` is absent) and then compiles/simulates with **Verilator** by
default.

**Yosys** (lint gate) — Debian/Ubuntu:

```bash
sudo apt install -y yosys
```

macOS: `brew install yosys`. It can be disabled per run with `TOP_SKIP_LINT=1`,
but that is meant for debugging, not normal use.

**Verilator** (simulator) is required for the smoke/regression/explore layers.

## 1. Generated-files directory

Generated RTL, lint reports, simulator builds, and cocotb XML are written to a
self-contained output root — **`./generated/`** by default. No external mount
(e.g. `/mnt/g`) or environment variable is required for the delivered tree to
run.

The default is declared in [`tests/framework/constants.py`](tests/framework/constants.py)
as `OUTPUT_ROOT`, and `generated_root.py` reads it as its default. Override it
without touching the sources:

```bash
# per pytest invocation
conda run -n pytv pytest tests/suites/top/runner.py -m smoke -v \
  --top-build-root /your/output/path

# process-wide (pytest, audit, and manual generation share this)
export PHY_PUSCH_GENERATED_ROOT=/your/output/path
```

The output root must be writable; generation aborts before starting otherwise
(there is no repository or `/tmp` fallback).

## 2. Manual TOP generation

`ModuleTOP` in [`top_api.py`](top_api.py) accepts five semantic inputs:

| Object | Content |
| --- | --- |
| `ProtocolSpec` | protocol capability range: `pusch` (RB/symbol count range, ECP), `dmrs` (Type 1/2/Hybrid etc.), antenna-port set, slot-index format |
| `ArchitectureConfig` | architecture: RB parallelism, FI/TI algorithm (`nn`/`linear`/`lmmse`), LMMSE parallelism, RE parallelism, coeff source ROM/SRAM, input mode A/B, switchable ports |
| `quants` | quantisation width dict — exactly 6 `QuantKey`s: `Y`, `H_LS`, `H_FI`, `H_TI`, `FI_LMMSE_COEFF`, `TI_LMMSE_COEFF` |
| `ArithmeticConfig` | LS rounding/overflow modes (`QuMode` / `OfMode`) |
| `ImplementationConfig` | LMMSE coeff-generation parameters (tau_rms, SNR, channel model, SCS, …), SRAM macro config, observation layouts |

The supported parameter values and ranges are listed below. The RB and symbol
count limits reflect both the protocol capability currently supported by this
project and its regression-tested boundaries. For some fields, `top_api.py`
only validates the type, positivity, or ordering; values outside the ranges
below have not been validated by the delivered test suite.

| Object | Parameter | Configurable values/range | Constraints / notes |
| --- | --- | --- | --- |
| `ProtocolSpec.pusch` | `num_RB_range` | Two-integer range `(min, max)`, `1 <= min <= max <= 273` | Selects the RB-count range available at runtime after generation. With `input_mode="A"`, the runtime RB count must also be divisible by `rb_parallelism`. |
| `ProtocolSpec.pusch` | `num_symbols_range` | Two-integer range `(min, max)`, `4 <= min <= max <= 14` | The ECP branch supports at most 12 symbols, so `max <= 12` is required when ECP is enabled. |
| `ProtocolSpec.pusch` | `is_ECP` | `False`, `True`, `"Hybrid"` | `"Hybrid"` generates both normal-CP and ECP runtime branches. |
| `ProtocolSpec.dmrs` | `dmrs_Uplink` | `True` | The current PUSCH TOP flow supports uplink DMRS only. |
| `ProtocolSpec.dmrs` | `dmrs_Type` | `1`, `2`, `"Hybrid"` | `"Hybrid"` generates both Type 1 and Type 2 branches. |
| `ProtocolSpec.dmrs` | `is_double_dmrs` | `False`, `True`, `"Hybrid"` | Double-symbol DMRS supports at most one additional DMRS occasion. |
| `ProtocolSpec.dmrs` | `is_enhanced` | `False`, `True`, `"Hybrid"` | Controls generation of the enhanced-DMRS branch. |
| `ProtocolSpec.dmrs` | `dmrs_typeA_pos` | `"pos2"`, `"pos3"`, `"Hybrid"` | Selects the Type-A front-loaded DMRS position `l0=2/3`. |
| `ProtocolSpec.dmrs` | `additional_DMRS_range` | A non-empty subset of `{0,1,2,3}`, for example `[0]` or `[0,1,2]` | Multiple values are runtime-selectable. A double-symbol DMRS branch may use only `0` or `1`. |
| `ProtocolSpec` | `antenna_ports` | Non-empty sequence of unique integers from `0..23`, up to 24 ports | DMRS Type 1 supports ports `0..15` only. Other port combinations must also satisfy TS 38.211 Section 6.4.1.1.1. |
| `ProtocolSpec` | `slot_index_format` | `QuType(DWT, 0, False)`, `DWT >= 1` | Unsigned integer format representing slot indices `0..2^DWT-1`. |
| `ArchitectureConfig` | `rb_parallelism` | Positive integer | RB parallelism. With `input_mode="A"`, the runtime RB count must be an integer multiple of this value. |
| `ArchitectureConfig` | `fi_lmmse_parallelism` | Positive integer, `>= rb_parallelism` | Must be divisible by `rb_parallelism`. |
| `ArchitectureConfig` | `freq_interp` | `"nn"`, `"linear"`, `"lmmse"` | Frequency-domain interpolation algorithm. |
| `ArchitectureConfig` | `time_interp` | `"nn"`, `"linear"`, `"lmmse"` | Time-domain interpolation algorithm. |
| `ArchitectureConfig` | `input_mode` | `"A"`, `"B"` | Default: `"A"`. |
| `ArchitectureConfig` | `switchable_ports` | `False`, `True` | When `False`, runtime selection cannot choose a subset of the generated antenna-port set. |
| `ArchitectureConfig` | `fi_re_parallelism` | `1`, `2`, `3`, `4`, `6`, `12` | Must divide the 12 REs in each RB. Default: `12`. |
| `ArchitectureConfig` | `ti_re_parallelism` | `1`, `2`, `3`, `4`, `6`, `12` | Must divide the 12 REs in each RB. Default: `3`. |
| `ArchitectureConfig` | `fi_lmmse_real_coeff` | `False`, `True` | Whether frequency-domain LMMSE coefficients are real-valued. Default: `True`. |
| `ArchitectureConfig` | `ti_lmmse_real_coeff` | `False`, `True` | Whether time-domain LMMSE coefficients are real-valued. Default: `True`. |
| `ArchitectureConfig` | `fi_lmmse_coeff_source` | `"ROM"`, `"SRAM"` | Frequency-domain LMMSE coefficient source. Default: `"ROM"`. |
| `ArchitectureConfig` | `ti_lmmse_coeff_source` | `"ROM"`, `"SRAM"` | Time-domain LMMSE coefficient source. Default: `"ROM"`. |
| `quants` | `QuantKey.Y` | `QuType(DWT, FRAC, IF_SIGNED)` | `DWT` is a positive integer, `0 <= FRAC <= DWT`, and `IF_SIGNED` is Boolean. |
| `quants` | `QuantKey.H_LS` | `QuType(DWT, FRAC, IF_SIGNED)` | Same constraints as above; format of one real or imaginary component of the LS channel estimate. |
| `quants` | `QuantKey.H_FI` | `QuType(DWT, FRAC, IF_SIGNED)` | Same constraints as above; format of one real or imaginary component after frequency interpolation. |
| `quants` | `QuantKey.H_TI` | `QuType(DWT, FRAC, IF_SIGNED)` | Same constraints as above; format of one real or imaginary component after time interpolation. |
| `quants` | `QuantKey.FI_LMMSE_COEFF` | `QuType(DWT, FRAC, IF_SIGNED)` | Same constraints as above; the format must represent the generated frequency-domain LMMSE coefficient values. |
| `quants` | `QuantKey.TI_LMMSE_COEFF` | `QuType(DWT, FRAC, IF_SIGNED)` | Same constraints as above; the format must represent the generated time-domain LMMSE coefficient values. |
| `ArithmeticConfig` | `ls_quant_mode` | `QuMode.TRN.TCPL`, `QuMode.TRN.SMGN`, `QuMode.RND.POS_INF`, `QuMode.RND.NEG_INF`, `QuMode.RND.ZERO`, `QuMode.RND.INF`, `QuMode.RND.CONV` | Default: `QuMode.TRN.TCPL`. |
| `ArithmeticConfig` | `ls_overflow_mode` | `OfMode.WRP.TCPL`, `OfMode.SAT.TCPL`, `OfMode.SAT.SMGN`, `OfMode.SAT.ZERO` | Default: `OfMode.WRP.TCPL`. |
| `ImplementationConfig` | `ti_lmmse_f_d_norm` | Finite positive floating-point value | Normalized Doppler frequency `f_D * T_sym`. Default: `0.01`. |
| `ImplementationConfig` | `ti_lmmse_w_coeffs` | `None` or a two-dimensional numeric matrix | With `None`, coefficients are generated from the Jakes model. A custom matrix applies only to one runtime configuration and must have shape `num_symbols x num_occasions`. |
| `ImplementationConfig` | `fi_lmmse_tau_rms` | Finite positive floating-point value | Normalized RMS delay spread for the sinc model when `fi_lmmse_channel_model=None`. Default: `3.0`. |
| `ImplementationConfig` | `fi_lmmse_snr_linear` | Finite positive floating-point value | Linear SNR, not dB. Default: `100.0`. |
| `ImplementationConfig` | `fi_lmmse_channel_model` | `None`, `"sinc"`, `"TDL-A"`, `"TDL-B"`, `"TDL-C"`, `"TDL-D"`, `"TDL-E"` | `None` uses `fi_lmmse_tau_rms`. Default: `"TDL-C"`. |
| `ImplementationConfig` | `fi_lmmse_delay_spread` | Finite positive floating-point value, in seconds | Used by the TDL and `sinc` channel models. Default: `200e-9`. |
| `ImplementationConfig` | `fi_lmmse_scs` | Finite positive floating-point value, in Hz | Subcarrier spacing. Default: `30e3`. |
| `ImplementationConfig` | `sram_macro` | `None` in this delivery | Reserved for Memory Compiler integration. |
| `ImplementationConfig` | `production_observation_layouts` | `None` in this delivery | Reserved for Architecture Selector integration; the associated observation modules are intentionally not included. |

Reference script template:

```python
import sys
from pathlib import Path

# PyTV parses sys.argv on import — isolate it first, then restore.
_real_argv = sys.argv[:]
sys.argv = [sys.argv[0]]

from pytv.ModuleLoader import moduleloader
from basic_modules.PyTU import QuType, QuMode, OfMode
from top_api import (
    ArchitectureConfig, ArithmeticConfig, ImplementationConfig,
    ModuleTOP, ProtocolSpec, QuantKey,
)
from generated_root import require_writable_generated_root

sys.argv = _real_argv

# 1. PyTV settings
out_dir = require_writable_generated_root() / "generation" / "my_design"
out_dir.mkdir(parents=True, exist_ok=True)
moduleloader.reset()
moduleloader.set_naming_mode("SEQUENTIAL")
moduleloader.set_root_dir(str(out_dir))
moduleloader.set_language_mode("verilog")
moduleloader.disEnableWarning()
moduleloader.set_debug_mode(False)
moduleloader.set_look_ahead_speedup(False)

# 2. Specifications
protocol = ProtocolSpec(
    pusch={"num_RB_range": (20, 273), "num_symbols_range": (4, 14), "is_ECP": False},
    dmrs={
        "dmrs_Uplink": True, "dmrs_Type": 1, "is_double_dmrs": False,
        "is_enhanced": False, "dmrs_typeA_pos": "pos2",
        "additional_DMRS_range": [0, 1, 2],
    },
    antenna_ports=[0, 1],
    slot_index_format=QuType(4, 0, False),
)
architecture = ArchitectureConfig(
    rb_parallelism=1,
    fi_lmmse_parallelism=4,
    freq_interp="linear",
    time_interp="linear",
    input_mode="B",
    switchable_ports=False,
    ti_re_parallelism=3,
)
quants = {
    QuantKey.Y: QuType(11, 4, True),
    QuantKey.H_LS: QuType(12, 4, True),
    QuantKey.H_FI: QuType(12, 4, True),
    QuantKey.H_TI: QuType(12, 4, True),
    QuantKey.FI_LMMSE_COEFF: QuType(12, 10, True),
    QuantKey.TI_LMMSE_COEFF: QuType(12, 11, True),
}
arithmetic = ArithmeticConfig(ls_quant_mode=QuMode.TRN.TCPL, ls_overflow_mode=OfMode.WRP.TCPL)
implementation = ImplementationConfig()

# 3. Generation
ModuleTOP(protocol, architecture, quants, arithmetic, implementation)
print(f"Design has been written to {out_dir}")
```

### 2.1 Protocol constraints

- `dmrs_Type` ∈ `{1, 2, "Hybrid"}`; `is_ECP` / `is_double_dmrs` / `is_enhanced` / `dmrs_typeA_pos` may also be `"Hybrid"` for runtime-selectable behaviour;
- `fi_re_parallelism`, `ti_re_parallelism` must divide 12;
- `fi_lmmse_parallelism ≥ rb_parallelism` and must be divisible by it;
- port IDs are integers in 0..23, non-repeating, subject to other protocol limits (see TS 38.211 §6.4.1.1.1);
- `quants` keys must be **exactly** the 6 `QuantKey`s — more or fewer raise an error;
- `QuType(DWT, FRAC, IF_SIGNED)`: `DWT` is a positive integer, `0 ≤ FRAC ≤ DWT`.

`Hybrid` means the dimension is elaborated with several branches at once and
selected at runtime through ports/configuration, so one compile covers several
protocol forms.

## 3. Cocotb-based test framework

The test entry point is `tests/suites/top/runner.py`; `c_model.cpp` is the
bit-exact reference. One pytest item = one RTL build + its runtime sub-cases
(Hybrid branches reuse one compiled Verilator binary).

Three layers:

| Layer | Marker | Purpose |
| --- | --- | --- |
| Health check | `smoke` | three deterministic low-cost checks |
| Regression | `regression` | named architectural edge anchors |
| Exploration | `explore` | deterministic coverage-oriented sampling |

### Common commands

```bash
# Health check
conda run -n pytv pytest tests/suites/top/runner.py -m smoke -v -n 1

# Named architectural regression
conda run -n pytv pytest tests/suites/top/runner.py -m regression -v

# Exploration (single worker; small/medium/large = 20/48/96 builds)
conda run -n pytv pytest tests/suites/top/runner.py -m explore -v -n 1 \
  --top-explore-seed 20260809 --top-explore-level large

# List / generate a manifest without simulating
conda run -n pytv python -m tests.suites.top.explore --seed 20260809 --level small --list

# Replay one exact runtime (BUILD_ID.RUNTIME_ID from a failure report)
conda run -n pytv pytest tests/suites/top/runner.py -m explore -v -n 1 \
  --top-replay-manifest tests/suites/top/artifacts/manifests/explore_20260809_medium.json \
  --top-case-id BUILD_ID.RUNTIME_ID

# Audit a completed or interrupted exploration (nonzero exit on failure)
conda run -n pytv python -m tests.suites.top.audit \
  --manifest tests/suites/top/artifacts/manifests/explore_20260809_large.json

# Infrastructure-only checks (no broad campaign)
conda run -n pytv pytest tests/suites/top/test_infrastructure.py -q
```

### Filtering and environment variables

```text
--top-fi lmmse                 # FI algorithm filter
--top-build-mode hybrid        # hybrid / static-single / static-double
--top-explore-budget 32        # build budget for the level
--top-manifest PATH            # manifest output path
--top-build-root PATH          # build/generation root (overrides default)
```

| Env var | Effect |
| --- | --- |
| `PHY_PUSCH_GENERATED_ROOT` | generated root (pytest and audit share it) |
| `TOP_DISABLE_BUILD_CACHE=1` | force recompile, skip content-stamped cache |
| `TOP_DIAGNOSTIC=1` | focused numerical / replay probe logs |
| `TOP_SKIP_LINT=1` | skip the Yosys lint gate |
| `VERIF_ENABLE_WAVES=1` | enable waveform dumping |

### Test results

- manifest: `tests/suites/top/artifacts/manifests/`
- failure reports (payload + reproduce command): `tests/suites/top/artifacts/failures/`

## 4. Verification after hand-off

```bash
conda run -n pytv pytest tests/suites/top/runner.py -m smoke -v -n 1
```

## 5. Contents

| Path | Role |
| --- | --- |
| `v_*.py`, `top_api.py`, `dmrs_config.py`, `lmmse_matrix_gen.py`, `analyze_timing.py`, `delay_budget.py`, `constants.py` | generator sources |
| `generated_root.py` | generated-root resolution & writability probe |
| `basic_modules/`, `helpers/` | PyTV basic unit library / generator helpers |
| `tests/framework/` | test framework (runner, config, accelerator, logger, lint) — includes `constants.py` (`OUTPUT_ROOT`) |
| `tests/QuBLAS/` | C-model C++ header library |
| `tests/suites/top/` | TOP suite (runner, cases, explore, audit, testbench, `c_model.cpp`) |
| `docs/` | per-module architecture notes (optional reading) |

The generator's content fingerprint covers `v_*.py`, `basic_modules/*.py`,
`dmrs_config.py`, and `analyze_timing.py`; deleting or editing any of these
invalidates the build cache.
