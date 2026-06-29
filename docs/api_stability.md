# v3 Platform Scope And Stability

This page defines the v3 platform stability policy for qchem-workbench. The
stable surface is a backend-agnostic workflow platform for molecular,
periodic/QE fixture, surface adsorption, CHE-style, microkinetic,
active-learning, dashboard, reporting, and screening workflows. It does not
promise to cover every computational-chemistry task, and it does not implement
DFT or replace external electronic-structure engines.

Stability means that documented imports, CLI command names, and schema version
handling should remain compatible until the next major release unless migration
notes are provided. It does not mean every optional backend, parser section, or
scientific workflow is appropriate for every system.

## Stable Python Imports

The stable public Python API is the set of names exported through package-level
`__all__` values in:

- `qchem_workbench`
- `qchem_workbench.active_learning`
- `qchem_workbench.core`
- `qchem_workbench.analysis`
- `qchem_workbench.backends`
- `qchem_workbench.campaigns`
- `qchem_workbench.dashboard`
- `qchem_workbench.geometry`
- `qchem_workbench.microkinetics`
- `qchem_workbench.projects`
- `qchem_workbench.reports`
- `qchem_workbench.results`
- `qchem_workbench.schema`
- `qchem_workbench.templates`

Only names exported by each package's `__all__` are stable. Underscore-prefixed
helpers, unexported module internals, and parser implementation details are
private.

## Stable CLI Commands

The command names shown by `qchemwb --help` are the stable v3 CLI surface.
New commands and options may be added in later releases, but existing stable
command names should not be renamed or removed without migration notes.

Stable command groups include:

| Area | Commands |
| --- | --- |
| Project setup and validation | `init`, `validate`, `schema-check`, `run-project` |
| Backend discovery and execution | `backends`, `run-pyscf` |
| Input rendering | `render-gaussian`, `render-orca`, `render-qe` |
| Output parsing | `parse-gaussian`, `parse-orca`, `parse-qe` |
| Structures and surfaces | `inspect-structure`, `convert-structure`, `build-slab`, `place-adsorbate` |
| Analysis tables | `check-results`, `reaction-table`, `adsorption-table`, `che-table`, `convergence-table`, `select-conformers` |
| Reports, exports, and plots | `report`, `dashboard-report`, `export-properties`, `plot-pathway`, `plot-spectrum`, `triage` |
| Campaigns and active learning | `descriptor-table`, `rank-candidates`, `active-learning ...` |
| Microkinetics | `microkinetics ...` |
| Dashboard | `dashboard` |

## Experimental Surfaces

The following surfaces are useful but intentionally marked experimental for v3:

- schema migration write support, which is currently a reporting stub;
- rule-based campaign ranking semantics beyond visible scoring columns;
- optional RDKit conformer generation;
- optional ASE slab and adsorbate placement helpers;
- optional BO Forge Python adapter internals;
- detailed Streamlit layout choices in the dashboard UI.

Experimental surfaces remain conservative: they should not invent scientific
data or make hidden scientific decisions.

## Schema Versions

All user-facing schema loaders use explicit `schema_version` fields. Current
schema version is `1` for the implemented schemas below. Unsupported versions
raise clear errors. The `schema-check` CLI currently covers the core schema
families listed with `yes`; other schema files are validated through their
dedicated loaders and workflow commands.

| Schema family | Current version | Loader/API | `schema-check` coverage |
| --- | --- | --- | --- |
| Species registry | `1` | `load_species_registry` | yes |
| Result store | `1` | `load_result_collection` | yes |
| Project manifest | `1` | `load_project_manifest` | yes |
| Reaction/pathway | `1` | `load_pathway` | yes |
| Screening campaign manifest | `1` | `load_campaign_manifest` | yes |
| Adsorption workflow | `1` | `load_adsorption_workflow` | no |
| CHE pathway | `1` | `load_che_pathway` | no |
| Pseudopotential manifest | `1` | `load_pseudopotential_manifest` | no |
| Convergence study | `1` | `load_convergence_study` | no |
| Structure pathway | `1` | `load_structure_pathway` | no |
| Microkinetic model | `1` | `load_microkinetic_model` | no |
| Microkinetic conditions | `1` | `load_microkinetic_conditions` | no |
| Microkinetic rate parameters | `1` | `load_rate_parameter_set` | no |
| Microkinetic uncertainty distributions | `1` | `load_parameter_distributions` | no |
| Active-learning candidates | `1` | `load_candidate_registry` | no |
| Active-learning campaign dataset | `1` | `load_active_learning_campaign` | no |
| Active-learning objectives/constraints | `1` | `load_objective_spec` | no |
| Active-learning state | `1` | `load_campaign_state` | no |

`SurfaceModel`, `AdsorptionSite`, and `CoverageSpec` are stable Python
bookkeeping models. They do not currently expose a standalone user-facing YAML
schema loader.

## Backend Support Matrix

The built-in backend registry is descriptive metadata, not a promise that a
given output file contains every property.

| Backend | Input rendering | Output parsing | Execution | Molecular | Periodic | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Gaussian | yes | yes | no | yes | no | External Gaussian is not bundled or invoked. |
| ORCA | yes | yes | no | yes | no | External ORCA is not bundled or invoked. |
| PySCF | no | no | optional | yes | no | Requires the optional `pyscf` extra; limited to molecular single points. |
| Quantum ESPRESSO `pw.x` | yes | yes | no | yes | yes | External QE and pseudopotentials are user-provided. |
| ASE helpers | file conversion/helpers | no | no calculators | yes | yes | Optional adapter/helper package, not a registered execution backend. |

## Optional Feature Groups

Base installation does not require Streamlit, PySCF, ASE, RDKit, SciPy, BO
Forge, or documentation-build tools.

| Extra | Purpose | Stability boundary |
| --- | --- | --- |
| `pyscf` | Optional PySCF single-point execution | Execution path is explicit and remains narrow. |
| `ase` | Structure conversion, slab helpers, adsorbate placement helpers | Generated structures are starting geometries requiring inspection. |
| `rdkit` | SMILES-to-conformer setup helpers | Generated conformers are not quantum-chemical minima. |
| `scipy` | Microkinetic ODE and steady-state solvers | Non-convergence must remain visible. |
| `dashboard` | Optional read-only Streamlit dashboard | Dashboard must not mutate project files by default. |
| `bo-forge` | Optional BO Forge Python adapter | File-based interchange remains the stable integration path. |
| `docs` | MkDocs documentation build | Not required at runtime. |
| `dev` | Local tests and developer checks | Not required at runtime. |

## Deprecation Policy

Stable Python exports, CLI command names, and schema fields should not be
removed during a minor release. If a stable item must change, the release notes
and migration guide must describe the change, the old behaviour, and the
replacement. Experimental APIs may change in minor releases, but release notes
should still identify the change when user files or workflows are affected.

Schema migrations must be explicit. qchem-workbench should not silently rewrite
or reinterpret unknown schema versions; migration helpers should default to
dry-run/reporting behaviour.

## Semantic Versioning Policy

- Major releases may introduce breaking changes to stable imports, CLI command
  names, schema semantics, or documented sign conventions, with migration notes.
- Minor releases may add commands, options, parser sections, schemas, optional
  integrations, and experimental workflow helpers without breaking stable
  surfaces.
- Patch releases are reserved for bug fixes, parser robustness improvements,
  documentation corrections, and non-breaking quality improvements.
- Changes to scientific bookkeeping definitions, units, or sign conventions
  must be documented. A change that intentionally breaks an established stable
  convention belongs in a major release unless it fixes a documented bug.
