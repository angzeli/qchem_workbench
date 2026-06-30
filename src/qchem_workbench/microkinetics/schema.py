"""Versioned microkinetic reaction-network schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


MICROKINETIC_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SiteType:
    id: str
    total_sites: float | None = None
    unit: str | None = None
    notes: str | None = None
    provenance: str | None = None


@dataclass(frozen=True)
class MicrokineticSpecies:
    id: str
    phase: str
    site_type: str | None = None
    formula: str | None = None
    notes: str | None = None
    provenance: str | None = None


@dataclass(frozen=True)
class ElementaryStep:
    id: str
    reversible: bool
    reactants: dict[str, float]
    products: dict[str, float]
    rate_constant_forward: str
    rate_constant_reverse: str | None = None
    notes: str | None = None
    provenance: str | None = None


@dataclass(frozen=True)
class MicrokineticModel:
    name: str
    site_types: dict[str, SiteType]
    gas_species: dict[str, MicrokineticSpecies]
    surface_species: dict[str, MicrokineticSpecies]
    steps: tuple[ElementaryStep, ...]
    rate_parameter_ids: tuple[str, ...]
    declared_rate_parameter_ids: tuple[str, ...] = ()
    notes: str | None = None
    provenance: str | None = None
    source_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def species(self) -> dict[str, MicrokineticSpecies]:
        return {**self.gas_species, **self.surface_species}


def load_microkinetic_model(path: Path) -> MicrokineticModel:
    """Load and validate a versioned microkinetic model YAML file."""

    model_path = Path(path)
    data = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{model_path}: microkinetic model file must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != MICROKINETIC_SCHEMA_VERSION:
        raise ValueError(
            f"{model_path}: unsupported schema_version {schema_version!r}; "
            f"expected {MICROKINETIC_SCHEMA_VERSION}"
        )
    raw_model = data.get("microkinetic_model")
    if not isinstance(raw_model, dict):
        raise ValueError(f"{model_path}: microkinetic_model must be a mapping")

    site_types = _site_types(model_path, raw_model.get("site_types", []))
    gas_species, surface_species = _species(model_path, raw_model.get("species", {}))
    _validate_surface_species_site_types(model_path, surface_species, site_types)
    steps = _steps(model_path, raw_model.get("steps", []))
    _validate_step_references(model_path, steps, gas_species, surface_species, site_types)
    _validate_site_bookkeeping(model_path, steps, surface_species, site_types)

    declared_parameter_ids = _declared_rate_parameter_ids(raw_model.get("rate_parameters"))
    rate_parameter_ids = _step_rate_parameter_ids(steps)
    if declared_parameter_ids:
        missing = sorted(set(rate_parameter_ids) - set(declared_parameter_ids))
        if missing:
            raise ValueError(
                f"{model_path}: missing rate parameter definition(s): "
                + ", ".join(missing)
            )

    name = _required_str(model_path, raw_model, "name")
    return MicrokineticModel(
        name=name,
        site_types=site_types,
        gas_species=gas_species,
        surface_species=surface_species,
        steps=tuple(steps),
        rate_parameter_ids=tuple(rate_parameter_ids),
        declared_rate_parameter_ids=tuple(sorted(declared_parameter_ids)),
        notes=_optional_str(raw_model.get("notes")),
        provenance=_optional_str(raw_model.get("provenance")),
        source_path=model_path,
        metadata=dict(raw_model.get("metadata", {}))
        if isinstance(raw_model.get("metadata", {}), dict)
        else {},
    )


def _site_types(path: Path, raw_site_types: Any) -> dict[str, SiteType]:
    if not isinstance(raw_site_types, list):
        raise ValueError(f"{path}: site_types must be a list")
    site_types: dict[str, SiteType] = {}
    duplicates: set[str] = set()
    for raw in raw_site_types:
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: each site_types entry must be a mapping")
        site_id = _required_str(path, raw, "id")
        if site_id in site_types:
            duplicates.add(site_id)
        total_sites = raw.get("total_sites")
        if total_sites is not None:
            if not isinstance(total_sites, (int, float)) or total_sites <= 0:
                raise ValueError(f"{path}: site type {site_id!r} total_sites must be positive")
            total_sites = float(total_sites)
        site_types[site_id] = SiteType(
            id=site_id,
            total_sites=total_sites,
            unit=_optional_str(raw.get("unit")),
            notes=_optional_str(raw.get("notes")),
            provenance=_optional_str(raw.get("provenance")),
        )
    if duplicates:
        raise ValueError(f"{path}: duplicate site type ID(s): {', '.join(sorted(duplicates))}")
    return site_types


def _species(
    path: Path,
    raw_species: Any,
) -> tuple[dict[str, MicrokineticSpecies], dict[str, MicrokineticSpecies]]:
    if not isinstance(raw_species, dict):
        raise ValueError(f"{path}: species must be a mapping")
    gas = _species_group(path, raw_species.get("gas", {}), "gas")
    surface = _species_group(path, raw_species.get("surface", {}), "surface")
    duplicates = sorted(set(gas) & set(surface))
    if duplicates:
        raise ValueError(f"{path}: duplicate species ID(s): {', '.join(duplicates)}")
    return gas, surface


def _species_group(
    path: Path,
    raw_group: Any,
    expected_phase: str,
) -> dict[str, MicrokineticSpecies]:
    if raw_group is None:
        return {}
    if not isinstance(raw_group, dict):
        raise ValueError(f"{path}: species.{expected_phase} must be a mapping")
    species: dict[str, MicrokineticSpecies] = {}
    for species_id, raw in raw_group.items():
        if not isinstance(species_id, str) or not species_id.strip():
            raise ValueError(f"{path}: species IDs must be non-empty strings")
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: species {species_id!r} entry must be a mapping")
        phase = raw.get("phase", expected_phase)
        if phase != expected_phase:
            raise ValueError(
                f"{path}: species {species_id!r} phase {phase!r} does not match "
                f"{expected_phase!r}"
            )
        species[species_id] = MicrokineticSpecies(
            id=species_id,
            phase=expected_phase,
            formula=_optional_str(raw.get("formula")),
            site_type=_optional_str(raw.get("site_type")),
            notes=_optional_str(raw.get("notes")),
            provenance=_optional_str(raw.get("provenance")),
        )
    return species


def _steps(path: Path, raw_steps: Any) -> list[ElementaryStep]:
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError(f"{path}: steps must be a non-empty list")
    steps: list[ElementaryStep] = []
    duplicates: set[str] = set()
    seen: set[str] = set()
    for raw in raw_steps:
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: each step must be a mapping")
        step_id = _required_str(path, raw, "id")
        if step_id in seen:
            duplicates.add(step_id)
        seen.add(step_id)
        reversible = bool(raw.get("reversible", False))
        forward = _required_str(path, raw, "rate_constant_forward")
        reverse = _optional_str(raw.get("rate_constant_reverse"))
        if reversible and reverse is None:
            raise ValueError(f"{path}: reversible step {step_id!r} requires rate_constant_reverse")
        steps.append(
            ElementaryStep(
                id=step_id,
                reversible=reversible,
                reactants=_stoichiometry(path, step_id, raw.get("reactants", {}), "reactants"),
                products=_stoichiometry(path, step_id, raw.get("products", {}), "products"),
                rate_constant_forward=forward,
                rate_constant_reverse=reverse,
                notes=_optional_str(raw.get("notes")),
                provenance=_optional_str(raw.get("provenance")),
            )
        )
    if duplicates:
        raise ValueError(f"{path}: duplicate elementary step ID(s): {', '.join(sorted(duplicates))}")
    return steps


def _stoichiometry(
    path: Path,
    step_id: str,
    raw_side: Any,
    side_label: str,
) -> dict[str, float]:
    if not isinstance(raw_side, dict):
        raise ValueError(f"{path}: step {step_id!r} {side_label} must be a mapping")
    parsed: dict[str, float] = {}
    for species_id, coefficient in raw_side.items():
        if not isinstance(species_id, str) or not species_id.strip():
            raise ValueError(f"{path}: step {step_id!r} has an empty species/site ID")
        if not isinstance(coefficient, (int, float)) or coefficient <= 0:
            raise ValueError(
                f"{path}: step {step_id!r} coefficient for {species_id!r} "
                "must be a positive number"
            )
        parsed[species_id] = float(coefficient)
    return parsed


def _validate_surface_species_site_types(
    path: Path,
    surface_species: dict[str, MicrokineticSpecies],
    site_types: dict[str, SiteType],
) -> None:
    for species in surface_species.values():
        if species.site_type is None:
            raise ValueError(f"{path}: surface species {species.id!r} requires site_type")
        if species.site_type not in site_types:
            raise ValueError(
                f"{path}: surface species {species.id!r} references missing site type "
                f"{species.site_type!r}"
            )


def _validate_step_references(
    path: Path,
    steps: list[ElementaryStep],
    gas_species: dict[str, MicrokineticSpecies],
    surface_species: dict[str, MicrokineticSpecies],
    site_types: dict[str, SiteType],
) -> None:
    allowed = set(gas_species) | set(surface_species) | set(site_types)
    for step in steps:
        for species_id in set(step.reactants) | set(step.products):
            if species_id not in allowed:
                raise ValueError(
                    f"{path}: step {step.id!r} references unknown species/site "
                    f"{species_id!r}"
                )


def _validate_site_bookkeeping(
    path: Path,
    steps: list[ElementaryStep],
    surface_species: dict[str, MicrokineticSpecies],
    site_types: dict[str, SiteType],
) -> None:
    for step in steps:
        reactant_sites = _site_counts(step.reactants, surface_species, site_types)
        product_sites = _site_counts(step.products, surface_species, site_types)
        if reactant_sites != product_sites:
            raise ValueError(
                f"{path}: step {step.id!r} does not conserve explicitly modelled sites"
            )


def _site_counts(
    stoichiometry: dict[str, float],
    surface_species: dict[str, MicrokineticSpecies],
    site_types: dict[str, SiteType],
) -> dict[str, float]:
    counts: dict[str, float] = {}
    for species_id, coefficient in stoichiometry.items():
        site_type = None
        if species_id in surface_species:
            site_type = surface_species[species_id].site_type
        elif species_id in site_types:
            site_type = species_id
        if site_type is not None:
            counts[site_type] = counts.get(site_type, 0.0) + coefficient
    return counts


def _declared_rate_parameter_ids(raw_parameters: Any) -> set[str]:
    if raw_parameters is None:
        return set()
    if isinstance(raw_parameters, list):
        return {str(item) for item in raw_parameters}
    if isinstance(raw_parameters, dict):
        declared: set[str] = set()
        for key, value in raw_parameters.items():
            if isinstance(value, dict):
                declared.add(str(key))
            elif isinstance(value, list):
                declared.update(str(item) for item in value)
            else:
                declared.add(str(key))
        return declared
    raise ValueError("rate_parameters must be a mapping or list when provided")


def _step_rate_parameter_ids(steps: list[ElementaryStep]) -> list[str]:
    ids: set[str] = set()
    for step in steps:
        ids.add(step.rate_constant_forward)
        if step.rate_constant_reverse is not None:
            ids.add(step.rate_constant_reverse)
    return sorted(ids)


def _required_str(path: Path, data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {key} must be a non-empty string")
    return value.strip()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    stripped = value.strip()
    return stripped or None
