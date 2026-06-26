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
```

Gaussian, ORCA, and Quantum ESPRESSO executables are not bundled or required by
the base package. Their adapters render input files or parse text outputs.

Build the documentation site when the docs extra is installed:

```bash
python -m mkdocs build --strict
```
