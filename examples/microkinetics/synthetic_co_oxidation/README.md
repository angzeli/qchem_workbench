# Synthetic Microkinetic Example

This example is a synthetic microkinetic workflow used to exercise
qchem-workbench commands. The rate constants, distributions, and output values
are not experimental data and are not a validated catalytic mechanism.

The model file defines gas species, surface species, an explicit vacant site,
and elementary steps. Rate constants and uncertainty ranges are user-provided.
qchem-workbench does not generate mechanisms or rate constants automatically.

Example commands:

```bash
qchemwb microkinetics simulate model.yaml --conditions conditions.yaml --out results/mk_trajectory.csv
qchemwb microkinetics steady-state model.yaml --conditions conditions.yaml --out results/mk_steady_state.csv
qchemwb microkinetics rates model.yaml --state results/mk_steady_state.csv --conditions conditions.yaml --tof-species CO2_g --site-count 1.0 --out results/mk_rates.csv
qchemwb microkinetics sensitivity model.yaml --conditions conditions.yaml --observable product_rate:CO2_g --out results/sensitivity.csv
qchemwb microkinetics sample model.yaml --conditions conditions.yaml --n 10 --seed 1 --out results/mk_uncertainty.csv
qchemwb microkinetics plot-trajectory results/mk_trajectory.csv --out reports/coverage.png
qchemwb microkinetics plot-rates results/mk_rates.csv --out reports/rates.png
qchemwb microkinetics plot-sensitivity results/sensitivity.csv --out reports/sensitivity.png
```

The committed `expected_outputs/` CSV files are synthetic fixtures. They are
included only to show output shape and should not be interpreted chemically.
