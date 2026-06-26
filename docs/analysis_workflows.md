# Analysis Workflows

qchem-workbench provides transparent bookkeeping utilities. It does not apply
hidden correction terms or infer mechanisms.

Implemented workflows include:

- reaction energy tables from explicit pathway stoichiometry;
- adsorption energy or adsorption free-energy tables from clean slab, isolated
  adsorbate, and combined slab+adsorbate result labels;
- CHE-style free-energy tables from explicit Gibbs free energies and explicit
  pH, potential, and correction terms;
- conformer selection by a chosen electronic or Gibbs energy field.

Use separate commands for electronic and Gibbs quantities:

```bash
qchemwb reaction-table pathway.yaml results.json --quantity electronic --out reaction_table.csv
qchemwb adsorption-table adsorption.yaml results.json --quantity gibbs --out adsorption_table.csv
qchemwb che-table che_pathway.yaml results.json --out che_table.csv
```
