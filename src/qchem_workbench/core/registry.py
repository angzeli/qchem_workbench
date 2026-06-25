"""Species registry loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.core.geometry import read_xyz
from qchem_workbench.core.species import Species


SUPPORTED_SCHEMA_VERSION = 1


def load_species_registry(path: Path) -> list[Species]:
    registry_path = Path(path)
    data = _load_yaml_mapping(registry_path)

    schema_version = data.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"{registry_path}: unsupported schema_version {schema_version!r}; "
            f"expected {SUPPORTED_SCHEMA_VERSION}"
        )

    species_entries = data.get("species", [])
    if not isinstance(species_entries, list):
        raise ValueError(f"{registry_path}: species must be a list")

    seen_names: set[str] = set()
    species: list[Species] = []
    for index, entry in enumerate(species_entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"{registry_path}: species[{index}] must be a mapping")

        item = _build_species(registry_path, index, entry)
        if item.name in seen_names:
            raise ValueError(f"{registry_path}: duplicate species name {item.name!r}")

        read_xyz(item.geometry_path)
        seen_names.add(item.name)
        species.append(item)

    return species


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: registry must be a mapping")
    return data


def _build_species(path: Path, index: int, entry: dict[str, Any]) -> Species:
    name = _required(path, index, entry, "name")
    charge = _required(path, index, entry, "charge")
    multiplicity = _required(path, index, entry, "multiplicity")
    geometry_value = _required(path, index, entry, "geometry_path")

    if not isinstance(geometry_value, str):
        raise ValueError(f"{path}: species[{index}].geometry_path must be a string")
    geometry_path = Path(geometry_value)
    if not geometry_path.is_absolute():
        geometry_path = path.parent / geometry_path
    if not geometry_path.exists():
        raise ValueError(f"{path}: missing geometry file {geometry_path}")

    return Species(
        name=_string_or_error(path, index, "name", name),
        formula=_optional_string(path, index, "formula", entry.get("formula")),
        charge=_int_or_error(path, index, "charge", charge),
        multiplicity=_int_or_error(path, index, "multiplicity", multiplicity),
        geometry_path=geometry_path,
        tags=_tags_or_error(path, index, entry.get("tags", [])),
        metadata=_metadata_or_error(path, index, entry.get("metadata", {})),
        notes=_optional_string(path, index, "notes", entry.get("notes")),
    )


def _required(path: Path, index: int, entry: dict[str, Any], key: str) -> Any:
    if key not in entry:
        raise ValueError(f"{path}: species[{index}].{key} is required")
    return entry[key]


def _string_or_error(path: Path, index: int, key: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{path}: species[{index}].{key} must be a string")
    return value


def _optional_string(path: Path, index: int, key: str, value: Any) -> str | None:
    if value is None:
        return None
    return _string_or_error(path, index, key, value)


def _int_or_error(path: Path, index: int, key: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{path}: species[{index}].{key} must be an integer")
    return value


def _tags_or_error(path: Path, index: int, value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{path}: species[{index}].tags must be a list of strings")
    return tuple(value)


def _metadata_or_error(path: Path, index: int, value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{path}: species[{index}].metadata must be a mapping")
    return dict(value)
