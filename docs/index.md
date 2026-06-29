# qchem-workbench

qchem-workbench is a backend-agnostic workflow manager for quantum-chemistry
projects. It organizes species registries, rendered inputs, parsed outputs,
result stores, analysis tables, reports, and example workflows.

It does not implement DFT or replace Gaussian, ORCA, PySCF, Quantum ESPRESSO,
or other electronic-structure codes. Execution support is explicit and limited:
PySCF single-point execution is optional, while Gaussian, ORCA, and Quantum
ESPRESSO support is input/output adapter support.

## Current Scope

- Molecular species registries and XYZ geometry handling.
- Gaussian, ORCA, and Quantum ESPRESSO input/output adapters.
- Optional parsed molecular property containers for explicit Gaussian and ORCA
  output sections.
- Optional PySCF and ASE integrations.
- Generic reaction, adsorption, CHE-style, convergence-study, and screening
  bookkeeping.
- File-based active-learning and BO Forge handoff utilities.
- Transparent microkinetic network bookkeeping, optional SciPy simulation,
  steady-state solving, rate/TOF tables, sensitivity, and user-provided
  uncertainty sampling.
- Markdown, CSV, LaTeX, and plot-oriented report utilities.

All examples using committed output files are synthetic fixtures unless stated
otherwise.
