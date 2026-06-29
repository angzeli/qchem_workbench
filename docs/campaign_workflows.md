# Campaign Workflows

Campaign manifests manage candidate sets, descriptor definitions, result paths,
and transparent ranking rules. They do not implement machine learning or make
automatic scientific decisions.

```yaml
schema_version: 1
campaign:
  name: synthetic screening demo
  results: results.json
  candidates:
    - id: water
      species: water
  descriptors:
    - name: gap_ev
      source: result
      field: gap_ev
  ranking:
    rules:
      - descriptor: gap_ev
        direction: maximize
```

Generate descriptors and rankings:

```bash
qchemwb descriptor-table campaign.yaml results.json --out descriptors.csv
qchemwb rank-candidates campaign.yaml descriptors.csv --out ranked_candidates.csv
```

Ranking outputs include visible score components and reasons for excluded rows.
Missing descriptor values are not imputed.

For file-based active-learning loops, BO Forge handoff files, proposal import,
and campaign state tracking, see `active_learning.md`.
