# Scientific Caveats

qchem-workbench is workflow software, not a DFT engine and not a substitute for
expert review.

- It does not choose exchange-correlation functionals, basis sets,
  pseudopotentials, cutoffs, solvent models, or standard states.
- It does not run Gaussian, ORCA, or Quantum ESPRESSO.
- It does not invent thermochemical corrections or missing parsed values.
- It does not infer reaction mechanisms, adsorption sites, catalytic activity,
  selectivity, or experimental validation.
- It keeps electronic energies, Gibbs free energies, correction terms,
  adsorption energies, and CHE-corrected free energies explicitly separated.

Committed parser outputs and screening values in examples are synthetic fixtures
for command validation and documentation.
