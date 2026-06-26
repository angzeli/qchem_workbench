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

Synthetic parser fixtures are provided under `examples/gaussian_parsing`,
`examples/orca_parsing`, and `examples/qe_parsing`.
