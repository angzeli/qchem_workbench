# Synthetic Active-Learning Adsorption Screening Example

This example demonstrates file-based active-learning bookkeeping for a small
synthetic adsorption-screening campaign. The descriptor values, objective
values, proposal ranks, and report outputs are synthetic fixtures for testing
and documentation only. They are not catalyst-performance predictions.

The workflow stays transparent:

```bash
qchemwb active-learning build-dataset campaign.yaml --out al_dataset.csv
qchemwb active-learning score-dataset al_dataset.csv objectives.yaml --out al_scored.csv
qchemwb active-learning export-bo-forge campaign.yaml al_scored.csv --out bo_forge_export/
qchemwb active-learning import-proposals campaign.yaml proposed_candidates.csv --out next_calculations.yaml
qchemwb active-learning state campaign_state.json summary
qchemwb active-learning report campaign.yaml campaign_state.json al_scored.csv --objectives objectives.yaml --proposals proposed_candidates.csv --out report_example.md
```

qchem-workbench does not run an optimiser in this example. The BO Forge handoff
is a stable CSV/JSON folder, and BO Forge itself is not required.
