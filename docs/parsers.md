# Parsers

Parsers convert text outputs into `CalculationResult` objects. They are designed
to be conservative:

- incomplete files should not crash parsing;
- missing values remain missing;
- warnings explain missing or ambiguous fields;
- electronic energies, thermal corrections, Gibbs free energies, and reaction
  energies remain separate.

Implemented parsers:

- `qchemwb parse-gaussian` scans `.log` and `.out` files.
- `qchemwb parse-orca` scans `.out` files.
- `qchemwb parse-qe` scans `.out` and `.pwout` files.

Gaussian and ORCA parsers also populate optional molecular property containers
when explicit sections are present. Supported property families include dipole
moments, population-analysis charges, molecular orbital tables, vibrational
modes, and excited-state summaries. See
[`property_parsing.md`](property_parsing.md) for the exact supported sections,
units, conversions, and caveats.

Synthetic parser fixtures are provided under `examples/gaussian_parsing`,
`examples/orca_parsing`, and `examples/qe_parsing`.
