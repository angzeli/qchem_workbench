# Continuous Integration

GitHub Actions runs a fast base test matrix and a small optional-dependency job.
No Gaussian, ORCA, Quantum ESPRESSO, or licensed executable is required.

## Jobs

- Base tests: install `.[dev]` and run `python -m pytest` on Python 3.10,
  3.11, and 3.12.
- Example validation: install `.[dev]` and run
  `python scripts/validate_examples.py`.
- Optional ASE tests: install `.[dev,ase]` and run the ASE-specific tests.
- Lint/type checks: no project lint, format, or type-check command is
  configured yet.

PySCF and RDKit optional tests are not separate required CI jobs at this stage.
Their tests skip cleanly when the optional dependency is unavailable.

## Local Equivalents

Run the base gate:

```bash
python -m pytest
python scripts/validate_examples.py
```

Run ASE-specific checks when ASE is installed:

```bash
python -m pytest tests/test_ase_adapter.py tests/test_ase_surface.py tests/test_ase_adsorption.py
```

Build the documentation site when the docs extra is installed:

```bash
python -m mkdocs build --strict
```
