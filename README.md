# qchem-workbench

qchem-workbench is a backend-agnostic workflow manager for quantum-chemistry
projects. It helps organize molecular inputs, calculation outputs, parsed
results, and reports across supported backends.

This project does not implement DFT or other quantum-chemistry methods from
scratch. It is a workflow layer around external engines and file formats.

Initial planned backends and integrations include:

- PySCF workflows.
- Gaussian input and output support.

## Development

Run the test suite with:

```bash
python -m pytest
```

Show CLI help with:

```bash
qchemwb --help
```

Create and validate a starter workflow directory with:

```bash
qchemwb init demo --template basic
qchemwb validate demo/species.yaml
```

Run PySCF single-point calculations when the optional PySCF dependency is
installed:

```bash
qchemwb run-pyscf demo/species.yaml --method b3lyp --basis sto-3g --out demo/results/pyscf_results.json
```

## Species Registry

Species registries are YAML files with `schema_version: 1` and a `species`
list. Geometry paths may be relative to the registry file.

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
