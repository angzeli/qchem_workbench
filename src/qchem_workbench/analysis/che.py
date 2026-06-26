"""Conservative CHE-style pathway bookkeeping."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.analysis.corrections import CorrectionTerm


CHE_SCHEMA_VERSION = 1
SUPPORTED_POTENTIAL_REFERENCES = ("SHE", "RHE", "user_defined")


@dataclass(frozen=True)
class CHEReaction:
    id: str
    label: str | None
    reactants: dict[str, float]
    products: dict[str, float]
    proton_electron_pairs: float
    pH: float | None = None
    potential_V: float | None = None
    potential_reference: str | None = None
    temperature_K: float | None = None
    correction_terms: tuple[CorrectionTerm, ...] = ()
    notes: str | None = None


@dataclass(frozen=True)
class CHEPathway:
    reactions: tuple[CHEReaction, ...]
    notes: str | None = None


def load_che_pathway(path: Path) -> CHEPathway:
    pathway_path = Path(path)
    data = _load_yaml_mapping(pathway_path)

    if "schema_version" not in data:
        raise ValueError(f"{pathway_path}: missing schema_version")
    schema_version = data["schema_version"]
    if schema_version != CHE_SCHEMA_VERSION:
        raise ValueError(
            f"{pathway_path}: unsupported schema_version {schema_version!r}; "
            f"expected {CHE_SCHEMA_VERSION}"
        )

    reaction_entries = data.get("reactions", [])
    if not isinstance(reaction_entries, list):
        raise ValueError(f"{pathway_path}: reactions must be a list")
    reactions = tuple(
        _build_che_reaction(pathway_path, index, entry)
        for index, entry in enumerate(reaction_entries, start=1)
    )
    _validate_unique_reaction_ids(pathway_path, reactions)
    return CHEPathway(
        reactions=reactions,
        notes=_optional_string(data, "notes", f"{pathway_path}: notes"),
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: CHE pathway must be a mapping")
    return data


def _build_che_reaction(path: Path, index: int, entry: Any) -> CHEReaction:
    if not isinstance(entry, dict):
        raise ValueError(f"{path}: reactions[{index}] must be a mapping")

    reaction_id = _required_string(entry, "id", f"{path}: reactions[{index}].id")
    potential_V = _optional_number(entry, "potential_V", f"{path}: reactions[{index}]")
    potential_reference = _optional_string(
        entry, "potential_reference", f"{path}: reactions[{index}].potential_reference"
    )
    _validate_potential_reference(path, index, potential_V, potential_reference)
    return CHEReaction(
        id=reaction_id,
        label=_optional_string(entry, "label", f"{path}: reactions[{index}].label"),
        reactants=_stoichiometry(path, index, entry, "reactants"),
        products=_stoichiometry(path, index, entry, "products"),
        proton_electron_pairs=_optional_number(
            entry,
            "proton_electron_pairs",
            f"{path}: reactions[{index}]",
            default=0.0,
        ),
        pH=_optional_number(entry, "pH", f"{path}: reactions[{index}]"),
        potential_V=potential_V,
        potential_reference=potential_reference,
        temperature_K=_optional_number(
            entry, "temperature_K", f"{path}: reactions[{index}]"
        ),
        correction_terms=_correction_terms(path, index, entry.get("correction_terms", [])),
        notes=_optional_string(entry, "notes", f"{path}: reactions[{index}].notes"),
    )


def _validate_potential_reference(
    path: Path,
    index: int,
    potential_V: float | None,
    potential_reference: str | None,
) -> None:
    if potential_V is None:
        return
    if potential_reference is None:
        raise ValueError(
            f"{path}: reactions[{index}].potential_reference is required when "
            "potential_V is set"
        )
    if potential_reference not in SUPPORTED_POTENTIAL_REFERENCES:
        allowed = ", ".join(SUPPORTED_POTENTIAL_REFERENCES)
        raise ValueError(
            f"{path}: reactions[{index}].potential_reference {potential_reference!r} "
            f"is unsupported; expected one of {allowed}"
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
            coefficient, f"{path}: reactions[{index}].{key}.{species_name}"
        )
    return coefficients


def _correction_terms(
    path: Path, index: int, entries: Any
) -> tuple[CorrectionTerm, ...]:
    if not isinstance(entries, list):
        raise ValueError(f"{path}: reactions[{index}].correction_terms must be a list")
    return tuple(
        _correction_term(path, index, term_index, entry)
        for term_index, entry in enumerate(entries, start=1)
    )


def _correction_term(
    path: Path, index: int, term_index: int, entry: Any
) -> CorrectionTerm:
    if not isinstance(entry, dict):
        raise ValueError(
            f"{path}: reactions[{index}].correction_terms[{term_index}] "
            "must be a mapping"
        )
    prefix = f"{path}: reactions[{index}].correction_terms[{term_index}]"
    return CorrectionTerm(
        label=_required_string(entry, "label", f"{prefix}.label"),
        value_eV=_number_or_error(entry.get("value_eV"), f"{prefix}.value_eV"),
        sign_convention=_required_string(
            entry, "sign_convention", f"{prefix}.sign_convention"
        ),
        source=_optional_string(entry, "source", f"{prefix}.source"),
        note=_optional_string(entry, "note", f"{prefix}.note"),
    )


def _validate_unique_reaction_ids(path: Path, reactions: tuple[CHEReaction, ...]) -> None:
    seen: set[str] = set()
    for reaction in reactions:
        if reaction.id in seen:
            raise ValueError(f"{path}: duplicate reaction id {reaction.id!r}")
        seen.add(reaction.id)


def _required_string(data: dict[str, Any], key: str, label: str) -> str:
    if key not in data:
        raise ValueError(f"{label} is required")
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _optional_string(data: dict[str, Any], key: str, label: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _optional_number(
    data: dict[str, Any], key: str, label: str, default: float | None = None
) -> float | None:
    if key not in data:
        return default
    return _number_or_error(data[key], f"{label}.{key}")


def _number_or_error(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    return float(value)
