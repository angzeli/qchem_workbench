# API Stability

qchem-workbench v2.0 defines a stable public surface for molecular,
periodic/QE fixture, surface adsorption, CHE-style, reporting, and screening
workflows. It does not promise to cover every computational-chemistry task.

## Stable Python Imports

The stable public Python API is the set of names exported through package-level
`__all__` values in:

- `qchem_workbench`
- `qchem_workbench.core`
- `qchem_workbench.analysis`
- `qchem_workbench.backends`
- `qchem_workbench.campaigns`
- `qchem_workbench.geometry`
- `qchem_workbench.projects`
- `qchem_workbench.reports`
- `qchem_workbench.results`
- `qchem_workbench.schema`
- `qchem_workbench.templates`

Underscore-prefixed helpers and unexported module internals are private.

## Stable CLI Commands

The command names shown by `qchemwb --help` are the stable v2.0 CLI surface.
New commands may be added in later releases, but existing v2.0 command names
should not be renamed without migration notes.

## Experimental Surfaces

The following areas are useful but intentionally marked experimental in v2.0:

- active-learning handoff CSV helpers;
- rule-based campaign ranking semantics beyond visible scoring columns;
- optional RDKit conformer generation;
- optional ASE slab and adsorbate placement helpers;
- schema migration write support, which is currently a reporting stub.

Experimental surfaces remain conservative: they should not invent scientific
data or make hidden scientific decisions.

## Schema Versions

Current schema version is `1` for species registries, result stores, pathway
files, project manifests, and campaign manifests. Unsupported versions are
reported clearly by `qchemwb schema-check`.
