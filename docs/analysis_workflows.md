# Analysis Workflows

qchem-workbench provides transparent bookkeeping utilities. It does not apply
hidden correction terms or infer mechanisms.
Surface adsorption and CHE-style outputs are bookkeeping aids that require
expert validation before scientific interpretation.

Implemented workflows include:

- reaction energy tables from explicit pathway stoichiometry;
- adsorption energy or adsorption free-energy tables from clean slab, isolated
  adsorbate, and combined slab+adsorbate result labels;
- CHE-style free-energy tables from explicit Gibbs free energies and explicit
  pH, potential, and correction terms;
- cutoff or k-point convergence tables from user-defined synthetic or parsed
  result sets;
- conformer selection by a chosen electronic or Gibbs energy field.

Use separate commands for electronic and Gibbs quantities:

```bash
qchemwb reaction-table pathway.yaml results.json --quantity electronic --out reaction_table.csv
qchemwb adsorption-table adsorption.yaml results.json --quantity gibbs --out adsorption_table.csv
qchemwb che-table che_pathway.yaml results.json --out che_table.csv
```

Plane-wave convergence studies are organisational tables, not automatic
production-setting selection. A synthetic QE-style study can be analysed with:

```bash
qchemwb convergence-table convergence.yaml results/qe_results.json --out results/convergence.csv
```

The convergence table marks differences relative to the user-provided tolerance
only. Missing results remain visible.
