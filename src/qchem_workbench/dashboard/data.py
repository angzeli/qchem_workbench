"""Pure data-loading helpers for the optional dashboard."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from qchem_workbench.active_learning.state import load_campaign_state, state_summary
from qchem_workbench.analysis.quality_checks import run_quality_checks
from qchem_workbench.core.registry import load_species_registry
from qchem_workbench.projects.manifest import ProjectManifest, load_project_manifest
from qchem_workbench.results.store import load_result_collection


@dataclass(frozen=True)
class DashboardFileProvenance:
    label: str
    path: Path
    status: str
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "path": str(self.path),
            "status": self.status,
            "message": self.message,
        }


@dataclass(frozen=True)
class DashboardSection:
    name: str
    kind: str
    rows: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "rows": list(self.rows),
            "metadata": dict(self.metadata),
            "source_path": str(self.source_path) if self.source_path else None,
        }


@dataclass(frozen=True)
class DashboardData:
    project_name: str | None = None
    project_path: Path | None = None
    loaded_sections: tuple[DashboardSection, ...] = ()
    missing_sections: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    file_provenance: tuple[DashboardFileProvenance, ...] = ()

    def section(self, name: str) -> DashboardSection | None:
        for section in self.loaded_sections:
            if section.name == name:
                return section
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_path": str(self.project_path) if self.project_path else None,
            "loaded_sections": [section.to_dict() for section in self.loaded_sections],
            "missing_sections": list(self.missing_sections),
            "warnings": list(self.warnings),
            "file_provenance": [item.to_dict() for item in self.file_provenance],
        }


def load_dashboard_data(
    *,
    project: Path | None = None,
    results: Iterable[Path] = (),
    species: Path | None = None,
    pathway_tables: Iterable[Path] = (),
    adsorption_tables: Iterable[Path] = (),
    che_tables: Iterable[Path] = (),
    microkinetic_outputs: Iterable[Path] = (),
    active_learning_datasets: Iterable[Path] = (),
    active_learning_state: Path | None = None,
) -> DashboardData:
    """Load dashboard sections without importing Streamlit or running analyses."""

    warnings: list[str] = []
    missing: list[str] = []
    provenance: list[DashboardFileProvenance] = []
    sections: list[DashboardSection] = []
    manifest: ProjectManifest | None = None
    result_paths = list(results)
    species_path = species

    if project is not None:
        manifest = _load_project(project, warnings, provenance)
        if manifest is not None:
            species_path = species_path or manifest.species_path
            if manifest.results_path is not None:
                result_paths.append(manifest.results_path)

    if species_path is not None:
        _load_species_section(species_path, sections, missing, warnings, provenance)

    for index, result_path in enumerate(result_paths, start=1):
        _load_result_section(
            result_path,
            f"results[{index}]",
            sections,
            missing,
            warnings,
            provenance,
        )

    _load_csv_sections("pathway_table", pathway_tables, sections, missing, warnings, provenance)
    _load_csv_sections("adsorption_table", adsorption_tables, sections, missing, warnings, provenance)
    _load_csv_sections("che_table", che_tables, sections, missing, warnings, provenance)
    _load_csv_sections(
        "microkinetic_output",
        microkinetic_outputs,
        sections,
        missing,
        warnings,
        provenance,
    )
    _load_csv_sections(
        "active_learning_dataset",
        active_learning_datasets,
        sections,
        missing,
        warnings,
        provenance,
    )
    if active_learning_state is not None:
        _load_active_learning_state(
            active_learning_state,
            sections,
            missing,
            warnings,
            provenance,
        )

    return DashboardData(
        project_name=manifest.name if manifest else None,
        project_path=manifest.path if manifest else None,
        loaded_sections=tuple(sections),
        missing_sections=tuple(missing),
        warnings=tuple(warnings),
        file_provenance=tuple(provenance),
    )


def _load_project(
    path: Path,
    warnings: list[str],
    provenance: list[DashboardFileProvenance],
) -> ProjectManifest | None:
    project_path = Path(path)
    try:
        manifest = load_project_manifest(project_path)
    except (OSError, ValueError) as exc:
        warnings.append(f"project manifest could not be loaded: {exc}")
        provenance.append(_provenance("project_manifest", project_path, "warning", str(exc)))
        return None
    provenance.append(_provenance("project_manifest", manifest.path, "loaded"))
    return manifest


def _load_species_section(
    path: Path,
    sections: list[DashboardSection],
    missing: list[str],
    warnings: list[str],
    provenance: list[DashboardFileProvenance],
) -> None:
    species_path = Path(path)
    if not species_path.exists():
        missing.append("species")
        provenance.append(_provenance("species", species_path, "missing"))
        return
    try:
        species = load_species_registry(species_path)
    except (OSError, ValueError) as exc:
        warnings.append(f"species registry could not be loaded: {exc}")
        provenance.append(_provenance("species", species_path, "warning", str(exc)))
        return
    sections.append(
        DashboardSection(
            name="species",
            kind="registry",
            rows=tuple(
                {
                    "name": item.name,
                    "formula": item.formula,
                    "charge": item.charge,
                    "multiplicity": item.multiplicity,
                    "geometry_path": str(item.geometry_path),
                }
                for item in species
            ),
            metadata={"count": len(species)},
            source_path=species_path,
        )
    )
    provenance.append(_provenance("species", species_path, "loaded"))


def _load_result_section(
    path: Path,
    label: str,
    sections: list[DashboardSection],
    missing: list[str],
    warnings: list[str],
    provenance: list[DashboardFileProvenance],
) -> None:
    result_path = Path(path)
    if not result_path.exists():
        missing.append(label)
        provenance.append(_provenance(label, result_path, "missing"))
        return
    try:
        results = load_result_collection(result_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        warnings.append(f"result store could not be loaded: {exc}")
        provenance.append(_provenance(label, result_path, "warning", str(exc)))
        return
    checks = run_quality_checks(results)
    sections.append(
        DashboardSection(
            name=label,
            kind="result_store",
            rows=tuple(result.to_dict() for result in results),
            metadata={
                "count": len(results),
                "quality_check_count": len(checks),
                "quality_error_count": sum(1 for check in checks if check.severity == "error"),
                "quality_warning_count": sum(
                    1 for check in checks if check.severity == "warning"
                ),
            },
            source_path=result_path,
        )
    )
    provenance.append(_provenance(label, result_path, "loaded"))


def _load_csv_sections(
    kind: str,
    paths: Iterable[Path],
    sections: list[DashboardSection],
    missing: list[str],
    warnings: list[str],
    provenance: list[DashboardFileProvenance],
) -> None:
    for index, path in enumerate(paths, start=1):
        label = f"{kind}[{index}]"
        csv_path = Path(path)
        if not csv_path.exists():
            missing.append(label)
            provenance.append(_provenance(label, csv_path, "missing"))
            continue
        try:
            rows = _read_csv_rows(csv_path)
        except OSError as exc:
            warnings.append(f"{label} could not be loaded: {exc}")
            provenance.append(_provenance(label, csv_path, "warning", str(exc)))
            continue
        sections.append(
            DashboardSection(
                name=label,
                kind=kind,
                rows=tuple(rows),
                metadata={"count": len(rows)},
                source_path=csv_path,
            )
        )
        provenance.append(_provenance(label, csv_path, "loaded"))


def _load_active_learning_state(
    path: Path,
    sections: list[DashboardSection],
    missing: list[str],
    warnings: list[str],
    provenance: list[DashboardFileProvenance],
) -> None:
    state_path = Path(path)
    if not state_path.exists():
        missing.append("active_learning_state")
        provenance.append(_provenance("active_learning_state", state_path, "missing"))
        return
    try:
        state = load_campaign_state(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        warnings.append(f"active-learning state could not be loaded: {exc}")
        provenance.append(
            _provenance("active_learning_state", state_path, "warning", str(exc))
        )
        return
    sections.append(
        DashboardSection(
            name="active_learning_state",
            kind="active_learning_state",
            rows=tuple(
                {"state": label, "count": count}
                for label, count in state_summary(state).items()
            ),
            metadata={"candidate_count": len(state.candidates)},
            source_path=state_path,
        )
    )
    provenance.append(_provenance("active_learning_state", state_path, "loaded"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _provenance(
    label: str,
    path: Path,
    status: str,
    message: str | None = None,
) -> DashboardFileProvenance:
    return DashboardFileProvenance(label=label, path=Path(path), status=status, message=message)
