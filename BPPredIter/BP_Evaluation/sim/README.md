# BP runtime simulation directory

This is the fixed runtime output root for BP RTL validation. Running
`metrics bp evaluate 1` from the repository root creates or updates `config1/`
below this directory.

Each `configN/` may contain generated RTL, simulator logs, comparison data,
`simulation_result.json`, and `wave.vcd`. These runtime files remain ignored by
Git; only this README is tracked so that a fresh checkout contains the canonical
BP `sim` directory.

Portable evidence from earlier verified runs is stored under
`simulation_artifacts/bp/` at the repository root.
