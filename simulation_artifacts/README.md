# RTL simulation artifacts

This directory contains the curated historical RTL evidence for the standard
LS, MIMO, and BP configurations. It is tracked so a fresh Ubuntu checkout has
the result files and waveforms without rerunning Icarus Verilog.

```text
simulation_artifacts/
├── ls/config1..config5/
├── mimo/config1..config6/
└── bp/config1..config5/
```

Each configuration contains one `wave.vcd`, the configuration snapshot, the
machine-readable simulation result, and the small functional comparison files
or logs produced by that module. Existing waveform/terminal captures are stored
as `screenshot.png`; MIMO config6 has no historical screenshot. Generated Verilog, simulator executables,
temporary build trees, and duplicate workspace waveforms are intentionally not
archived.

## View a waveform

For example, on Ubuntu:

```bash
sudo apt install gtkwave
gtkwave simulation_artifacts/ls/config1/wave.vcd
gtkwave simulation_artifacts/mimo/config1/wave.vcd
gtkwave simulation_artifacts/bp/config1/wave.vcd
```

## Verify the archive

The files are marked `-text` in `.gitattributes` so Git does not change their
bytes on Windows or Linux. Verify every archived file from this directory:

```bash
cd simulation_artifacts
sha256sum -c SHA256SUMS
```

## Regenerate current outputs

Run from the repository root in the documented module environments:

```bash
python -m metrics_framework ls evaluate 1
python -m metrics_framework mimo evaluate 1
python -m metrics_framework bp evaluate 1
```

Fresh runs write to the modules' ignored simulation/evaluation output trees;
they do not overwrite this historical archive. If JSON validation already
supplies all latency fields, the framework does not launch RTL and therefore
does not produce a new waveform.

The elapsed milliseconds in `simulation_result.json` are single-run wall-clock
measurements. Depending on the module they may include RTL generation,
compilation, simulation, waveform dumping, or other validation work. They are
not cross-host benchmarks. Compare cycle counts for functional timing; use
repeated runs with an identical toolchain and inputs for host performance.

Some BP result JSON files retain absolute `/home/roboute/...` paths from the
original run as provenance. Those strings are historical metadata, not paths
that must exist in a new checkout. The evidence files referenced by them are
collected beside the result where applicable.

## Provenance

- LS: original `Generator/LSCE/BehaviorialVerification/sim/TestcaseN` top-level
  evidence. All five configuration snapshots are semantically identical to the
  current root `configs/config_caseN.json` files.
- MIMO: original
  `Generator/MIMODetector/BehaviorialVerification/sim/TestcaseN` top-level
  evidence. Configurations 1–5 differ from current configs only by later-added
  area-reference switches; configuration 6 is semantically identical.
- BP: original `BPPredIter/BP_Evaluation/sim/configN` top-level evidence. All
  five configuration snapshots are semantically identical to the current
  module configs.
