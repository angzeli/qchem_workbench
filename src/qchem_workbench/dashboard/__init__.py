"""Optional Streamlit dashboard support for qchem-workbench."""

from qchem_workbench.dashboard.app import (
    DashboardConfig,
    MissingStreamlitError,
    load_dashboard_config,
    render_dashboard,
    run_dashboard,
)

__all__ = [
    "DashboardConfig",
    "MissingStreamlitError",
    "load_dashboard_config",
    "render_dashboard",
    "run_dashboard",
]
