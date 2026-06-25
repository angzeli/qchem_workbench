# CO2RR Molecular Workflow Example

This is an illustrative molecular bookkeeping workflow for selected CO2RR
species. It is not a complete CO2RR mechanism, does not include electrochemical
or standard-state corrections, and should not be used to draw scientific
conclusions from the synthetic fixtures.

The XYZ files are simple starter geometries for workflow testing. The Gaussian-
like outputs in `outputs/` are synthetic parser fixtures; their energies are not
scientific data.

## Validate The Registry

```bash
qchemwb validate examples/co2rr_molecular/species.yaml
```

## Render Gaussian Inputs

This writes Gaussian input files only. It does not run Gaussian.

```bash
qchemwb render-gaussian examples/co2rr_molecular/species.yaml --method wb97xd --basis 6-31g --task single_point --out /tmp/qchemwb-co2rr-gaussian --force
```

## Parse Synthetic Gaussian Fixtures

```bash
qchemwb parse-gaussian examples/co2rr_molecular/outputs --out /tmp/qchemwb-co2rr-results.json
```

## Build Reaction Tables

```bash
qchemwb reaction-table examples/pathways/co2rr/co_pathway.yaml /tmp/qchemwb-co2rr-results.json --quantity electronic --out /tmp/qchemwb-co2rr-co-table.csv
qchemwb reaction-table examples/pathways/co2rr/formate_pathway.yaml /tmp/qchemwb-co2rr-results.json --quantity electronic --out /tmp/qchemwb-co2rr-formate-table.csv
```

See `reaction_table_example.csv` for an example table generated from synthetic
fixture values.

## Generate A Report

```bash
qchemwb report /tmp/qchemwb-co2rr-results.json --species examples/co2rr_molecular/species.yaml --out /tmp/qchemwb-co2rr-report.md
```

See `report_example.md` for a compact report-shape example.

