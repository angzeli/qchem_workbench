# Release Checklist

Use this checklist before tagging or publishing a qchem-workbench release.

## Tests

- Run `python -m pytest`.
- Confirm optional PySCF tests skip cleanly when PySCF is not installed.
- Confirm no test requires Gaussian or other licensed software.

## Lint And Type Checks

- Run configured lint, format, and type-check commands if they have been added.
- If no commands are configured, note that explicitly in the release notes.

## README Command Verification

- Verify README CLI commands match `qchemwb --help`.
- Run the basic molecule validate, render, parse, and report example commands.
- Run the CO2RR molecular validate, render, parse, reaction-table, and report
  example commands against synthetic fixtures.

## Example Workflow Validation

- Validate every committed species registry.
- Validate every committed pathway YAML.
- Confirm synthetic outputs are clearly labelled as synthetic.
- Confirm generated outputs are not accidentally committed unless they are
  intentional fixtures or documentation examples.

## Result Schema Review

- Review `CalculationResult` fields for backward compatibility.
- Confirm electronic energies, thermal corrections, Gibbs free energies, and
  reaction energies remain explicitly separated.
- Confirm missing fields remain missing rather than receiving placeholder
  scientific values.

## Parser Fixture Review

- Confirm parser fixtures cover normal termination, error termination, missing
  energies, thermochemistry, frequencies, spin lines, and malformed cases.
- Confirm fixture energies and outputs are synthetic where applicable.
- Confirm parser warnings are preserved in result JSON.

## Scientific Caveat Audit

- Check README, examples, and reports for overclaiming.
- Confirm no documentation implies qchem-workbench replaces DFT engines or
  licensed quantum-chemistry software.
- Confirm domain examples, including CO2RR, are labelled as illustrative when
  they are not complete mechanisms.

## Changelog Update

- Update the changelog or release notes with user-facing changes.
- Mention new commands, schema changes, examples, and any compatibility notes.
- Record test commands and outcomes used for the release.
