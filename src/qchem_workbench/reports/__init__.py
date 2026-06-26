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
from qchem_workbench.reports.spectrum import (
    BroadenedSpectrum,
    SpectrumStick,
    broaden_stick_spectrum,
    plot_vibrational_spectrum,
    vibrational_sticks_from_result,
    write_broadened_spectrum_csv,
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
    "BroadenedSpectrum",
    "SpectrumStick",
    "TRIAGE_CATEGORIES",
    "TriageCategory",
    "broaden_stick_spectrum",
    "classify_triage_results",
    "generate_failed_jobs_markdown",
    "generate_markdown_report",
    "latex_escape",
    "pathway_plot_data",
    "plot_pathway_from_csv",
    "plot_vibrational_spectrum",
    "reaction_rows_to_csv",
    "reaction_rows_to_latex_tabular",
    "results_to_csv",
    "results_to_latex_tabular",
    "species_to_csv",
    "vibrational_sticks_from_result",
    "write_broadened_spectrum_csv",
    "write_failed_jobs_report",
    "write_markdown_report",
]
