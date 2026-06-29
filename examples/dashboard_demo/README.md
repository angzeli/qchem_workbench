# Dashboard Demo

This example is a synthetic dashboard project for checking the optional
Streamlit interface and dashboard data-loading layer. The results, reaction
table, adsorption table, and active-learning rows are synthetic fixtures for
workflow review only. They are not scientific claims or production calculation
outputs.

Install the optional dashboard extra before launching Streamlit:

```bash
python -m pip install -e ".[dashboard]"
qchemwb dashboard --project qchem_project.yaml
```

The dashboard is read-only by default. It summarizes loaded files, result
quality, molecular results, structure metadata, and any analysis CSVs supplied
to the data loader. To write a Markdown summary explicitly:

```bash
qchemwb dashboard-report --project qchem_project.yaml --out dashboard_report.md
```

No Gaussian, ORCA, Quantum ESPRESSO, PySCF, ASE, or BO Forge executable is
required for this demo.
