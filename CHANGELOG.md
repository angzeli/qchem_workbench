# Changelog

## v2.0.0

Stable molecular, periodic, surface, reporting, and screening workflow release.

### Added

- ORCA input rendering and output parsing without requiring ORCA in the base
  install or CI.
- Quantum ESPRESSO `pw.x` input rendering and output parsing with explicit,
  user-provided pseudopotential mappings.
- Optional ASE structure conversion, slab setup, and adsorbate-placement
  helpers for starting geometries.
- Optional RDKit SMILES-to-conformer setup helpers.
- Multi-frame XYZ support, geometry utilities, conformer-aware registries, and
  conformer result selection.
- Adsorption workflow schemas, adsorption energy/free-energy tables, and
  adsorption report sections.
- Explicit correction-term and CHE-style free-energy bookkeeping with visible
  potential, pH, and user-provided correction terms.
- Generic property schemas, vibrational and excitation parsing, spectrum
  broadening, and property report sections.
- Campaign manifests, descriptor tables, transparent ranking rules, and
  file-based active-learning handoff helpers.
- Backend capability registry, schema-check command, comprehensive synthetic
  example suite, MkDocs documentation site, and strengthened CI matrix.

### Stability Notes

- Package and CLI names remain `qchem_workbench` and `qchemwb`.
- CLI commands shown by `qchemwb --help` are the stable v2.0 command surface.
- Current schema version remains `1` for species registries, result stores,
  pathway files, project manifests, and campaign manifests.
- Experimental helper surfaces are documented in the API stability guide.

### Scientific Scope

- qchem-workbench remains a workflow manager and does not implement DFT.
- Gaussian, ORCA, and Quantum ESPRESSO support is input/output adapter support;
  those external engines are not bundled or executed by qchem-workbench.
- PySCF execution is optional and limited to molecular single-point workflows.
- Surface, adsorption, CHE, and screening outputs are transparent bookkeeping
  aids that require expert validation.
- Synthetic fixtures remain labelled as synthetic and are not scientific data.

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
