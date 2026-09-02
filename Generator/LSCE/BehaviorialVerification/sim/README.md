# LSCE runtime simulation directory

This is the fixed runtime output root for LS RTL validation.

Running the following command from the repository root creates or updates
`Testcase1/` below this directory:

```bash
metrics ls evaluate 1
```

Each `TestcaseN/` may contain the generated standalone C++ reference program,
RTL and testbench files, Icarus output, `wave.vcd`, comparison files, and
`simulation_result.json`. These generated files are intentionally ignored by
Git; only this README is tracked so that a fresh checkout contains the canonical
`sim` directory.

Archived, portable evidence from earlier verified runs remains under
`simulation_artifacts/ls/` at the repository root.
