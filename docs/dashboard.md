# Dashboard

qchem-workbench includes an optional Streamlit dashboard for read-only project
review. It is intended for academic meetings and workflow supervision: loaded
files, result summaries, quality checks, structures, analysis CSVs,
microkinetic outputs, and active-learning tables can be browsed without running
external electronic-structure codes.

The dashboard does not implement DFT, validate scientific correctness, choose
settings, optimise structures, or run calculations.

## Installation

Streamlit is not a base dependency:

```bash
python -m pip install -e ".[dashboard]"
```

The base test suite does not require Streamlit. Dashboard data-loading helpers
are pure Python and are tested without importing Streamlit.

## Launch

Launch from a project manifest:

```bash
qchemwb dashboard --project examples/dashboard_demo/qchem_project.yaml
```

Or load one or more result stores directly:

```bash
qchemwb dashboard --results results/results.json
```

The dashboard is read-only by default. It does not mutate project files.

## Report Export

Writing a Markdown dashboard summary is an explicit action:

```bash
qchemwb dashboard-report --project examples/dashboard_demo/qchem_project.yaml --out reports/dashboard_report.md
```

Inside Streamlit, the report download button creates a Markdown file in the
browser session. It uses the same shared report-building function as the CLI.

## Supported Views

- Project overview and loaded file paths.
- Result count, species count, backend/method/basis summaries, and missing data.
- Quality checks grouped by severity, plus failed-calculation rows.
- Molecular result and parsed-property tables with units in column names.
- Reaction, adsorption, and CHE CSV tables, including incomplete rows and
  visible CHE correction-term strings.
- Structure metadata summaries for species geometry paths.
- Microkinetic output tables when CSVs are supplied to the data loader.
- Active-learning dataset and campaign-state tables when supplied to the data
  loader.

## Limitations

- No external executable is bundled or launched.
- No 3D viewer dependency is required; structure summaries remain table-based.
- Missing optional files are shown as missing or warnings.
- Synthetic examples remain synthetic fixtures and are not scientific data.
- The dashboard helps review workflow state; it does not certify calculation
  quality, catalytic activity, selectivity, spectra, electrochemistry, or
  microkinetic validity.

See `examples/dashboard_demo/` for a minimal synthetic project.
