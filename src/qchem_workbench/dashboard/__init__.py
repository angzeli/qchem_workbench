"""Optional Streamlit dashboard support for qchem-workbench."""

from qchem_workbench.dashboard.app import (
    DashboardConfig,
    MissingStreamlitError,
    load_dashboard_config,
    render_dashboard,
    run_dashboard,
)
from qchem_workbench.dashboard.active_learning import (
    active_learning_dataset_rows,
    active_learning_missing_descriptor_rows,
    active_learning_objective_rows,
    active_learning_proposal_rows,
    active_learning_quality_flag_rows,
    active_learning_ranking_rows,
    active_learning_state_rows,
    active_learning_transition_rows,
)
from qchem_workbench.dashboard.data import (
    DashboardData,
    DashboardFileProvenance,
    DashboardSection,
    load_dashboard_data,
)
from qchem_workbench.dashboard.molecular import (
    PROPERTY_TABLE_TYPES,
    molecular_property_rows,
    molecular_result_rows,
    table_rows_to_csv,
)
from qchem_workbench.dashboard.microkinetics import (
    final_coverage_rows,
    load_microkinetic_network_rows,
    microkinetic_network_rows,
    microkinetic_output_sections,
    steady_state_warning_rows,
)
from qchem_workbench.dashboard.overview import (
    backend_method_basis_rows,
    loaded_file_rows,
    missing_data_rows,
    overview_summary_rows,
)
from qchem_workbench.dashboard.quality import (
    failed_calculation_rows,
    quality_check_rows,
    quality_summary_rows,
)
from qchem_workbench.dashboard.report import (
    generate_dashboard_markdown_report,
    write_dashboard_markdown_report,
)
from qchem_workbench.dashboard.structures import (
    dashboard_structure_rows,
    formula_from_atoms,
    structure_summary_from_xyz,
    structure_summary_rows,
)
from qchem_workbench.dashboard.workflows import (
    adsorption_energy_rows,
    che_correction_display_rows,
    che_energy_rows,
    incomplete_analysis_rows,
    method_consistency_warnings,
    reaction_energy_rows,
)

__all__ = [
    "DashboardConfig",
    "DashboardData",
    "DashboardFileProvenance",
    "DashboardSection",
    "MissingStreamlitError",
    "PROPERTY_TABLE_TYPES",
    "active_learning_dataset_rows",
    "active_learning_missing_descriptor_rows",
    "active_learning_objective_rows",
    "active_learning_proposal_rows",
    "active_learning_quality_flag_rows",
    "active_learning_ranking_rows",
    "active_learning_state_rows",
    "active_learning_transition_rows",
    "adsorption_energy_rows",
    "backend_method_basis_rows",
    "che_correction_display_rows",
    "che_energy_rows",
    "dashboard_structure_rows",
    "failed_calculation_rows",
    "final_coverage_rows",
    "formula_from_atoms",
    "generate_dashboard_markdown_report",
    "incomplete_analysis_rows",
    "loaded_file_rows",
    "load_dashboard_config",
    "load_dashboard_data",
    "missing_data_rows",
    "method_consistency_warnings",
    "load_microkinetic_network_rows",
    "microkinetic_network_rows",
    "microkinetic_output_sections",
    "molecular_property_rows",
    "molecular_result_rows",
    "overview_summary_rows",
    "quality_check_rows",
    "quality_summary_rows",
    "reaction_energy_rows",
    "render_dashboard",
    "structure_summary_from_xyz",
    "structure_summary_rows",
    "run_dashboard",
    "steady_state_warning_rows",
    "table_rows_to_csv",
    "write_dashboard_markdown_report",
]
