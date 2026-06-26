# Backend Adapters

Backends are discoverable through the capability registry:

```bash
qchemwb backends
```

Current built-in backend metadata covers:

- Gaussian: molecular input rendering and output parsing; execution is external.
- ORCA: molecular input rendering and output parsing; execution is external.
- PySCF: optional molecular single-point execution.
- Quantum ESPRESSO `pw.x`: input rendering and output parsing for atomistic
  structures; execution is external.

The registry reports whether each adapter supports input rendering, output
parsing, execution, molecular workflows, periodic workflows, and parsed property
families. Capability metadata is descriptive; it is not a guarantee that a
specific calculation contains every property.
