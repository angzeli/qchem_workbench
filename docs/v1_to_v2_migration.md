# v1 to v2 Migration

qchem-workbench v2.0 keeps the package import name and CLI name unchanged:

- Python package: `qchem_workbench`
- CLI command: `qchemwb`

The v2.0 release stabilises the workflow surface that grew during v1.x. It does
not replace Gaussian, ORCA, Quantum ESPRESSO, PySCF, ASE, or RDKit, and it does
not add hidden scientific corrections.

## Schemas

The current schema version remains `1` for supported file types:

- species registries;
- result stores;
- pathway files;
- project manifests;
- campaign manifests.

Files should keep an explicit `schema_version: 1`. Unknown or missing schema
versions are rejected consistently. Use `qchemwb schema-check path/to/file.yaml`
or `qchemwb schema-check path/to/results.json` to inspect a file before using it
in a v2 workflow.

## Result Stores

Result stores remain transparent JSON files. v2 result records may include
fields added during v1.x, including:

- `conformer_id` for conformer-aware workflows;
- `properties` for optional vibrational modes, excited states, dipole moments,
  population analyses, and molecular orbital tables;
- metadata used by parser, quality-check, campaign, and provenance workflows.

Older result records without these optional fields still load with missing
values left missing. Electronic energies, Gibbs free energies, thermal
corrections, and reaction or adsorption energies remain separate fields or
derived tables.

## Backend Registry

Built-in backend capability metadata is now discoverable with:

```bash
qchemwb backends
```

The registry describes whether each backend supports input rendering, output
parsing, optional execution, molecular structures, periodic structures, and
selected parsed properties. It does not install or run external production
codes. Gaussian, ORCA, and Quantum ESPRESSO support is input/output adapter
support; PySCF execution remains optional.

## Optional Dependencies

The base install is still intended to work without heavyweight optional tools.
Optional dependency groups are:

- `pyscf` for optional molecular single-point execution;
- `ase` for optional structure conversion and surface setup helpers;
- `rdkit` for optional SMILES-to-conformer setup helpers;
- `docs` for local documentation builds;
- `dev` for local test and lint tooling.

Install only the extras needed for a workflow, for example:

```bash
python -m pip install "qchem-workbench[ase]"
```

## Examples

The v1 examples remain valid v2 examples. The release validation script checks
the basic molecule, Gaussian parsing, ORCA parsing, QE parsing, CO2RR molecular,
surface adsorption, CHE analysis, screening campaign, and report workflows using
synthetic fixtures where production outputs are not required.

Run:

```bash
python scripts/validate_examples.py
```

## Deprecated Commands Or Fields

No CLI command is deprecated for v2.0. Existing command names remain available.
No result fields are removed. Experimental helper surfaces are documented in
the API stability page and should be treated as subject to change before a
future major release.
