"""Conservative CHE-style pathway bookkeeping."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.analysis.corrections import CorrectionTerm
from qchem_workbench.analysis.reactions import HARTREE_TO_KJ_MOL
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.units import HARTREE_TO_EV


CHE_SCHEMA_VERSION = 1
SUPPORTED_POTENTIAL_REFERENCES = ("SHE", "RHE", "user_defined")
DEFAULT_CHE_TEMPERATURE_K = 298.15
BOLTZMANN_EV_PER_K = 8.617333262145e-5
LN_10 = 2.302585092994046


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


@dataclass(frozen=True)
class CHEFreeEnergyRow:
    reaction_id: str
    label: str | None
    proton_electron_pairs: float
    potential_reference: str | None
    complete: bool
    uncorrected_delta_g_hartree: float | None
    uncorrected_delta_g_ev: float | None
    correction_terms: tuple[CorrectionTerm, ...]
    correction_total_eV: float
    corrected_delta_g_ev: float | None
    corrected_delta_g_kj_mol: float | None
    missing_species: tuple[str, ...]
    warnings: tuple[str, ...]
    notes: str | None = None


@dataclass(frozen=True)
class CHELimitingPotentialResult:
    complete: bool
    limiting_reaction_ids: tuple[str, ...]
    max_uphill_delta_g_ev: float | None
    limiting_potential_V: float | None
    reference_equilibrium_potential_V: float | None = None
    relative_to_reference_equilibrium_V: float | None = None
    incomplete_reactions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
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


def che_free_energy_table(
    pathway: CHEPathway, results: list[CalculationResult]
) -> list[CHEFreeEnergyRow]:
    """Compute CHE-style corrected free energies from explicit species Gibbs values.

    Sign convention for built-in bookkeeping terms:
    - potential term: ``-n * U`` eV, where ``n`` is proton_electron_pairs and
      ``U`` is potential_V versus the named reference;
    - pH term: ``n * k_B * T * ln(10) * pH`` eV.

    These terms are transparent bookkeeping only. Users remain responsible for
    choosing references and deciding whether this convention fits their system.
    """

    gibbs_by_species = {
        result.species_name: result.gibbs_free_energy_hartree for result in results
    }
    return [
        _che_free_energy_row(reaction, gibbs_by_species)
        for reaction in pathway.reactions
    ]


def _che_free_energy_row(
    reaction: CHEReaction, gibbs_by_species: dict[str, float | None]
) -> CHEFreeEnergyRow:
    correction_terms = _che_correction_terms(reaction)
    correction_total = sum(term.value_eV for term in correction_terms)
    warnings = tuple(
        warning for term in correction_terms for warning in term.warnings
    )
    missing_species = tuple(
        species_name
        for species_name in sorted(set(reaction.reactants) | set(reaction.products))
        if gibbs_by_species.get(species_name) is None
    )
    if missing_species:
        return CHEFreeEnergyRow(
            reaction_id=reaction.id,
            label=reaction.label,
            proton_electron_pairs=reaction.proton_electron_pairs,
            potential_reference=reaction.potential_reference,
            complete=False,
            uncorrected_delta_g_hartree=None,
            uncorrected_delta_g_ev=None,
            correction_terms=correction_terms,
            correction_total_eV=correction_total,
            corrected_delta_g_ev=None,
            corrected_delta_g_kj_mol=None,
            missing_species=missing_species,
            warnings=warnings,
            notes=reaction.notes,
        )

    delta_g_hartree = _stoichiometric_sum(reaction.products, gibbs_by_species) - (
        _stoichiometric_sum(reaction.reactants, gibbs_by_species)
    )
    delta_g_ev = delta_g_hartree * HARTREE_TO_EV
    corrected_delta_g_ev = delta_g_ev + correction_total
    return CHEFreeEnergyRow(
        reaction_id=reaction.id,
        label=reaction.label,
        proton_electron_pairs=reaction.proton_electron_pairs,
        potential_reference=reaction.potential_reference,
        complete=True,
        uncorrected_delta_g_hartree=delta_g_hartree,
        uncorrected_delta_g_ev=delta_g_ev,
        correction_terms=correction_terms,
        correction_total_eV=correction_total,
        corrected_delta_g_ev=corrected_delta_g_ev,
        corrected_delta_g_kj_mol=corrected_delta_g_ev * HARTREE_TO_KJ_MOL / HARTREE_TO_EV,
        missing_species=(),
        warnings=warnings,
        notes=reaction.notes,
    )


def che_limiting_potential(
    rows: list[CHEFreeEnergyRow],
    *,
    results: list[CalculationResult] | None = None,
    reference_equilibrium_potential_V: float | None = None,
) -> CHELimitingPotentialResult:
    if not rows:
        return CHELimitingPotentialResult(
            complete=False,
            limiting_reaction_ids=(),
            max_uphill_delta_g_ev=None,
            limiting_potential_V=None,
            reference_equilibrium_potential_V=reference_equilibrium_potential_V,
            warnings=("No CHE rows were provided.",),
            notes="Limiting potential was not computed.",
        )

    incomplete_reactions = tuple(
        row.reaction_id
        for row in rows
        if not row.complete or row.corrected_delta_g_ev is None
    )
    warnings = _limiting_potential_warnings(rows, results)
    if incomplete_reactions:
        return CHELimitingPotentialResult(
            complete=False,
            limiting_reaction_ids=(),
            max_uphill_delta_g_ev=None,
            limiting_potential_V=None,
            reference_equilibrium_potential_V=reference_equilibrium_potential_V,
            incomplete_reactions=incomplete_reactions,
            warnings=warnings,
            notes="Limiting potential was not computed because at least one step is incomplete.",
        )

    unsupported_rows = tuple(
        row.reaction_id for row in rows if row.proton_electron_pairs <= 0
    )
    if unsupported_rows:
        return CHELimitingPotentialResult(
            complete=False,
            limiting_reaction_ids=(),
            max_uphill_delta_g_ev=None,
            limiting_potential_V=None,
            reference_equilibrium_potential_V=reference_equilibrium_potential_V,
            warnings=(
                *warnings,
                "Limiting potential requires positive proton_electron_pairs for "
                f"each step; unsupported rows: {', '.join(unsupported_rows)}.",
            ),
            notes="No limiting potential was computed for non-electrochemical steps.",
        )

    max_uphill = max(float(row.corrected_delta_g_ev) for row in rows)
    limiting_rows = tuple(
        row for row in rows if abs(float(row.corrected_delta_g_ev) - max_uphill) < 1e-12
    )
    limiting_reaction_ids = tuple(row.reaction_id for row in limiting_rows)
    first_limiting_row = limiting_rows[0]
    limiting_potential = -max_uphill / first_limiting_row.proton_electron_pairs
    relative = (
        None
        if reference_equilibrium_potential_V is None
        else limiting_potential - reference_equilibrium_potential_V
    )
    return CHELimitingPotentialResult(
        complete=True,
        limiting_reaction_ids=limiting_reaction_ids,
        max_uphill_delta_g_ev=max_uphill,
        limiting_potential_V=limiting_potential,
        reference_equilibrium_potential_V=reference_equilibrium_potential_V,
        relative_to_reference_equilibrium_V=relative,
        warnings=warnings,
        notes=(
            "Limiting potential is computed from the maximum uphill corrected "
            "step as -Delta G_i / n_i. "
            "This is a transparent descriptor, not a definitive overpotential."
        ),
    )


def _limiting_potential_warnings(
    rows: list[CHEFreeEnergyRow],
    results: list[CalculationResult] | None,
) -> tuple[str, ...]:
    warnings: list[str] = []
    references = {
        row.potential_reference
        for row in rows
        if row.potential_reference is not None
    }
    if len(references) > 1:
        warnings.append("CHE rows use mixed potential references.")
    if results is not None and len(_result_setting_groups(results)) > 1:
        warnings.append(
            "CHE limiting-potential analysis uses mixed backend/method/basis/task "
            "settings; compare steps only after checking provenance."
        )
    return tuple(warnings)


def _result_setting_groups(
    results: list[CalculationResult],
) -> set[tuple[str, str | None, str | None, str | None]]:
    return {
        (result.backend, result.method, result.basis, result.task)
        for result in results
    }


def _che_correction_terms(reaction: CHEReaction) -> tuple[CorrectionTerm, ...]:
    terms = list(reaction.correction_terms)
    n_pairs = reaction.proton_electron_pairs
    if n_pairs != 0 and reaction.potential_V is not None:
        terms.append(
            CorrectionTerm(
                label="CHE potential correction",
                value_eV=-n_pairs * reaction.potential_V,
                sign_convention=(
                    "-n * U eV, where n is proton_electron_pairs and U is "
                    "potential_V versus potential_reference"
                ),
                source=f"CHE pathway potential versus {reaction.potential_reference}",
            )
        )
    if n_pairs != 0 and reaction.pH is not None:
        temperature = reaction.temperature_K or DEFAULT_CHE_TEMPERATURE_K
        terms.append(
            CorrectionTerm(
                label="CHE pH correction",
                value_eV=n_pairs * BOLTZMANN_EV_PER_K * temperature * LN_10 * reaction.pH,
                sign_convention=(
                    "n * k_B * T * ln(10) * pH eV, where n is "
                    "proton_electron_pairs"
                ),
                source=(
                    f"CHE pathway pH={reaction.pH:g}, temperature={temperature:g} K"
                ),
            )
        )
    return tuple(terms)


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


def _stoichiometric_sum(
    stoichiometry: dict[str, float], gibbs_by_species: dict[str, float | None]
) -> float:
    return sum(
        coefficient * float(gibbs_by_species[species_name])
        for species_name, coefficient in stoichiometry.items()
    )
