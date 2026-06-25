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
