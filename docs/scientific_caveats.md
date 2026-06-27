# Scientific Caveats

qchem-workbench is workflow software, not a DFT engine and not a substitute for
expert review.

- It does not choose exchange-correlation functionals, basis sets,
  pseudopotentials, cutoffs, solvent models, or standard states.
- It does not run Gaussian, ORCA, or Quantum ESPRESSO.
- It does not invent thermochemical corrections or missing parsed values.
- It does not infer reaction mechanisms, adsorption sites, catalytic activity,
  selectivity, or experimental validation.
- It does not treat rule-based screening rankings as predictions of activity or
  experimental performance.
- It does not treat population-analysis charges as direct observables.
- It does not treat HOMO/LUMO orbital energies as redox potentials or band
  edges.
- It does not treat broadened vibrational or TD-DFT-derived spectra as
  experimental predictions.
- It keeps electronic energies, Gibbs free energies, correction terms,
  adsorption energies, and CHE-corrected free energies explicitly separated.

Committed parser outputs and screening values in examples are synthetic fixtures
for command validation and documentation.
