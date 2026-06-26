"""Generic adsorption workflow schemas and analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ADSORPTION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class AdsorptionCalculationRef:
    id: str
    result: str
    role: str
    notes: str | None = None


@dataclass(frozen=True)
class AdsorptionSystem:
    id: str
    slab_result: str
    adsorbate_result: str
    combined_result: str
    notes: str | None = None


@dataclass(frozen=True)
class AdsorptionWorkflow:
    clean_slabs: tuple[AdsorptionCalculationRef, ...]
    isolated_adsorbates: tuple[AdsorptionCalculationRef, ...]
    slab_adsorbates: tuple[AdsorptionCalculationRef, ...]
    adsorption_systems: tuple[AdsorptionSystem, ...]


def load_adsorption_workflow(path: Path) -> AdsorptionWorkflow:
    workflow_path = Path(path)
    data = _load_yaml_mapping(workflow_path)

    if "schema_version" not in data:
        raise ValueError(f"{workflow_path}: missing schema_version")
    schema_version = data["schema_version"]
    if schema_version != ADSORPTION_SCHEMA_VERSION:
        raise ValueError(
            f"{workflow_path}: unsupported schema_version {schema_version!r}; "
            f"expected {ADSORPTION_SCHEMA_VERSION}"
        )

    clean_slabs = _calculation_refs(
        workflow_path,
        data,
        preferred_key="clean_slab_calculations",
        alias_key="clean_slabs",
        role="clean_slab",
    )
    isolated_adsorbates = _calculation_refs(
        workflow_path,
        data,
        preferred_key="isolated_adsorbate_calculations",
        alias_key="isolated_adsorbates",
        role="isolated_adsorbate",
    )
    slab_adsorbates = _calculation_refs(
        workflow_path,
        data,
        preferred_key="slab_adsorbate_calculations",
        alias_key="slab_adsorbates",
        role="slab_adsorbate",
    )
    systems = _adsorption_systems(workflow_path, data.get("adsorption_systems", []))
    _validate_unique_ids(
        workflow_path,
        [system.id for system in systems],
        "adsorption system",
    )
    _validate_system_result_references(
        workflow_path,
        systems,
        clean_slabs=clean_slabs,
        isolated_adsorbates=isolated_adsorbates,
        slab_adsorbates=slab_adsorbates,
    )
    return AdsorptionWorkflow(
        clean_slabs=clean_slabs,
        isolated_adsorbates=isolated_adsorbates,
        slab_adsorbates=slab_adsorbates,
        adsorption_systems=systems,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: adsorption workflow must be a mapping")
    return data


def _calculation_refs(
    path: Path,
    data: dict[str, Any],
    *,
    preferred_key: str,
    alias_key: str,
    role: str,
) -> tuple[AdsorptionCalculationRef, ...]:
    entries = data.get(preferred_key, data.get(alias_key, []))
    if not isinstance(entries, list):
        raise ValueError(f"{path}: {preferred_key} must be a list")

    refs = tuple(
        _calculation_ref(path, preferred_key, index, entry, role)
        for index, entry in enumerate(entries, start=1)
    )
    _validate_unique_ids(path, [ref.id for ref in refs], role)
    return refs


def _calculation_ref(
    path: Path, section: str, index: int, entry: Any, role: str
) -> AdsorptionCalculationRef:
    if not isinstance(entry, dict):
        raise ValueError(f"{path}: {section}[{index}] must be a mapping")
    ref_id = _required_string(path, f"{section}[{index}].id", entry.get("id"))
    result = _optional_string(entry.get("result")) or ref_id
    return AdsorptionCalculationRef(
        id=ref_id,
        result=result,
        role=role,
        notes=_optional_string(entry.get("notes")),
    )


def _adsorption_systems(
    path: Path, entries: Any
) -> tuple[AdsorptionSystem, ...]:
    if not isinstance(entries, list):
        raise ValueError(f"{path}: adsorption_systems must be a list")
    return tuple(
        _adsorption_system(path, index, entry)
        for index, entry in enumerate(entries, start=1)
    )


def _adsorption_system(path: Path, index: int, entry: Any) -> AdsorptionSystem:
    if not isinstance(entry, dict):
        raise ValueError(f"{path}: adsorption_systems[{index}] must be a mapping")
    prefix = f"adsorption_systems[{index}]"
    return AdsorptionSystem(
        id=_required_string(path, f"{prefix}.id", entry.get("id")),
        slab_result=_required_string(
            path, f"{prefix}.slab_result", entry.get("slab_result")
        ),
        adsorbate_result=_required_string(
            path, f"{prefix}.adsorbate_result", entry.get("adsorbate_result")
        ),
        combined_result=_required_string(
            path, f"{prefix}.combined_result", entry.get("combined_result")
        ),
        notes=_optional_string(entry.get("notes")),
    )


def _validate_system_result_references(
    path: Path,
    systems: tuple[AdsorptionSystem, ...],
    *,
    clean_slabs: tuple[AdsorptionCalculationRef, ...],
    isolated_adsorbates: tuple[AdsorptionCalculationRef, ...],
    slab_adsorbates: tuple[AdsorptionCalculationRef, ...],
) -> None:
    if not (clean_slabs or isolated_adsorbates or slab_adsorbates):
        return

    clean_results = {ref.result for ref in clean_slabs} | {ref.id for ref in clean_slabs}
    adsorbate_results = {ref.result for ref in isolated_adsorbates} | {
        ref.id for ref in isolated_adsorbates
    }
    combined_results = {ref.result for ref in slab_adsorbates} | {
        ref.id for ref in slab_adsorbates
    }
    for system in systems:
        missing: list[str] = []
        if system.slab_result not in clean_results:
            missing.append(f"slab_result {system.slab_result!r}")
        if system.adsorbate_result not in adsorbate_results:
            missing.append(f"adsorbate_result {system.adsorbate_result!r}")
        if system.combined_result not in combined_results:
            missing.append(f"combined_result {system.combined_result!r}")
        if missing:
            raise ValueError(
                f"{path}: adsorption system {system.id!r} references missing "
                + ", ".join(missing)
            )


def _validate_unique_ids(path: Path, ids: list[str], label: str) -> None:
    seen: set[str] = set()
    for item_id in ids:
        if item_id in seen:
            raise ValueError(f"{path}: duplicate {label} id {item_id!r}")
        seen.add(item_id)


def _required_string(path: Path, field: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {field} must be a nonempty string")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional text fields must be strings")
    return value
