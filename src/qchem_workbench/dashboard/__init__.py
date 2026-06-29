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

__all__ = [
    "DashboardConfig",
    "DashboardData",
    "DashboardFileProvenance",
    "DashboardSection",
    "MissingStreamlitError",
    "PROPERTY_TABLE_TYPES",
    "backend_method_basis_rows",
    "failed_calculation_rows",
    "loaded_file_rows",
    "load_dashboard_config",
    "load_dashboard_data",
    "missing_data_rows",
    "molecular_property_rows",
    "molecular_result_rows",
    "overview_summary_rows",
    "quality_check_rows",
    "quality_summary_rows",
    "render_dashboard",
    "run_dashboard",
    "table_rows_to_csv",
]
