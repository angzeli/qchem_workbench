"""Optional Streamlit dashboard skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qchem_workbench.dashboard.data import DashboardData, load_dashboard_data
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
from qchem_workbench.dashboard.structures import dashboard_structure_rows
from qchem_workbench.dashboard.workflows import (
    adsorption_energy_rows,
    che_correction_display_rows,
    che_energy_rows,
    incomplete_analysis_rows,
    method_consistency_warnings,
    reaction_energy_rows,
)
from qchem_workbench.projects.manifest import ProjectManifest, load_project_manifest


class MissingStreamlitError(RuntimeError):
    """Raised when the optional dashboard dependency is unavailable."""


@dataclass(frozen=True)
class DashboardConfig:
    """Resolved read-only dashboard startup configuration."""

    project_path: Path | None = None
    project_name: str | None = None
    species_path: Path | None = None
    results_paths: tuple[Path, ...] = ()
    report_path: Path | None = None
    loaded_file_paths: tuple[Path, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_path": str(self.project_path) if self.project_path else None,
            "project_name": self.project_name,
            "species_path": str(self.species_path) if self.species_path else None,
            "results_paths": [str(path) for path in self.results_paths],
            "report_path": str(self.report_path) if self.report_path else None,
            "loaded_file_paths": [str(path) for path in self.loaded_file_paths],
            "warnings": list(self.warnings),
        }


def load_dashboard_config(
    *,
    project: Path | None = None,
    results: tuple[Path, ...] | list[Path] = (),
) -> DashboardConfig:
    """Load read-only dashboard startup metadata.

    This function performs no calculations and does not import Streamlit.
    """

    if project is None and not results:
        raise ValueError("dashboard requires --project or at least one --results file")
    result_paths = tuple(Path(path) for path in results)
    warnings: list[str] = []
    loaded_paths: list[Path] = []
    manifest: ProjectManifest | None = None
    if project is not None:
        manifest = load_project_manifest(Path(project))
        loaded_paths.append(manifest.path)
        loaded_paths.append(manifest.species_path)
        if manifest.results_path is not None:
            result_paths = (*result_paths, manifest.results_path)
        if manifest.report_path is not None:
            loaded_paths.append(manifest.report_path)
        for pathway_path in manifest.pathway_paths:
            loaded_paths.append(pathway_path)
    for result_path in result_paths:
        loaded_paths.append(result_path)
        if not result_path.exists():
            warnings.append(f"result file is listed but does not exist: {result_path}")
    return DashboardConfig(
        project_path=manifest.path if manifest else None,
        project_name=manifest.name if manifest else None,
        species_path=manifest.species_path if manifest else None,
        results_paths=result_paths,
        report_path=manifest.report_path if manifest else None,
        loaded_file_paths=tuple(dict.fromkeys(loaded_paths)),
        warnings=tuple(warnings),
    )


def run_dashboard(
    *,
    project: Path | None = None,
    results: tuple[Path, ...] | list[Path] = (),
) -> None:
    """Render the Streamlit dashboard after lazy-importing Streamlit."""

    streamlit = _import_streamlit()
    config = load_dashboard_config(project=project, results=results)
    data = load_dashboard_data(project=project, results=results)
    render_dashboard(streamlit, config, data=data)


def render_dashboard(
    st: Any,
    config: DashboardConfig,
    *,
    data: DashboardData | None = None,
) -> None:
    """Render the initial read-only dashboard page with a Streamlit-like object."""

    st.set_page_config(page_title="qchem-workbench dashboard", layout="wide")
    st.title("qchem-workbench dashboard")
    st.caption(
        "Read-only project overview. qchem-workbench organizes workflow data and "
        "does not implement DFT."
    )
    st.subheader("Project summary")
    summary_rows = [
        {"item": "Project name", "value": config.project_name or "N/A"},
        {"item": "Project manifest", "value": _path_text(config.project_path)},
        {"item": "Species registry", "value": _path_text(config.species_path)},
        {"item": "Result files", "value": str(len(config.results_paths))},
        {"item": "Report path", "value": _path_text(config.report_path)},
    ]
    st.table(summary_rows)
    st.subheader("Loaded file paths")
    st.table([{"path": str(path)} for path in config.loaded_file_paths])
    if config.warnings:
        st.subheader("Warnings")
        st.table([{"warning": warning} for warning in config.warnings])
    if data is not None:
        st.header("Overview")
        st.table(overview_summary_rows(data))
        st.subheader("Loaded files")
        st.table(loaded_file_rows(data))
        st.subheader("Backend / method / basis summary")
        st.table(backend_method_basis_rows(data))
        missing_rows = missing_data_rows(data)
        if missing_rows:
            st.subheader("Missing data summary")
            st.table(missing_rows)

        st.header("Quality")
        st.table(quality_summary_rows(data))
        check_rows = quality_check_rows(data)
        if check_rows:
            st.subheader("Quality checks")
            st.table(check_rows)
        failed_rows = failed_calculation_rows(data)
        if failed_rows:
            st.subheader("Failed calculations")
            st.table(failed_rows)

        st.header("Molecular results")
        result_rows = molecular_result_rows(data)
        if result_rows:
            st.table(result_rows)
            st.download_button(
                "Download molecular results CSV",
                table_rows_to_csv(result_rows),
                file_name="qchemwb_molecular_results.csv",
                mime="text/csv",
            )
        else:
            st.caption("No molecular result rows are loaded.")

        st.header("Molecular properties")
        st.caption(
            "Property tables show parsed values only. Orbital energies are not "
            "redox potentials."
        )
        for property_type in PROPERTY_TABLE_TYPES:
            rows = molecular_property_rows(data, property_type)
            if rows:
                st.subheader(property_type.replace("_", " ").title())
                st.table(rows)
                st.download_button(
                    f"Download {property_type} CSV",
                    table_rows_to_csv(rows),
                    file_name=f"qchemwb_{property_type}.csv",
                    mime="text/csv",
                )

        st.header("Reaction, adsorption, and CHE analyses")
        reaction_rows = reaction_energy_rows(data)
        if reaction_rows:
            st.subheader("Reaction energies")
            st.table(reaction_rows)
            _render_analysis_warnings(st, "reaction energies", reaction_rows)
        adsorption_rows = adsorption_energy_rows(data)
        if adsorption_rows:
            st.subheader("Adsorption energies")
            st.table(adsorption_rows)
            _render_analysis_warnings(st, "adsorption energies", adsorption_rows)
        che_rows = che_energy_rows(data)
        if che_rows:
            st.subheader("CHE free energies")
            st.table(che_rows)
            st.subheader("CHE correction terms")
            st.table(che_correction_display_rows(data))
            _render_analysis_warnings(st, "CHE free energies", che_rows)

        structure_rows = dashboard_structure_rows(data)
        if structure_rows:
            st.header("Structure summaries")
            st.caption(
                "Structure display is read-only. Summaries are starting-point "
                "metadata, not geometry validation."
            )
            st.table(structure_rows)


def _import_streamlit() -> Any:
    try:
        import streamlit as st
    except ImportError as exc:
        raise MissingStreamlitError(
            "Streamlit dashboard support is optional. Install it with "
            "`pip install qchem-workbench[dashboard]`."
        ) from exc
    return st


def _render_analysis_warnings(st: Any, label: str, rows: list[dict[str, Any]]) -> None:
    incomplete = incomplete_analysis_rows(rows)
    if incomplete:
        st.subheader(f"Incomplete {label}")
        st.table(incomplete)
    consistency = method_consistency_warnings(rows, label=label)
    if consistency:
        st.subheader(f"Method consistency warnings for {label}")
        st.table(consistency)


def _path_text(path: Path | None) -> str:
    return str(path) if path is not None else "N/A"
