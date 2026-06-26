# Electrochemistry and CHE-Style Bookkeeping

qchem-workbench supports transparent computational hydrogen electrode (CHE)
style bookkeeping. It does not solve electrochemistry automatically, choose a
mechanism, choose references, apply standard corrections, or validate a
catalyst model.

The implementation starts from explicit species Gibbs free energies stored in a
result collection. If a required Gibbs value is missing, the row remains
incomplete. It does not fall back to electronic energy.

## CHE Pathway Schema

CHE pathway files use `schema_version: 1`:

```yaml
schema_version: 1
reactions:
  - id: synthetic_step_1
    reactants: {A: 1}
    products: {B: 1}
    proton_electron_pairs: 1
    pH: 7
    potential_V: 0.0
    potential_reference: SHE
    temperature_K: 298.15
    correction_terms:
      - label: synthetic user correction
        value_eV: 0.05
        sign_convention: added to uncorrected delta G
        source: synthetic example table
    notes: Synthetic bookkeeping example, not scientific data.
```

Supported `potential_reference` labels are `SHE`, `RHE`, and `user_defined`.
The label is recorded and validated, but qchem-workbench does not decide which
reference is appropriate.

## Sign Conventions

The uncorrected value is:

```text
Delta G = products - reactants
```

Built-in CHE correction terms are listed separately:

```text
potential correction = -n * U eV
pH correction = n * k_B * T * ln(10) * pH eV
```

Here `n` is `proton_electron_pairs`, `U` is `potential_V`, and `T` is
`temperature_K` or 298.15 K if no temperature is provided. These are transparent
bookkeeping conventions. Users are responsible for deciding whether the
conventions fit their references and system.

User-supplied correction terms are added in eV and must include a visible label,
value, sign convention, and source or note.

## CLI

Generate a CHE table from synthetic-style inputs:

```bash
qchemwb che-table che_pathway.yaml results/results.json --out results/che_table.csv
```

The CSV includes uncorrected Delta G, every correction term, correction totals,
corrected Delta G, missing-data fields, warnings, and notes. It does not report
activity, selectivity, or experimental validation.

## Limiting-Potential Descriptor

`qchem_workbench.analysis.che.che_limiting_potential()` identifies the maximum
uphill corrected free-energy step and reports the reaction ID or tied IDs. It
computes a limiting-potential descriptor only when all rows are complete and
each step has a positive `proton_electron_pairs` value.

The descriptor is not a definitive overpotential. A comparison to an equilibrium
reference is only reported when a reference equilibrium potential is explicitly
provided by the caller.

## What Is Not Automated

qchem-workbench does not:

- choose proton/electron references;
- infer mechanisms or active sites;
- add solvation, entropy, standard-state, or field corrections automatically;
- rank catalytic activity or selectivity;
- treat synthetic examples as real calculations.
