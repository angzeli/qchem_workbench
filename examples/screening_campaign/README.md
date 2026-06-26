# Screening Campaign Example

This example demonstrates campaign descriptors and transparent rule-based
ranking. It is workflow management only: descriptors are extracted values, not
predictions, and the ranking is not a claim of real-world performance or
experimental behavior.

The result values are synthetic.

Example commands:

```bash
qchemwb descriptor-table campaign.yaml results.json --out descriptors.csv
qchemwb rank-candidates campaign.yaml descriptors.csv --out ranked_candidates.csv
```
