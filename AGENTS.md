# Agent Guidance

## Project Purpose

qchem-workbench is a backend-agnostic workflow manager for quantum-chemistry
projects. It organizes inputs, outputs, parsed results, and reports; it is not a
DFT engine.

## Repository Layout

- `src/qchem_workbench/`: Python package.
- `tests/`: pytest suite.
- `README.md`: user-facing overview and examples.
- `pyproject.toml`: package metadata, entry points, and test configuration.

## Commands

- Tests: `python -m pytest`
- CLI help: `qchemwb --help`
- Lint/type-check: no project command is configured yet.

## Scientific Safety

- Do not invent chemical data, thermochemical corrections, or scientific claims.
- Do not silently accept failed calculations.
- Keep electronic energies, thermal corrections, Gibbs free energies, and
  reaction energies explicitly separated.
- Missing parsed values should remain missing and produce warnings rather than
  fake values.
- Synthetic fixture data must be clearly labelled as synthetic.

## Naming And Scope

- Package name: `qchem_workbench`
- CLI name: `qchemwb`
- Core modules must remain generic and backend-independent.
- CO2RR-specific assumptions belong only in examples, docs, or optional workflow
  modules, not in core package code.
