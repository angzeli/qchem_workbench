"""Optional Streamlit dashboard skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    render_dashboard(streamlit, config)


def render_dashboard(st: Any, config: DashboardConfig) -> None:
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


def _import_streamlit() -> Any:
    try:
        import streamlit as st
    except ImportError as exc:
        raise MissingStreamlitError(
            "Streamlit dashboard support is optional. Install it with "
            "`pip install qchem-workbench[dashboard]`."
        ) from exc
    return st


def _path_text(path: Path | None) -> str:
    return str(path) if path is not None else "N/A"
