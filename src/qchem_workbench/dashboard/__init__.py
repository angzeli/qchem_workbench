"""Optional Streamlit dashboard support for qchem-workbench."""

from qchem_workbench.dashboard.app import (
    DashboardConfig,
    MissingStreamlitError,
    load_dashboard_config,
    render_dashboard,
    run_dashboard,
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
    "adsorption_energy_rows",
    "backend_method_basis_rows",
    "che_correction_display_rows",
    "che_energy_rows",
    "failed_calculation_rows",
    "incomplete_analysis_rows",
    "loaded_file_rows",
    "load_dashboard_config",
    "load_dashboard_data",
    "missing_data_rows",
    "method_consistency_warnings",
    "molecular_property_rows",
    "molecular_result_rows",
    "overview_summary_rows",
    "quality_check_rows",
    "quality_summary_rows",
    "reaction_energy_rows",
    "render_dashboard",
    "run_dashboard",
    "table_rows_to_csv",
]
