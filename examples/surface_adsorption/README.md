# Surface Adsorption Example

This is a synthetic bookkeeping example for adsorption-energy workflows. It
connects three existing result labels: a clean slab, an isolated adsorbate, and
a combined slab+adsorbate result.

No slab, adsorbate, or adsorption site in this directory is claimed to be
physically realistic or relaxed. No correction terms are applied automatically.

Example command:

```bash
qchemwb adsorption-table adsorption.yaml results.json --quantity electronic --out adsorption_table.csv
```

`placement.yaml` shows the optional explicit-site adsorbate placement schema.
It is a synthetic starting-geometry template only. qchem-workbench does not
optimise the geometry or auto-detect active sites.
