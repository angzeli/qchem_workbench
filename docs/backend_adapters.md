# Backend Adapters

Backends are discoverable through the capability registry:

```bash
qchemwb backends
```

Current built-in backend metadata covers:

| Backend | Input rendering | Output parsing | Execution | Molecular | Periodic | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| Gaussian | yes | yes | no | yes | no | External Gaussian installation is not bundled or invoked. |
| ORCA | yes | yes | no | yes | no | External ORCA installation is not bundled or invoked. |
| PySCF | no | no | optional | yes | no | Requires the optional `pyscf` extra and supports narrow molecular single points. |
| Quantum ESPRESSO `pw.x` | yes | yes | no | yes | yes | External QE installation and pseudopotentials are user-provided. |

The registry reports whether each adapter supports input rendering, output
parsing, execution, molecular workflows, periodic workflows, and parsed property
families. Capability metadata is descriptive; it is not a guarantee that a
specific calculation contains every property.

Gaussian, ORCA, and Quantum ESPRESSO support is input/output adapter support.
qchem-workbench does not execute those engines in CI or at runtime.
QE input rendering, output parsing, pseudopotential manifests, convergence
tables, and surface placement caveats are documented in
[`qe_surface_workflows.md`](qe_surface_workflows.md).

Detailed Gaussian and ORCA property parsing support is documented in
[`property_parsing.md`](property_parsing.md). Population charges, orbital
energies, vibrational summaries, and excited-state summaries are stored as
parsed properties with units and source provenance; they are not interpreted as
standalone observables or predictions.
