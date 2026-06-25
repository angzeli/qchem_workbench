"""Generic reaction and pathway analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species
from qchem_workbench.core.units import HARTREE_TO_EV


PATHWAY_SCHEMA_VERSION = 1
HARTREE_TO_KJ_MOL = 2625.4996394799


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


@dataclass(frozen=True)
class ReactionEnergyRow:
    reaction_id: str
    label: str | None
    quantity: str
    delta_hartree: float | None
    delta_ev: float | None
    delta_kj_mol: float | None
    complete: bool
    missing_species: tuple[str, ...]
    notes: str | None = None


def load_pathway(path: Path, species_registry: list[Species] | None = None) -> Pathway:
    pathway_path = Path(path)
    data = _load_yaml_mapping(pathway_path)

    if "schema_version" not in data:
        raise ValueError(f"{pathway_path}: missing schema_version")
    schema_version = data["schema_version"]
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


def reaction_electronic_energy_table(
    pathway: Pathway, results: list[CalculationResult]
) -> list[ReactionEnergyRow]:
    energy_by_species = {
        result.species_name: result.electronic_energy_hartree for result in results
    }
    return [
        _reaction_energy_row(
            reaction,
            energy_by_species,
            quantity="delta_e_electronic",
            notes="Sign convention: products minus reactants.",
        )
        for reaction in pathway.reactions
    ]


def reaction_gibbs_free_energy_table(
    pathway: Pathway, results: list[CalculationResult]
) -> list[ReactionEnergyRow]:
    energy_by_species = {
        result.species_name: result.gibbs_free_energy_hartree for result in results
    }
    return [
        _reaction_energy_row(
            reaction,
            energy_by_species,
            quantity="delta_g_gibbs",
            notes=(
                "Sign convention: products minus reactants. No standard-state or "
                "electrochemical corrections applied."
            ),
        )
        for reaction in pathway.reactions
    ]


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


def _reaction_energy_row(
    reaction: Reaction,
    energy_by_species: dict[str, float | None],
    quantity: str,
    notes: str | None,
) -> ReactionEnergyRow:
    missing_species = tuple(
        species_name
        for species_name in sorted(set(reaction.reactants) | set(reaction.products))
        if energy_by_species.get(species_name) is None
    )
    if missing_species:
        return ReactionEnergyRow(
            reaction_id=reaction.id,
            label=reaction.label,
            quantity=quantity,
            delta_hartree=None,
            delta_ev=None,
            delta_kj_mol=None,
            complete=False,
            missing_species=missing_species,
            notes=notes,
        )

    delta_hartree = _stoichiometric_sum(reaction.products, energy_by_species) - (
        _stoichiometric_sum(reaction.reactants, energy_by_species)
    )
    return ReactionEnergyRow(
        reaction_id=reaction.id,
        label=reaction.label,
        quantity=quantity,
        delta_hartree=delta_hartree,
        delta_ev=delta_hartree * HARTREE_TO_EV,
        delta_kj_mol=delta_hartree * HARTREE_TO_KJ_MOL,
        complete=True,
        missing_species=(),
        notes=notes,
    )


def _stoichiometric_sum(
    stoichiometry: dict[str, float], energy_by_species: dict[str, float | None]
) -> float:
    return sum(
        coefficient * float(energy_by_species[species_name])
        for species_name, coefficient in stoichiometry.items()
    )
