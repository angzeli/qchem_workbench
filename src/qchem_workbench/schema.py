"""Schema detection and migration-check helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

from qchem_workbench.analysis.reactions import PATHWAY_SCHEMA_VERSION, load_pathway
from qchem_workbench.campaigns import CAMPAIGN_SCHEMA_VERSION, load_campaign_manifest
from qchem_workbench.core.registry import SUPPORTED_SCHEMA_VERSION, load_species_registry
from qchem_workbench.projects.manifest import (
    PROJECT_MANIFEST_SCHEMA_VERSION,
    load_project_manifest,
)
from qchem_workbench.results.store import (
    RESULT_COLLECTION_SCHEMA_VERSION,
    load_result_collection,
)


SCHEMA_FILE_TYPES = {
    "species_registry": SUPPORTED_SCHEMA_VERSION,
    "result_store": RESULT_COLLECTION_SCHEMA_VERSION,
    "pathway": PATHWAY_SCHEMA_VERSION,
    "project_manifest": PROJECT_MANIFEST_SCHEMA_VERSION,
    "campaign": CAMPAIGN_SCHEMA_VERSION,
}

__all__ = [
    "SCHEMA_FILE_TYPES",
    "SchemaCheckReport",
    "SchemaMigrationStatus",
    "check_schema_file",
]


@dataclass(frozen=True)
class SchemaMigrationStatus:
    """Migration status for a schema file check."""

    available: bool
    required: bool
    write_requested: bool
    changed: bool
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "required": self.required,
            "write_requested": self.write_requested,
            "changed": self.changed,
            "message": self.message,
        }


@dataclass(frozen=True)
class SchemaCheckReport:
    """Schema check result for one file."""

    path: Path
    file_type: str | None
    schema_version: Any
    valid: bool
    problems: tuple[str, ...]
    migration: SchemaMigrationStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "file_type": self.file_type,
            "schema_version": self.schema_version,
            "valid": self.valid,
            "problems": list(self.problems),
            "migration": self.migration.to_dict(),
        }


def check_schema_file(path: Path, *, write: bool = False) -> SchemaCheckReport:
    """Detect, validate, and report schema information for *path*."""

    input_path = Path(path)
    problems: list[str] = []
    try:
        data = _load_mapping(input_path)
    except (OSError, ValueError) as exc:
        return SchemaCheckReport(
            path=input_path,
            file_type=None,
            schema_version=None,
            valid=False,
            problems=(str(exc),),
            migration=_migration_status(None, None, write),
        )

    file_type = _detect_file_type(data)
    schema_version = data.get("schema_version")
    if file_type is None:
        problems.append("could not detect schema file type")
    if schema_version is None:
        problems.append("missing schema_version")

    if file_type is not None and schema_version is not None:
        expected_version = SCHEMA_FILE_TYPES[file_type]
        if schema_version != expected_version:
            problems.append(
                f"unsupported schema_version {schema_version!r}; "
                f"expected {expected_version}"
            )
        else:
            validator = _validator_for_type(file_type)
            try:
                validator(input_path)
            except (OSError, ValueError) as exc:
                problems.append(str(exc))

    migration = _migration_status(file_type, schema_version, write)
    return SchemaCheckReport(
        path=input_path,
        file_type=file_type,
        schema_version=schema_version,
        valid=not problems,
        problems=tuple(problems),
        migration=migration,
    )


def _load_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML/JSON") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: schema file must be a mapping/object")
    return data


def _detect_file_type(data: dict[str, Any]) -> str | None:
    if "project" in data:
        return "project_manifest"
    if "campaign" in data:
        return "campaign"
    if "species" in data:
        return "species_registry"
    if "reactions" in data:
        return "pathway"
    if "results" in data:
        return "result_store"
    return None


def _validator_for_type(file_type: str) -> Callable[[Path], object]:
    validators: dict[str, Callable[[Path], object]] = {
        "species_registry": load_species_registry,
        "result_store": load_result_collection,
        "pathway": load_pathway,
        "project_manifest": load_project_manifest,
        "campaign": load_campaign_manifest,
    }
    return validators[file_type]


def _migration_status(
    file_type: str | None,
    schema_version: Any,
    write: bool,
) -> SchemaMigrationStatus:
    if file_type is None or schema_version is None:
        return SchemaMigrationStatus(
            available=False,
            required=False,
            write_requested=write,
            changed=False,
            message="No migration available until file type and schema_version are known.",
        )

    current_version = SCHEMA_FILE_TYPES[file_type]
    if schema_version == current_version:
        return SchemaMigrationStatus(
            available=False,
            required=False,
            write_requested=write,
            changed=False,
            message=(
                "No migration required."
                if not write
                else "No migration required; no file changes written."
            ),
        )

    return SchemaMigrationStatus(
        available=False,
        required=True,
        write_requested=write,
        changed=False,
        message=(
            f"No migration is implemented from schema_version {schema_version!r} "
            f"to {current_version}. Comments are not rewritten."
        ),
    )
