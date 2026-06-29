# Active-Learning And BO Forge Handoff

qchem-workbench active-learning support is file-based campaign bookkeeping. It
helps collect candidate descriptors, apply explicit objective and constraint
rules, export optimiser-ready CSV/JSON files, import proposed candidates, and
track calculation state. It does not implement Bayesian optimisation, choose
new candidates automatically, or claim that a score is real catalytic
performance.

## Candidate Registry

Candidate files are generic and versioned:

```yaml
schema_version: 1
candidates:
  - id: cand_001
    type: molecule
    species: CO
    features:
      descriptor_source: parsed_results
    metadata:
      notes: Example candidate
```

Supported candidate types are `molecule`, `conformer`, `surface`,
`adsorbate_system`, `reaction_pathway`, and `custom`.

## Descriptor Dataset

An active-learning campaign references a candidate registry and descriptor
sources:

```yaml
schema_version: 1
active_learning_campaign:
  name: synthetic adsorption screen
  candidates: candidates.yaml
  descriptor_sources:
    - id: ads
      type: csv
      path: synthetic_adsorption_descriptors.csv
```

Build the dataset:

```bash
qchemwb active-learning build-dataset campaign.yaml --out al_dataset.csv
```

Descriptor sources can come from result stores, adsorption tables, CHE tables,
microkinetic outputs, property exports, or plain CSV files. Missing descriptors
remain missing and missing-data reason columns are preserved.

## Objectives And Constraints

Objective and constraint YAML files make optimisation intent explicit:

```yaml
schema_version: 1
objectives:
  - id: minimise_adsorption_energy
    source_column: ads_adsorption_energy_eV
    direction: minimise
    weight: 1.0
constraints:
  - id: require_no_quality_errors
    source_column: ads_quality_error_count
    op: equals
    value: 0
```

Score a dataset:

```bash
qchemwb active-learning score-dataset al_dataset.csv objectives.yaml --out al_scored.csv
```

Transformations are transparent. Minimise objectives are negated for a
maximise-style score, target objectives use distance to the target, and failed
constraints are visible in output columns.

## BO Forge Interchange

The stable BO Forge integration path is a folder of CSV/JSON files:

```bash
qchemwb active-learning export-bo-forge campaign.yaml al_scored.csv --out bo_forge_export/
```

The folder contains `bo_forge_candidates.csv`, `bo_forge_observations.csv`, and
`bo_forge_metadata.json`. BO Forge is not required to create or read this
interchange format.

An optional Python adapter exists for environments where BO Forge is installed,
but the file-based format is the stable public path.

## Proposal Import

External optimisers can propose candidates through `proposed_candidates.csv`:

```csv
candidate_id,proposal_rank,acquisition_value,proposed_by,notes
cand_001,1,0.72,external_optimizer,Example proposal
```

Import proposals into a calculation-planning manifest:

```bash
qchemwb active-learning import-proposals campaign.yaml proposed_candidates.csv --out next_calculations.yaml
```

The command validates proposed IDs against the candidate registry and does not
run calculations.

## Campaign State

Campaign state is a human-readable JSON file. State changes are explicit and
audited:

```bash
qchemwb active-learning state campaign_state.json summary
qchemwb active-learning state campaign_state.json mark-proposed cand_001 --reason "External proposal"
qchemwb active-learning state campaign_state.json mark-pending cand_001 --reason "Gaussian input rendered"
qchemwb active-learning state campaign_state.json mark-completed cand_001 --result results.json
```

Allowed transitions are `unobserved -> proposed`, `proposed -> pending`,
`pending -> completed`, `pending -> failed`, and `completed -> excluded`.
Failure and exclusion transitions require a reason.

## Loop Report

Generate a Markdown loop report:

```bash
qchemwb active-learning report campaign.yaml campaign_state.json al_scored.csv --objectives objectives.yaml --proposals proposed_candidates.csv --out al_report.md
```

Reports include candidate counts by state, objective definitions, current
ranked candidates, proposed next candidates, pending/failed calculations,
quality flags, and BO Forge handoff provenance. Reports summarize explicit
inputs only; they do not infer optimisation success.

## Synthetic Example

See `examples/active_learning/synthetic_adsorption_screening/`. All descriptor
values, proposal ranks, and outputs in that example are synthetic fixtures.
