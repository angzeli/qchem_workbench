# 🧪 qchem-workbench

## 🔬 Backend-agnostic quantum-chemistry workflow management

qchem-workbench is a Python package and CLI for organizing quantum-chemistry
workflows. It helps manage species registries, input files, calculation outputs,
parsed result collections, quality checks, reaction-energy tables, plots, and
Markdown reports across supported backends.

qchem-workbench is not a quantum-chemistry engine. It does not implement or
compute DFT, wavefunction methods, molecular dynamics, thermochemistry
corrections, or electrochemical corrections from scratch. It does not replace
Gaussian, PySCF, ORCA, Quantum ESPRESSO, VASP, or any other
electronic-structure code.
External engines, licensed software, and pseudopotential files are not bundled.

The current workflow support focuses on:

- PySCF single-point calculations through an optional backend.
- Gaussian input rendering without running Gaussian.
- Gaussian output parsing from `.log` and `.out` files.
- ORCA input rendering and `.out` parsing without running ORCA.
- Structure inspection/conversion and starting slab generation through optional
  ASE support.
- Quantum ESPRESSO `pw.x` input rendering and output parsing without running QE.
- Generic species, result, quality-check, reaction, report, and project
  manifest utilities.
- Generic adsorption-energy and CHE-style electrochemical bookkeeping with
  explicit, user-visible correction terms. These workflows require expert
  validation.
- Screening campaign manifests, descriptor tables, and transparent rule-based
  rankings. These are workflow tables, not activity predictions.

CO2RR is included as the first domain example, not as the scope of the package.
Core modules remain generic and backend-agnostic.

## Installation

For local development:

```bash
pip install -e .
```

For the optional PySCF backend:

```bash
pip install -e ".[pyscf]"
```

For optional ASE structure conversion and slab helpers:

```bash
pip install -e ".[ase]"
```

For optional RDKit conformer setup helpers:

```bash
pip install -e ".[rdkit]"
```

For documentation builds:

```bash
pip install -e ".[docs]"
```

For local development tests and currently configured developer tools:

```bash
pip install -e ".[dev]"
```

Run the test suite:

```bash
python -m pytest
```

Show CLI help:

```bash
qchemwb --help
```

Build the documentation site when the docs extra is installed:

```bash
python -m mkdocs build --strict
```

## Quickstart

Create a starter workflow directory and validate its species registry:

```bash
qchemwb init demo --template basic
qchemwb validate demo/species.yaml
```

Render Gaussian input files without running Gaussian:

```bash
qchemwb render-gaussian demo/species.yaml --method wb97xd --basis 6-31g --task single_point --out demo/gaussian_inputs
```

Parse Gaussian-like outputs:

```bash
qchemwb parse-gaussian demo/outputs --out demo/results/gaussian_results.json
```

Render and parse ORCA files without requiring ORCA during this workflow step:

```bash
qchemwb render-orca demo/species.yaml --method b3lyp --basis def2-svp --task single_point --out demo/orca_inputs
qchemwb parse-orca demo/outputs --out demo/results/orca_results.json
```

Render a QE `pw.x` input file after explicitly providing pseudopotentials,
atomic masses, cutoffs, and a cell:

```bash
qchemwb render-qe demo/xyz/water.xyz --pseudo-map pseudos.yaml --ecutwfc 30 --cell 12 12 12 --gamma-only --out demo/qe_inputs/water.in
```

Run quality checks and write a Markdown report:

```bash
qchemwb check-results demo/results/gaussian_results.json --species demo/species.yaml
qchemwb report demo/results/gaussian_results.json --species demo/species.yaml --out demo/reports/report.md
```

Inspect and convert simple XYZ structures without ASE:

```bash
qchemwb inspect-structure demo/xyz/water.xyz
qchemwb convert-structure demo/xyz/water.xyz /tmp/water-copy.xyz
```

Inspect backend adapter capabilities:

```bash
qchemwb backends
```

## PySCF Backend

The PySCF backend is optional. Base package imports and most CLI commands work
without PySCF installed. When PySCF is available, qchem-workbench can run simple
molecular single-point calculations:

```bash
qchemwb run-pyscf demo/species.yaml --method b3lyp --basis sto-3g --out demo/results/pyscf_results.json
```

Current PySCF support is intentionally narrow: molecular single-point
calculations only. The workflow manager records electronic energies and basic
metadata; it does not overinterpret those values.

## Gaussian Input And Output

Gaussian input rendering writes `.gjf` files from species registries and generic
calculation settings:

```bash
qchemwb render-gaussian examples/basic_molecules/species.yaml --method wb97xd --basis 6-31g --task single_point --out /tmp/qchemwb-basic-gaussian --force
```

Optional job-folder and scheduler-script templates are available:

```bash
qchemwb render-gaussian examples/basic_molecules/species.yaml --method wb97xd --basis 6-31g --task single_point --out /tmp/qchemwb-basic-jobs --job-folders --scheduler slurm --force
```

Scheduler scripts are templates only and require local adaptation. qchem-workbench
does not execute Gaussian and does not require a Gaussian installation for input
rendering or output parsing.

Gaussian output parsing scans `.log` and `.out` files and stores a JSON result
collection:

```bash
qchemwb parse-gaussian examples/basic_molecules/outputs --out /tmp/qchemwb-basic-results.json
```

Missing parsed values remain missing. Parser warnings are recorded rather than
filled with invented values. When explicit sections are present, the parser can
also populate optional property containers such as dipole moments, population
analyses, molecular orbital tables, vibrational modes, and excited-state
summaries.

## ORCA Input And Output

ORCA support is file-based. qchem-workbench can render `.inp` files and parse
ORCA-like `.out` files into the same generic result schema:

```bash
qchemwb render-orca examples/basic_molecules/species.yaml --method b3lyp --basis def2-svp --task opt_freq --out /tmp/qchemwb-basic-orca --force
qchemwb parse-orca /path/to/orca_outputs --out /tmp/qchemwb-orca-results.json
```

The tool does not execute ORCA, does not assume a local ORCA binary path or
cluster scheduler, and does not require ORCA for CI.
ORCA property parsing is best-effort and uses the same generic property
containers as Gaussian parsing when explicit sections are present.

## ASE Structure Tools

ASE integration is optional. Base qchem-workbench commands, imports, and CI do
not require ASE. When ASE is installed, qchem-workbench can bridge the generic
`AtomisticStructure` model to ASE `Atoms` objects and use ASE I/O for formats
beyond built-in XYZ support.

Built-in XYZ inspection and XYZ-to-XYZ conversion do not require ASE:

```bash
qchemwb inspect-structure examples/basic_molecules/xyz/water.xyz
qchemwb convert-structure examples/basic_molecules/xyz/water.xyz /tmp/water.xyz
```

With ASE installed, `convert-structure` can read and write additional formats
supported by ASE. The command copies structure data through ASE I/O; it does not
relax structures, alter coordinates, or attach calculators.

ASE can also create simple starting slabs for later atomistic workflows:

```bash
qchemwb build-slab --element Cu --facet 111 --size 2 2 4 --vacuum 15 --out /tmp/cu111.xyz
```

Generated slabs are labelled as starting geometries requiring human inspection.
They are not relaxed slabs, and qchem-workbench does not run DFT or ASE
calculators.

## Quantum ESPRESSO pw.x Input And Output

QE support is currently limited to `pw.x` input rendering and output parsing.
qchem-workbench does not execute QE and does not provide or choose
pseudopotentials. Users must provide pseudopotential filenames explicitly in a
YAML pseudo map, along with atomic masses needed by QE `ATOMIC_SPECIES`.

Example pseudo map:

```yaml
pseudopotentials:
  H: H.pbe.UPF
atomic_masses:
  H: 1.008
```

Schema-versioned pseudopotential manifests can also track user-provided
filename, family, functional, suggested cutoffs, and source/provenance metadata.
qchem-workbench records that metadata; it does not download, choose, or validate
the scientific suitability of pseudopotentials.

Render an input file:

```bash
qchemwb render-qe examples/basic_molecules/xyz/water.xyz --pseudo-map pseudos.yaml --ecutwfc 30 --cell 12 12 12 --gamma-only --out /tmp/water-qe.in
```

Parse QE-like output files:

```bash
qchemwb parse-qe /path/to/qe_outputs --out /tmp/qe-results.json --csv /tmp/qe-results.csv
```

QE cutoff or k-point convergence studies can be organised from explicit
synthetic or parsed result stores:

```bash
qchemwb convergence-table examples/qe_parsing/convergence.yaml examples/qe_parsing/convergence_results.json --out /tmp/qe-convergence.csv
```

Generated QE inputs are starting points for human inspection. Cutoffs,
k-points, cells, pseudopotentials, smearing, and convergence settings are not
guaranteed to be suitable for production calculations.
See `docs/qe_surface_workflows.md` for QE and surface workflow caveats.

## Species Registry Format

Species registries are YAML files with `schema_version: 1` and a `species` list.
Geometry paths may be relative to the registry file.

```yaml
schema_version: 1
species:
  - name: water
    formula: H2O
    charge: 0
    multiplicity: 1
    geometry_path: xyz/water.xyz
    tags: [demo]
    notes: Example molecule
```

The core species model is backend-independent. PySCF spin is derived only when
the PySCF backend needs it.

## Schema Versioning

Public workflow files use explicit schema versions. The current schema version
is `1` for:

- species registries;
- result collections;
- pathway files;
- project manifests;
- campaign manifests.

Missing `schema_version` fields and unsupported schema versions are rejected
with clear errors. qchem-workbench does not silently reinterpret unknown schema
versions.

## Result Schema Overview

Calculation results keep physically distinct quantities in separate fields:

- `electronic_energy_hartree`
- `zero_point_correction_hartree`
- `thermal_correction_energy_hartree`
- `thermal_correction_enthalpy_hartree`
- `thermal_correction_gibbs_hartree`
- `gibbs_free_energy_hartree`
- `sum_electronic_zero_point_energy_hartree`
- `sum_electronic_thermal_free_energy_hartree`
- orbital summaries such as `homo_ev`, `lumo_ev`, and `gap_ev` when available

The result store is transparent JSON. It preserves warnings, metadata, source
paths, and missing values.

Optional parsed molecular properties live under `properties`. Current property
containers include dipole moments in Debye, population-analysis charges in
elementary charge `e`, molecular orbital tables in Hartree/eV, vibrational modes
with explicit units, and excited-state summaries in eV/nm. These values are
parser outputs, not standalone scientific conclusions.

Export tidy property CSV files with:

```bash
qchemwb export-properties results/results.json --out results/properties/
qchemwb export-properties results/results.json --type charges --out charges.csv
```

See `docs/property_parsing.md` for supported Gaussian/ORCA sections, units,
conversions, and caveats.

Stable result fields include:

- `species_name`
- `conformer_id`
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
- `properties`
- `source_path`

## Reaction Table Workflow

Pathway YAML files define stoichiometric bookkeeping only:

```yaml
schema_version: 1
reactions:
  - id: r1
    label: A to B
    reactants:
      A: 1
    products:
      B: 1
```

Compute electronic reaction energies:

```bash
qchemwb reaction-table examples/pathways/basic_isomerisation.yaml /tmp/qchemwb-basic-results.json --quantity electronic --out /tmp/qchemwb-reaction-table.csv
```

Compute Gibbs free-energy differences only when stored Gibbs values are present:

```bash
qchemwb reaction-table examples/pathways/basic_isomerisation.yaml /tmp/qchemwb-basic-results.json --quantity gibbs --out /tmp/qchemwb-gibbs-table.csv
```

Electronic and Gibbs modes do not fall back to each other. No electrochemical or
standard-state corrections are applied.

## CHE-Style Electrochemical Bookkeeping

CHE-style analysis starts from explicit Gibbs free energies and writes every
correction term separately. qchem-workbench does not choose proton/electron
references, infer mechanisms, or claim activity/selectivity.

```bash
qchemwb che-table che_pathway.yaml results/results.json --out results/che_table.csv
```

The built-in bookkeeping terms use documented sign conventions:
`-n * U` eV for potential and `n * k_B * T * ln(10) * pH` eV for pH. Users are
responsible for deciding whether those conventions and references fit their
workflow. See `docs/electrochemistry.md`.

## Screening Campaigns

Campaign manifests define candidate IDs, descriptor columns, result paths, and
explicit ranking rules:

```bash
qchemwb descriptor-table examples/screening_campaign/campaign.yaml examples/screening_campaign/results.json --out /tmp/qchemwb-descriptors.csv
qchemwb rank-candidates examples/screening_campaign/campaign.yaml /tmp/qchemwb-descriptors.csv --out /tmp/qchemwb-ranked.csv
```

Descriptor values are extracted or calculated from stored results and analysis
tables. Missing descriptor values remain missing. Ranking outputs include
visible score components and exclusion reasons; they are not predictions of
activity, selectivity, or experimental behavior.

## Quality Checks And Triage

Quality checks are conservative and generic:

```bash
qchemwb check-results /tmp/qchemwb-basic-results.json --species examples/basic_molecules/species.yaml
```

They report issues such as failed calculations, missing electronic energies,
missing method or basis fields, imaginary frequencies, missing frequency
thermochemistry, possible spin contamination when expected spin is available,
and mixed backend/method/basis result sets.

Failed-job triage writes a Markdown summary:

```bash
qchemwb triage /tmp/qchemwb-basic-results.json --out /tmp/qchemwb-failed-jobs.md
```

Triage suggestions are conservative. They direct users to inspect source files
and warnings rather than prescribing fake fixes.

## Project Manifests

Project manifests are optional YAML files for explicit batch workflows:

```yaml
schema_version: 1
project:
  name: demo
  species: species.yaml
  results: results/results.json
  reports: reports/report.md
  steps: [parse_gaussian, quality_checks, report]
```

Run configured steps:

```bash
qchemwb run-project qchem_project.yaml
```

Only listed steps run. The command does not execute Gaussian.

## Examples

CO2RR molecular bookkeeping example:

- `examples/co2rr_molecular/`
- `examples/pathways/co2rr/co_pathway.yaml`
- `examples/pathways/co2rr/formate_pathway.yaml`

This is an illustrative molecular workflow, not a complete CO2RR mechanism.
Synthetic outputs are labelled as synthetic and should not be used as
scientific data.

Basic molecule tutorial:

- `examples/basic_molecules/`

Parser fixture examples:

- `examples/gaussian_parsing/`
- `examples/orca_parsing/`
- `examples/qe_parsing/`

Surface, CHE, and screening examples:

- `examples/surface_adsorption/`
- `examples/che_analysis/`
- `examples/screening_campaign/`

Generic pathway example:

- `examples/pathways/basic_isomerisation.yaml`

## Scientific Caveats

- Do not invent chemical data, thermochemical corrections, or scientific claims.
- Do not silently accept failed calculations.
- Keep electronic energies, thermal corrections, Gibbs free energies, and
  reaction energies separate.
- Missing parsed values should remain missing and should produce warnings.
- Synthetic fixture data is for parser and workflow testing only.
- Reaction tables use a products-minus-reactants sign convention and apply no
  unrequested corrections.
- CHE-style tables expose every correction term and do not treat limiting
  potentials as experimentally validated overpotentials.
- Surface and CHE workflow outputs are bookkeeping aids that require expert
  review before scientific interpretation.

## Author

Angze Li
