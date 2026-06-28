# Quantum ESPRESSO Parsing Example

This example contains synthetic Quantum ESPRESSO `pw.x`-like fixtures. It
demonstrates parser and convergence-table behavior without requiring Quantum
ESPRESSO.

Example command:

```bash
qchemwb parse-qe outputs/ --out qe_results.json --csv qe_results.csv
qchemwb convergence-table convergence.yaml convergence_results.json --out convergence.csv
```

`pseudos.yaml` is a synthetic pseudopotential manifest example. It does not
provide a real pseudopotential file and is not a production recommendation.
