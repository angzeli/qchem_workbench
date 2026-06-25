"""Optional project manifest loading for batch workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.core.calculation import CalculationSpec


PROJECT_MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProjectCalculationSettings:
    """Calculation settings declared in a project manifest."""

    backend: str | None = None
    method: str | None = None
    basis: str | None = None
    task: str | None = None
    solvent: str | None = None
    keywords: dict[str, Any] = field(default_factory=dict)
    route_keywords: tuple[str, ...] = ()

    def to_spec(self, default_backend: str | None = None) -> CalculationSpec:
        backend = self.backend or default_backend
        missing = [
            name
            for name, value in (
                ("backend", backend),
                ("method", self.method),
                ("task", self.task),
            )
            if value is None or value == ""
        ]
        if missing:
            raise ValueError(
                "manifest calculation settings missing required field(s): "
                + ", ".join(missing)
            )
        return CalculationSpec(
            backend=str(backend),
            method=str(self.method),
            basis=self.basis,
            task=str(self.task),
            solvent=self.solvent,
            keywords=dict(self.keywords),
        )


@dataclass(frozen=True)
class ProjectManifest:
    """Resolved project manifest paths and workflow settings."""

    path: Path
    name: str
    species_path: Path
    results_path: Path | None = None
    report_path: Path | None = None
    reaction_table_path: Path | None = None
    inputs_dir: Path | None = None
    outputs_dir: Path | None = None
    pathway_paths: tuple[Path, ...] = ()
    reaction_quantity: str | None = None
    backend_mode: str | None = None
    calculation: ProjectCalculationSettings = field(
        default_factory=ProjectCalculationSettings
    )
    steps: tuple[str, ...] = ()

    @property
    def root(self) -> Path:
        return self.path.parent


def load_project_manifest(path: Path) -> ProjectManifest:
    """Load and validate a qchem-workbench project manifest."""

    manifest_path = Path(path)
    data = _load_yaml_mapping(manifest_path)
    schema_version = data.get("schema_version")
    if schema_version != PROJECT_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"{manifest_path}: unsupported schema_version {schema_version!r}; "
            f"expected {PROJECT_MANIFEST_SCHEMA_VERSION}"
        )

    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError(f"{manifest_path}: project must be a mapping")

    species_path = _required_path(manifest_path, project, "species")
    _require_existing_file(manifest_path, species_path, "species")
    pathway_paths = _path_list(manifest_path, project.get("pathways", []), "pathways")
    for pathway_path in pathway_paths:
        _require_existing_file(manifest_path, pathway_path, "pathways")

    name = _optional_string(project, "name") or manifest_path.stem
    return ProjectManifest(
        path=manifest_path,
        name=name,
        species_path=species_path,
        results_path=_optional_path(manifest_path, project, "results"),
        report_path=_optional_path(manifest_path, project, "reports"),
        reaction_table_path=_optional_path(manifest_path, project, "reaction_table"),
        inputs_dir=_optional_path(manifest_path, project, "inputs"),
        outputs_dir=_optional_path(manifest_path, project, "outputs"),
        pathway_paths=pathway_paths,
        reaction_quantity=_optional_string(project, "reaction_quantity"),
        backend_mode=_optional_string(project, "backend_mode"),
        calculation=_calculation_settings(manifest_path, project.get("calculation", {})),
        steps=_string_tuple(manifest_path, project.get("steps", []), "steps"),
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest must be a mapping")
    return data


def _required_path(manifest_path: Path, project: dict[str, Any], key: str) -> Path:
    if key not in project:
        raise ValueError(f"{manifest_path}: project.{key} is required")
    return _resolve_path(manifest_path, project[key], f"project.{key}")


def _optional_path(
    manifest_path: Path, project: dict[str, Any], key: str
) -> Path | None:
    if key not in project or project[key] is None:
        return None
    return _resolve_path(manifest_path, project[key], f"project.{key}")


def _resolve_path(manifest_path: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{manifest_path}: {label} must be a nonempty path string")
    path = Path(value)
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path


def _path_list(manifest_path: Path, value: Any, label: str) -> tuple[Path, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return (_resolve_path(manifest_path, value, f"project.{label}"),)
    if not isinstance(value, list):
        raise ValueError(f"{manifest_path}: project.{label} must be a path or list")
    return tuple(
        _resolve_path(manifest_path, item, f"project.{label}[{index}]")
        for index, item in enumerate(value)
    )


def _string_tuple(manifest_path: Path, value: Any, label: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{manifest_path}: project.{label} must be a list")
    strings = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{manifest_path}: project.{label}[{index}] must be a nonempty string"
            )
        strings.append(item)
    return tuple(strings)


def _calculation_settings(
    manifest_path: Path, value: Any
) -> ProjectCalculationSettings:
    if value in (None, ""):
        value = {}
    if not isinstance(value, dict):
        raise ValueError(f"{manifest_path}: project.calculation must be a mapping")
    route_keywords = value.get("route_keywords", [])
    if route_keywords in (None, ""):
        route_keywords = []
    if not isinstance(route_keywords, (list, tuple)):
        raise ValueError(
            f"{manifest_path}: project.calculation.route_keywords must be a list"
        )
    for index, item in enumerate(route_keywords):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{manifest_path}: project.calculation.route_keywords[{index}] "
                "must be a nonempty string"
            )
    keywords = value.get("keywords", {})
    if keywords in (None, ""):
        keywords = {}
    if not isinstance(keywords, dict):
        raise ValueError(f"{manifest_path}: project.calculation.keywords must be a mapping")
    return ProjectCalculationSettings(
        backend=_optional_string(value, "backend"),
        method=_optional_string(value, "method"),
        basis=_optional_string(value, "basis"),
        task=_optional_string(value, "task"),
        solvent=_optional_string(value, "solvent"),
        keywords=dict(keywords),
        route_keywords=tuple(route_keywords),
    )


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _require_existing_file(manifest_path: Path, path: Path, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"{manifest_path}: referenced {label} file does not exist: {path}")
