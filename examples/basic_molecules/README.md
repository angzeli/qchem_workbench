# Basic Molecules Example

This example is a small qchem-workbench workflow for simple molecules. It is
intended for fast command-line testing and tutorial use, not as a benchmark or
production chemistry setup.

The Gaussian-like output files in `outputs/` are synthetic parser fixtures.
Their energies and text are not scientific data.

## Validate The Registry

```bash
qchemwb validate examples/basic_molecules/species.yaml
```

## Optional PySCF Single Point

This command requires installing the optional PySCF dependency.

```bash
qchemwb run-pyscf examples/basic_molecules/species.yaml --method b3lyp --basis sto-3g --out /tmp/qchemwb-basic-pyscf.json
```

## Render Gaussian Inputs

This only writes Gaussian input files. It does not run Gaussian.

```bash
qchemwb render-gaussian examples/basic_molecules/species.yaml --method wb97xd --basis 6-31g --task single_point --out /tmp/qchemwb-basic-gaussian --force
```

## Parse Synthetic Gaussian Fixtures

```bash
qchemwb parse-gaussian examples/basic_molecules/outputs --out /tmp/qchemwb-basic-results.json
```

## Generate A Markdown Report

```bash
qchemwb report /tmp/qchemwb-basic-results.json --species examples/basic_molecules/species.yaml --out /tmp/qchemwb-basic-report.md
```

See `report_example.md` for a compact example of the expected report shape.
