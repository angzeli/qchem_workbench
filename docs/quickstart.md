# Quickstart

Create a small workflow directory:

```bash
qchemwb init demo --template basic
qchemwb validate demo/species.yaml
```

Render Gaussian inputs without running Gaussian:

```bash
qchemwb render-gaussian demo/species.yaml --method wb97xd --basis 6-31g --task single_point --out demo/gaussian_inputs
```

Parse committed parser fixtures or user-provided output text into a result store:

```bash
qchemwb parse-gaussian demo/outputs --out demo/results/gaussian_results.json
qchemwb check-results demo/results/gaussian_results.json --species demo/species.yaml
```

Generate a report:

```bash
qchemwb report demo/results/gaussian_results.json --species demo/species.yaml --out demo/reports/report.md
```

Export parsed molecular property tables when a result store contains them:

```bash
qchemwb export-properties demo/results/gaussian_results.json --out demo/results/properties/
```

Inspect registered backend capabilities:

```bash
qchemwb backends
```

Check schema files:

```bash
qchemwb schema-check demo/species.yaml
```
