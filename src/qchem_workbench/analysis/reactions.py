"""Generic reaction and pathway analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.core.species import Species


PATHWAY_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Reaction:
    id: str
    label: str | None
    reactants: dict[str, float]
    products: dict[str, float]
    electrons: float = 0.0
    protons: float = 0.0
    notes: str | None = None


@dataclass(frozen=True)
class Pathway:
    reactions: tuple[Reaction, ...]


def load_pathway(path: Path, species_registry: list[Species] | None = None) -> Pathway:
    pathway_path = Path(path)
    data = _load_yaml_mapping(pathway_path)

    schema_version = data.get("schema_version")
    if schema_version != PATHWAY_SCHEMA_VERSION:
        raise ValueError(
            f"{pathway_path}: unsupported schema_version {schema_version!r}; "
            f"expected {PATHWAY_SCHEMA_VERSION}"
        )

    reaction_entries = data.get("reactions", [])
    if not isinstance(reaction_entries, list):
        raise ValueError(f"{pathway_path}: reactions must be a list")

    reactions = tuple(
        _build_reaction(pathway_path, index, entry)
        for index, entry in enumerate(reaction_entries, start=1)
    )
    _validate_unique_reaction_ids(pathway_path, reactions)
    if species_registry is not None:
        _validate_referenced_species(pathway_path, reactions, species_registry)
    return Pathway(reactions=reactions)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: pathway must be a mapping")
    return data


def _build_reaction(path: Path, index: int, entry: Any) -> Reaction:
    if not isinstance(entry, dict):
        raise ValueError(f"{path}: reactions[{index}] must be a mapping")

    reaction_id = _required_string(path, index, entry, "id")
    reactants = _stoichiometry(path, index, entry, "reactants")
    products = _stoichiometry(path, index, entry, "products")
    return Reaction(
        id=reaction_id,
        label=_optional_string(path, index, entry, "label"),
        reactants=reactants,
        products=products,
        electrons=_optional_number(path, index, entry, "electrons", 0.0),
        protons=_optional_number(path, index, entry, "protons", 0.0),
        notes=_optional_string(path, index, entry, "notes"),
    )


def _stoichiometry(
    path: Path, index: int, entry: dict[str, Any], key: str
) -> dict[str, float]:
    value = entry.get(key)
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{path}: reactions[{index}].{key} must be a nonempty mapping")

    coefficients: dict[str, float] = {}
    for species_name, coefficient in value.items():
        if not isinstance(species_name, str) or not species_name.strip():
            raise ValueError(
                f"{path}: reactions[{index}].{key} contains an invalid species name"
            )
        coefficients[species_name] = _number_or_error(
            path, index, f"{key}.{species_name}", coefficient
        )
    return coefficients


def _validate_unique_reaction_ids(path: Path, reactions: tuple[Reaction, ...]) -> None:
    seen: set[str] = set()
    for reaction in reactions:
        if reaction.id in seen:
            raise ValueError(f"{path}: duplicate reaction id {reaction.id!r}")
        seen.add(reaction.id)


def _validate_referenced_species(
    path: Path, reactions: tuple[Reaction, ...], species_registry: list[Species]
) -> None:
    known_species = {species.name for species in species_registry}
    for reaction in reactions:
        referenced_species = set(reaction.reactants) | set(reaction.products)
        missing_species = sorted(referenced_species - known_species)
        if missing_species:
            raise ValueError(
                f"{path}: reaction {reaction.id!r} references unknown species "
                f"{', '.join(missing_species)}"
            )


def _required_string(path: Path, index: int, entry: dict[str, Any], key: str) -> str:
    if key not in entry:
        raise ValueError(f"{path}: reactions[{index}].{key} is required")
    value = entry[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: reactions[{index}].{key} must be a nonempty string")
    return value


def _optional_string(
    path: Path, index: int, entry: dict[str, Any], key: str
) -> str | None:
    value = entry.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{path}: reactions[{index}].{key} must be a string")
    return value


def _optional_number(
    path: Path, index: int, entry: dict[str, Any], key: str, default: float
) -> float:
    if key not in entry:
        return default
    return _number_or_error(path, index, key, entry[key])


def _number_or_error(path: Path, index: int, key: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path}: reactions[{index}].{key} must be a number")
    return float(value)
