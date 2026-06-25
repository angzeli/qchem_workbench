# Changelog

## v1.0.0

Initial stable public release of qchem-workbench.

### Added

- Backend-independent core models for species, geometries, calculation specs,
  and calculation results.
- JSON result collection storage with schema versioning.
- Optional PySCF single-point backend.
- Gaussian input rendering, scheduler script templates, and Gaussian output
  parsing.
- Generic quality checks, result/species matching, reaction-energy tables,
  plotting, Markdown reports, and failed-job triage reports.
- Optional project manifests and explicit `run-project` orchestration.
- Basic molecule and illustrative CO2RR molecular workflow examples using
  synthetic fixtures.
- Developer guide, release checklist, example validation script, and GitHub
  Actions CI.

### Stability Notes

- CLI command names shown by `qchemwb --help` are treated as the stable v1.0
  command surface.
- Public Python package exports are defined through package-level `__all__`
  values.
- Current schema version is `1` for species registries, result collections,
  pathway files, and project manifests.

### Scientific Scope

- qchem-workbench is a workflow manager, not a quantum-chemistry engine.
- It does not implement DFT, thermochemistry corrections, electrochemical
  corrections, or mechanistic inference.
- Synthetic fixtures are for parser and workflow validation only.
