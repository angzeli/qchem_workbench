# Microkinetics

qchem-workbench supports transparent microkinetic bookkeeping and small
synthetic simulations. It does not generate catalytic mechanisms, infer rate
constants, or claim that a model predicts catalyst performance.

The microkinetics workflow is built from explicit user inputs:

- a versioned network schema with gas species, surface species, site types, and
  elementary steps;
- explicit rate constants, Arrhenius parameters, Eyring parameters, or
  user-provided uncertainty distributions;
- explicit conditions such as external gas activities/pressures, initial
  coverages, time grids, and selected observables.

## Network Schema

The schema is stoichiometric bookkeeping. Vacant sites are represented
explicitly as site type IDs, such as `star`, and surface species reference a
site type.

```yaml
schema_version: 1
microkinetic_model:
  name: synthetic_example
  site_types:
    - id: star
      total_sites: 1.0
      unit: fraction
  species:
    gas:
      CO_g:
        phase: gas
    surface:
      CO_star:
        phase: surface
        site_type: star
  steps:
    - id: co_ads
      reversible: true
      reactants:
        CO_g: 1
        star: 1
      products:
        CO_star: 1
      rate_constant_forward: k_co_ads_f
      rate_constant_reverse: k_co_ads_r
```

The loader validates duplicate IDs, missing site types, invalid coefficients,
unknown species/site references, and reversible steps that lack reverse
parameters. It does not infer missing vacant-site species.

## Rate Parameters

Rate parameters must be user-provided. Direct rate constants, Arrhenius
parameters, and Eyring parameters keep units and provenance visible. Arrhenius
evaluation uses `k = A exp(-Ea/kBT)` with `Ea` in eV. Eyring evaluation uses
`k = (kBT/h) exp(-DeltaG‡/kBT)` with the activation free energy in eV.

Missing parameter provenance produces warnings; missing units are errors.
qchem-workbench does not infer barriers from reaction energies and does not
invent prefactors.

## Simulation And Steady State

ODE simulation and steady-state solving use SciPy when installed:

```bash
pip install -e ".[scipy]"
qchemwb microkinetics simulate model.yaml --conditions conditions.yaml --out results/mk_trajectory.csv
qchemwb microkinetics steady-state model.yaml --conditions conditions.yaml --out results/mk_steady_state.csv
```

The solver reports convergence and residuals. Non-convergence is not hidden,
and a steady state is not marked successful unless the solver reports
convergence and residuals satisfy the requested tolerance.

## Rates, TOF, And Sensitivity

Rate tables are computed from an explicit state CSV:

```bash
qchemwb microkinetics rates model.yaml --state results/mk_steady_state.csv --conditions conditions.yaml --tof-species CO2_g --site-count 1.0 --out results/mk_rates.csv
```

TOF is defined as net production rate divided by an explicit active-site count.
The tool does not infer active-site counts or compare TOFs across inconsistent
models.

Finite-difference sensitivity perturbs `ln(k)` for each explicit rate
parameter and recomputes the selected observable:

```bash
qchemwb microkinetics sensitivity model.yaml --conditions conditions.yaml --observable product_rate:CO2_g --out results/sensitivity.csv
```

This is a transparent finite-difference descriptor. It should not be
overstated as rigorous degree of rate control unless the modelling assumptions
are appropriate and documented by the user.

## Uncertainty Sampling

Parameter distributions are user-provided. Supported distribution types are
`fixed`, `uniform`, `normal`, and `loguniform`. No default uncertainty ranges
are assigned.

```bash
qchemwb microkinetics sample model.yaml --conditions conditions.yaml --n 100 --seed 1 --out results/mk_uncertainty.csv
```

Failed samples are counted and reported. Summary statistics are computed only
from successful samples.

## Plotting

Microkinetic CSV outputs can be plotted with matplotlib:

```bash
qchemwb microkinetics plot-trajectory results/mk_trajectory.csv --out reports/coverage.png
qchemwb microkinetics plot-rates results/mk_rates.csv --out reports/rates.png
qchemwb microkinetics plot-sensitivity results/sensitivity.csv --out reports/sensitivity.png
```

Plots are visual summaries of the model output. They are not experimental
validation.

## Example

See `examples/microkinetics/synthetic_co_oxidation/` for a complete synthetic
workflow. The example values are synthetic fixtures and are not a validated CO
oxidation mechanism.
