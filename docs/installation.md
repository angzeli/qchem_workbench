# Installation

Install the base package from a checkout:

```bash
python -m pip install -e .
```

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Optional integrations are separate:

```bash
python -m pip install -e ".[ase]"
python -m pip install -e ".[pyscf]"
python -m pip install -e ".[rdkit]"
python -m pip install -e ".[docs]"
python -m pip install -e ".[dashboard]"
```

The `dev` extra installs the currently configured local developer tools. The
`docs` extra installs the documentation builder only; it is not part of the base
runtime dependency set. The `dashboard` extra installs Streamlit for the
optional read-only dashboard.

Gaussian, ORCA, and Quantum ESPRESSO executables are not bundled or required by
the base package. Their adapters render input files or parse text outputs.
Pseudopotential files for Quantum ESPRESSO are user-provided and are not chosen
by qchem-workbench.

Build the documentation site when the docs extra is installed:

```bash
python -m mkdocs build --strict
```
