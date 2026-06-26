# Developer Guide

This guide documents the implemented architecture of qchem-workbench. It avoids
roadmap claims; if a feature is not in the codebase, it is not described as
available here.

## Architecture

The package is organized around small backend-independent models and optional
backend integrations:

- `qchem_workbench.core`: generic species, geometry, calculation, result, units,
  and registry models.
- `qchem_workbench.backends`: backend protocol plus PySCF, Gaussian input,
  Gaussian parser, Gaussian scheduler-template helpers, ORCA input, and ORCA
  parser helpers.
- `qchem_workbench.analysis`: quality checks, result/species matching, and
  stoichiometric reaction-energy bookkeeping.
- `qchem_workbench.results`: JSON result-store helpers.
- `qchem_workbench.reports`: Markdown reports, exports, plotting, and triage.
- `qchem_workbench.projects`: optional project manifest loading.
- `qchem_workbench.cli`: command orchestration over the same library functions.

Core modules must stay generic. Domain examples such as CO2RR belong under
`examples/`, not in core code.

## Public API Stability

For v1.0, the stable public Python API is the set of names exported through
package-level `__all__` values in:

- `qchem_workbench`
- `qchem_workbench.core`
- `qchem_workbench.analysis`
- `qchem_workbench.backends`
- `qchem_workbench.projects`
- `qchem_workbench.reports`
- `qchem_workbench.results`

Underscore-prefixed helpers and unexported implementation details are private.
The CLI command names shown by `qchemwb --help` are the stable v1.0 command
surface.

## Core Models

`Species` describes a molecular species with name, formula, charge,
multiplicity, geometry path, tags, metadata, and notes. It validates that names
are nonempty, multiplicities are positive, and geometry paths are present.

`MoleculeGeometry` and `Atom` represent parsed XYZ files. The XYZ parser is
deterministic and strict: atom counts must match exactly, coordinates must be
numeric, and element symbols must be in the supported symbol set.

Geometry utilities support centroid translation, distance matrices, RMSD, and
optional Kabsch alignment. RMSD and alignment require identical atom ordering;
the utilities do not perform atom matching or symmetry-aware comparisons.

`CalculationSpec` is a backend-independent request object with backend, method,
basis, task, solvent, charge, multiplicity, and keyword fields.

`CalculationResult` is the generic result object. It keeps electronic energies,
thermal corrections, Gibbs free energies, orbital summaries, warnings, metadata,
and source paths in separate serializable fields.

## Backend Interface

Backends implement the protocol in `qchem_workbench.backends.base`:

```python
def run(species: Species, spec: CalculationSpec) -> CalculationResult:
    ...
```

The backend returns a `CalculationResult`. Missing values should remain `None`,
and warnings should explain missing or questionable parsed fields. Backends
should not invent data or silently accept failed calculations.

## Result Schema

Result JSON uses a transparent top-level object with `schema_version` and a
`results` list. Individual result dictionaries are produced by
`CalculationResult.to_dict()` and restored with `CalculationResult.from_dict()`.

Current schema version is `1`. Species registries, result collections, pathway
files, and project manifests all require a top-level `schema_version`. Missing
or unsupported versions must raise clear errors rather than being interpreted
implicitly.

Important separated fields include:

- `species_name`
- `backend`
- `method`
- `basis`
- `task`
- `success`
- `electronic_energy_hartree`
- `gibbs_free_energy_hartree`
- `zero_point_correction_hartree`
- `thermal_correction_energy_hartree`
- `thermal_correction_enthalpy_hartree`
- `thermal_correction_gibbs_hartree`
- `sum_electronic_zero_point_energy_hartree`
- `sum_electronic_thermal_free_energy_hartree`
- `homo_ev`
- `lumo_ev`
- `gap_ev`
- `warnings`
- `metadata`
- `source_path`

Do not collapse these quantities into a single generic energy field.

## Gaussian Parser Design

`qchem_workbench.backends.gaussian_parser.parse_gaussian_output()` reads a
Gaussian-like output file and returns a `CalculationResult`.

Implemented parsing includes:

- normal and error termination flags;
- route section when present;
- last `SCF Done` electronic energy;
- thermochemistry corrections and summed values;
- frequencies, negative-frequency count, and most negative frequency;
- `S**2` before and after annihilation when present.

Incomplete files should not crash the parser. Missing values remain missing and
warnings explain what was not found. Negative frequencies are reported without
assigning transition-state identity.

## ORCA Input And Parser Design

`qchem_workbench.backends.orca_input.render_orca_input()` renders `.inp` text
from a `Species`, a `CalculationSpec`, and explicit ORCA input options. It does
not run ORCA.

`qchem_workbench.backends.orca_parser.parse_orca_output()` reads an ORCA-like
`.out` file and returns a `CalculationResult`.

Implemented parsing includes:

- normal and error termination flags;
- route line when present;
- final single-point electronic energy;
- frequencies, negative-frequency count, and most negative frequency;
- Hartree-labelled thermochemistry corrections when present;
- eV-labelled HOMO/LUMO summaries when present;
- `S**2` metadata when present.

ORCA execution remains external. The parser uses synthetic fixtures in tests and
does not require ORCA in CI.

## Quality Checks

`qchem_workbench.analysis.quality_checks.run_quality_checks()` returns
`QualityCheck` objects with a code, severity, message, and result identifier.

Implemented checks include:

- unsuccessful calculation;
- missing electronic energy;
- missing method or basis;
- imaginary frequencies present;
- missing thermochemistry for frequency-style tasks;
- possible spin contamination when expected multiplicity is available;
- mixed backend/method/basis in a result set.

Checks are conservative. Warnings should make issues visible without rejecting
usable data unless the calculation is clearly invalid.

## Adding New Backends

To add a backend:

1. Keep backend-specific imports lazy if the dependency is optional.
2. Accept `Species` and `CalculationSpec`.
3. Return `CalculationResult`.
4. Preserve missing fields as `None`.
5. Add focused unit tests that skip cleanly when optional dependencies are not
   installed.
6. Add CLI support only after the library path is tested.

Do not add domain assumptions to core models to support a backend.

## Adding Workflow Examples

Workflow examples belong under `examples/`. Each example should include:

- a species registry;
- XYZ files;
- commands that match the current CLI;
- synthetic parser fixtures when outputs are committed;
- clear labels that fixture data is synthetic;
- scientific caveats when the example is domain-specific.

Generated outputs such as reports, result JSON, and calculation logs are ignored
by default. Commit only intentional fixtures and documentation, force-adding
ignored fixture files when necessary.
