"""Report-generation helpers for qchem-workbench."""

from qchem_workbench.reports.exports import (
    latex_escape,
    reaction_rows_to_csv,
    reaction_rows_to_latex_tabular,
    results_to_csv,
    results_to_latex_tabular,
    species_to_csv,
)
from qchem_workbench.reports.markdown import generate_markdown_report, write_markdown_report
from qchem_workbench.reports.plotting import (
    PathwayPlotData,
    pathway_plot_data,
    plot_pathway_from_csv,
)
from qchem_workbench.reports.triage import (
    TRIAGE_CATEGORIES,
    TriageCategory,
    classify_triage_results,
    generate_failed_jobs_markdown,
    write_failed_jobs_report,
)

__all__ = [
    "PathwayPlotData",
    "TRIAGE_CATEGORIES",
    "TriageCategory",
    "classify_triage_results",
    "generate_failed_jobs_markdown",
    "generate_markdown_report",
    "latex_escape",
    "pathway_plot_data",
    "plot_pathway_from_csv",
    "reaction_rows_to_csv",
    "reaction_rows_to_latex_tabular",
    "results_to_csv",
    "results_to_latex_tabular",
    "species_to_csv",
    "write_failed_jobs_report",
    "write_markdown_report",
]
