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

Render a Gaussian route from a calculation spec in Python:

```python
from qchem_workbench.backends.gaussian_input import gaussian_route_from_spec
from qchem_workbench.core.calculation import CalculationSpec

spec = CalculationSpec(
    backend="gaussian",
    method="wb97xd",
    basis="6-31+G(d,p)",
    task="opt_freq",
    solvent="smd,solvent=water",
)
route = gaussian_route_from_spec(spec)
```

## Parsed Result Fields

Gaussian thermochemistry parsing keeps corrections and totals separate:

- `zero_point_correction_hartree`
- `thermal_correction_energy_hartree`
- `thermal_correction_enthalpy_hartree`
- `thermal_correction_gibbs_hartree`
- `sum_electronic_zero_point_energy_hartree`
- `sum_electronic_thermal_free_energy_hartree`

## Example Pathways

Generic pathway example:

- `examples/pathways/basic_isomerisation.yaml`

Illustrative CO2RR molecular bookkeeping examples:

- `examples/pathways/co2rr/co_pathway.yaml`
- `examples/pathways/co2rr/formate_pathway.yaml`

The CO2RR examples are not complete mechanisms and do not include
electrochemical or standard-state corrections.

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
