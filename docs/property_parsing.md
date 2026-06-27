# Molecular Property Parsing

Gaussian and ORCA parsers can populate backend-independent molecular property
containers under `CalculationResult.properties`. These fields are optional.
Missing sections are normal and remain missing; malformed or ambiguous sections
produce parser warnings instead of fabricated values.

## Parser Capability Table

| Property family | Gaussian sections parsed | ORCA sections parsed | Container | Units |
| --- | --- | --- | --- | --- |
| Dipole moment | `Dipole moment` in Debye with `X`, `Y`, `Z`, and `Tot` values | `Total Dipole Moment (Debye)` and `Magnitude (Debye)` when printed | `DipoleMoment` | Debye |
| Population charges | Explicit `Mulliken`, `Lowdin`, `NPA`, or `Natural Population Analysis` charge tables | Explicit `Mulliken`, `Lowdin`/`Loewdin`, or `NPA` charge tables | `PopulationAnalysis`, `AtomicCharge` | elementary charge `e` |
| Molecular orbitals | `occ. eigenvalues --` and `virt. eigenvalues --`, including `Alpha`/`Beta` variants | `ORBITAL ENERGIES` or `ORBITALS` tables, including alpha/beta or spin-up/spin-down variants | `OrbitalTable`, `MolecularOrbital` | Hartree and eV |
| Vibrational modes | `Frequencies --`, `Red. masses --`, `Frc consts --`, `IR Inten --`, and `Raman Activ --` rows | `Frequencies --`, simple `n: value cm**-1` rows, and simple `IR SPECTRUM` rows | `VibrationalMode` | `cm^-1`, `km/mol`, `angstrom^4/amu`, `amu`, `mDyne/angstrom` |
| Excited states | TD-DFT-style `Excited State n:` summary lines and compact transition lines | `STATE n:` excited-state summary lines and compact transition lines | `ExcitedState` | eV, nm, dimensionless oscillator strength |

The table lists implemented best-effort parsing patterns, not a guarantee that
any production output contains these sections or that every backend version uses
the same formatting.

## Units And Conversions

- Dipole components and magnitudes are stored in Debye only when Debye values are
  printed.
- Atomic charges are stored in units of elementary charge `e`; charge schemes
  are kept separate.
- Gaussian orbital eigenvalues are treated as Hartree values and converted to eV
  with the tested Hartree-to-eV constant.
- ORCA orbital rows with both Hartree and eV columns preserve both values. Rows
  with one energy column are treated as Hartree and converted to eV.
- Excited-state wavelengths are parsed when printed. If the energy is available
  and the wavelength is absent, the parser computes wavelength in nm using the
  tested eV-nm conversion constant.
- Vibrational frequencies are stored in `cm^-1`. IR intensities, Raman
  activities, reduced masses, and force constants stay missing when their rows
  are absent.

## Caveats

Population-analysis charges are method- and scheme-dependent model quantities.
qchem-workbench stores them for inspection and comparison within an explicitly
documented workflow; it does not present them as direct observables.

HOMO, LUMO, and gap values are orbital-energy summaries. They are not redox
potentials, band edges, or activity descriptors unless a user applies and
documents additional analysis outside the parser.

Vibrational data are parsed from output text with method and source provenance.
The parser counts negative frequencies and stores mode metadata, but it does not
assign transition-state identity or validate whether a frequency calculation is
scientifically complete.

Excited-state summaries are parsed when TD-DFT-like sections are explicit.
Stored energies, wavelengths, oscillator strengths, and transition descriptions
are parser outputs, not experimental UV-vis predictions.

Committed parser fixtures and example result values are synthetic unless a file
explicitly states otherwise.

## Exporting Properties

Use `qchemwb export-properties` to write tidy CSV tables from a result store:

```bash
qchemwb export-properties results/results.json --out results/properties/
qchemwb export-properties results/results.json --type charges --out charges.csv
qchemwb export-properties results/results.json --type orbitals --out orbitals.csv
qchemwb export-properties results/results.json --type vibrations --out vibrations.csv
qchemwb export-properties results/results.json --type excitations --out excitations.csv
```

The directory form writes non-empty `dipoles.csv`, `charges.csv`,
`orbitals.csv`, `vibrations.csv`, and `excitations.csv` files. Each row includes
species, backend, method, basis, task, source path, and explicit unit columns
where applicable.
