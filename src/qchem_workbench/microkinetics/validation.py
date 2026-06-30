"""Conservative validation checks for microkinetic models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Mapping

from qchem_workbench.microkinetics.parameters import RateParameterSet
from qchem_workbench.microkinetics.schema import (
    ElementaryStep,
    MicrokineticModel,
    MicrokineticSpecies,
    SiteType,
)


ValidationSeverity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class MicrokineticValidationCheck:
    code: str
    severity: ValidationSeverity
    message: str
    identifier: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "identifier": self.identifier,
        }


@dataclass(frozen=True)
class MicrokineticValidationReport:
    model_name: str
    checks: tuple[MicrokineticValidationCheck, ...]

    @property
    def error_count(self) -> int:
        return sum(check.severity == "error" for check in self.checks)

    @property
    def warning_count(self) -> int:
        return sum(check.severity == "warning" for check in self.checks)

    @property
    def valid(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "valid": self.valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "checks": [check.to_dict() for check in self.checks],
        }


def validate_microkinetic_model(
    model: MicrokineticModel,
    *,
    parameters: RateParameterSet | None = None,
    initial_coverages: Mapping[str, float] | None = None,
) -> MicrokineticValidationReport:
    """Run conservative microkinetic model checks without inferring chemistry."""

    checks: list[MicrokineticValidationCheck] = []
    checks.extend(_site_total_checks(model))
    checks.extend(_step_definition_checks(model))
    checks.extend(_reference_checks(model))
    checks.extend(_site_balance_checks(model))
    checks.extend(_elemental_balance_checks(model))
    checks.extend(_disconnected_species_checks(model))
    checks.extend(_rate_parameter_checks(model, parameters))
    if initial_coverages is not None:
        checks.extend(_initial_coverage_checks(model, initial_coverages))
    return MicrokineticValidationReport(model_name=model.name, checks=tuple(checks))


def _site_total_checks(model: MicrokineticModel) -> list[MicrokineticValidationCheck]:
    checks: list[MicrokineticValidationCheck] = []
    for site_id, site_type in model.site_types.items():
        if site_type.total_sites is not None and site_type.total_sites < 0:
            checks.append(
                _check(
                    "negative_site_total",
                    "error",
                    f"Site type {site_id!r} has negative total_sites.",
                    site_id,
                )
            )
    return checks


def _step_definition_checks(
    model: MicrokineticModel,
) -> list[MicrokineticValidationCheck]:
    checks: list[MicrokineticValidationCheck] = []
    signatures: dict[tuple[object, ...], str] = {}
    for step in model.steps:
        if not step.reactants:
            checks.append(
                _check(
                    "missing_reactants",
                    "error",
                    f"Elementary step {step.id!r} has no reactants.",
                    step.id,
                )
            )
        if not step.products:
            checks.append(
                _check(
                    "missing_products",
                    "error",
                    f"Elementary step {step.id!r} has no products.",
                    step.id,
                )
            )
        if step.reversible and step.rate_constant_reverse is None:
            checks.append(
                _check(
                    "reversible_step_missing_reverse_parameter",
                    "error",
                    f"Reversible step {step.id!r} has no reverse rate parameter.",
                    step.id,
                )
            )
        if not step.reversible and step.rate_constant_reverse is not None:
            checks.append(
                _check(
                    "irreversible_step_has_reverse_parameter",
                    "warning",
                    f"Irreversible step {step.id!r} declares a reverse parameter.",
                    step.id,
                )
            )
        signature = _step_signature(step)
        duplicate_of = signatures.get(signature)
        if duplicate_of is None:
            signatures[signature] = step.id
        else:
            checks.append(
                _check(
                    "duplicate_reaction",
                    "warning",
                    f"Step {step.id!r} duplicates stoichiometry of {duplicate_of!r}.",
                    step.id,
                )
            )
    return checks


def _reference_checks(model: MicrokineticModel) -> list[MicrokineticValidationCheck]:
    checks: list[MicrokineticValidationCheck] = []
    known_ids = set(model.species) | set(model.site_types)
    for step in model.steps:
        referenced_ids = set(step.reactants) | set(step.products)
        for species_id in sorted(referenced_ids - known_ids):
            checks.append(
                _check(
                    "undefined_species_or_site",
                    "error",
                    f"Step {step.id!r} references undefined "
                    f"species/site {species_id!r}.",
                    step.id,
                )
            )
    for species in model.surface_species.values():
        if species.site_type is not None and species.site_type not in model.site_types:
            checks.append(
                _check(
                    "undefined_site_type",
                    "error",
                    f"Surface species {species.id!r} references undefined "
                    f"site type {species.site_type!r}.",
                    species.id,
                )
            )
    return checks


def _site_balance_checks(model: MicrokineticModel) -> list[MicrokineticValidationCheck]:
    checks: list[MicrokineticValidationCheck] = []
    for step in model.steps:
        reactant_sites = _site_counts(
            step.reactants,
            model.surface_species,
            model.site_types,
        )
        product_sites = _site_counts(
            step.products,
            model.surface_species,
            model.site_types,
        )
        if reactant_sites != product_sites:
            checks.append(
                _check(
                    "site_imbalance",
                    "error",
                    f"Step {step.id!r} does not conserve explicitly modelled sites.",
                    step.id,
                )
            )
    return checks


def _elemental_balance_checks(
    model: MicrokineticModel,
) -> list[MicrokineticValidationCheck]:
    checks: list[MicrokineticValidationCheck] = []
    for step in model.steps:
        species_ids = [
            species_id
            for species_id in set(step.reactants) | set(step.products)
            if species_id not in model.site_types
        ]
        if any(species_id not in model.species for species_id in species_ids):
            continue
        missing = [
            species_id
            for species_id in sorted(species_ids)
            if model.species[species_id].formula is None
        ]
        if missing:
            checks.append(
                _check(
                    "missing_formula_for_elemental_balance",
                    "warning",
                    "Elemental balance was not checked for step "
                    f"{step.id!r}; missing formula(s): {', '.join(missing)}.",
                    step.id,
                )
            )
            continue
        try:
            reactants = _element_counts(step.reactants, model.species, model.site_types)
            products = _element_counts(step.products, model.species, model.site_types)
        except ValueError as exc:
            checks.append(
                _check("invalid_formula", "warning", str(exc), step.id)
            )
            continue
        if reactants != products:
            checks.append(
                _check(
                    "elemental_imbalance",
                    "error",
                    f"Step {step.id!r} does not conserve elements from formulas.",
                    step.id,
                )
            )
    return checks


def _disconnected_species_checks(
    model: MicrokineticModel,
) -> list[MicrokineticValidationCheck]:
    referenced: set[str] = set()
    for step in model.steps:
        referenced.update(step.reactants)
        referenced.update(step.products)
    checks: list[MicrokineticValidationCheck] = []
    for species_id in sorted(set(model.species) - referenced):
        checks.append(
            _check(
                "disconnected_species",
                "warning",
                f"Species {species_id!r} is defined but not used in any step.",
                species_id,
            )
        )
    return checks


def _rate_parameter_checks(
    model: MicrokineticModel,
    parameters: RateParameterSet | None,
) -> list[MicrokineticValidationCheck]:
    checks: list[MicrokineticValidationCheck] = []
    required = set(model.rate_parameter_ids)
    declared = set(model.declared_rate_parameter_ids)
    for parameter_id in sorted(declared - required):
        checks.append(
            _check(
                "unused_declared_rate_parameter",
                "warning",
                f"Declared rate parameter {parameter_id!r} is not used by any step.",
                parameter_id,
            )
        )
    if parameters is None:
        if not declared and required:
            checks.append(
                _check(
                    "missing_rate_parameter_definitions",
                    "warning",
                    "Model references rate parameters but no parameter set "
                    "was supplied.",
                    "rate_parameters",
                )
            )
        return checks

    available = set(parameters.parameter_ids)
    for parameter_id in sorted(required - available):
        checks.append(
            _check(
                "missing_rate_constant",
                "error",
                f"Rate parameter {parameter_id!r} is required but not defined.",
                parameter_id,
            )
        )
    for parameter_id in sorted(available - required):
        checks.append(
            _check(
                "unused_rate_parameter",
                "warning",
                f"Rate parameter {parameter_id!r} is defined but not used.",
                parameter_id,
            )
        )
    checks.extend(_rate_unit_checks(model, parameters))
    return checks


def _rate_unit_checks(
    model: MicrokineticModel,
    parameters: RateParameterSet,
) -> list[MicrokineticValidationCheck]:
    checks: list[MicrokineticValidationCheck] = []
    for step in model.steps:
        if step.rate_constant_reverse is None:
            continue
        forward_unit = _parameter_unit(parameters, step.rate_constant_forward)
        reverse_unit = _parameter_unit(parameters, step.rate_constant_reverse)
        if forward_unit is None or reverse_unit is None:
            continue
        if forward_unit != reverse_unit:
            checks.append(
                _check(
                    "inconsistent_rate_units",
                    "warning",
                    f"Step {step.id!r} forward and reverse parameters use "
                    f"different units: {forward_unit!r} vs {reverse_unit!r}.",
                    step.id,
                )
            )
    return checks


def _initial_coverage_checks(
    model: MicrokineticModel,
    initial_coverages: Mapping[str, float],
) -> list[MicrokineticValidationCheck]:
    checks: list[MicrokineticValidationCheck] = []
    dynamic = _dynamic_variable_ids(model)
    missing = sorted(dynamic - set(initial_coverages))
    for species_id in missing:
        checks.append(
            _check(
                "missing_initial_coverage",
                "error",
                f"Initial coverage for {species_id!r} is missing.",
                species_id,
            )
        )
    for species_id, value in initial_coverages.items():
        if species_id not in dynamic:
            continue
        if not isinstance(value, (int, float)):
            checks.append(
                _check(
                    "invalid_initial_coverage",
                    "error",
                    f"Initial coverage for {species_id!r} is not numeric.",
                    species_id,
                )
            )
        elif float(value) < 0:
            checks.append(
                _check(
                    "negative_initial_coverage",
                    "error",
                    f"Initial coverage for {species_id!r} is negative.",
                    species_id,
                )
            )
    checks.extend(_initial_site_total_checks(model, initial_coverages))
    return checks


def _initial_site_total_checks(
    model: MicrokineticModel,
    initial_coverages: Mapping[str, float],
) -> list[MicrokineticValidationCheck]:
    checks: list[MicrokineticValidationCheck] = []
    for site_id, site_type in model.site_types.items():
        if site_type.total_sites is None:
            continue
        occupied = 0.0
        invalid_component = False
        site_coverage = initial_coverages.get(site_id, 0.0)
        if isinstance(site_coverage, (int, float)):
            occupied += float(site_coverage)
        else:
            invalid_component = True
        for species in model.surface_species.values():
            if species.site_type == site_id:
                species_coverage = initial_coverages.get(species.id, 0.0)
                if isinstance(species_coverage, (int, float)):
                    occupied += float(species_coverage)
                else:
                    invalid_component = True
        if invalid_component:
            continue
        if occupied > site_type.total_sites + 1e-12:
            checks.append(
                _check(
                    "initial_coverage_exceeds_site_total",
                    "error",
                    f"Initial coverages for site type {site_id!r} sum to "
                    f"{occupied:g}, above total_sites {site_type.total_sites:g}.",
                    site_id,
                )
            )
    return checks


def _check(
    code: str,
    severity: ValidationSeverity,
    message: str,
    identifier: str,
) -> MicrokineticValidationCheck:
    return MicrokineticValidationCheck(
        code=code,
        severity=severity,
        message=message,
        identifier=identifier,
    )


def _step_signature(step: ElementaryStep) -> tuple[object, ...]:
    return (
        tuple(sorted(step.reactants.items())),
        tuple(sorted(step.products.items())),
        step.reversible,
    )


def _site_counts(
    stoichiometry: Mapping[str, float],
    surface_species: Mapping[str, MicrokineticSpecies],
    site_types: Mapping[str, SiteType],
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


def _element_counts(
    stoichiometry: Mapping[str, float],
    species: Mapping[str, MicrokineticSpecies],
    site_types: Mapping[str, SiteType],
) -> dict[str, float]:
    counts: dict[str, float] = {}
    for species_id, coefficient in stoichiometry.items():
        if species_id in site_types:
            continue
        formula = species[species_id].formula
        assert formula is not None
        for element, count in _parse_formula(formula, species_id).items():
            counts[element] = counts.get(element, 0.0) + coefficient * count
    return {
        element: value
        for element, value in counts.items()
        if abs(value) > 1e-12
    }


def _parse_formula(formula: str, species_id: str) -> dict[str, float]:
    matches = list(re.finditer(r"([A-Z][a-z]?)([0-9]*(?:\.[0-9]+)?)", formula))
    if not matches or "".join(match.group(0) for match in matches) != formula:
        raise ValueError(
            f"Species {species_id!r} formula {formula!r} is not parseable."
        )
    counts: dict[str, float] = {}
    for match in matches:
        element = match.group(1)
        raw_count = match.group(2)
        count = float(raw_count) if raw_count else 1.0
        counts[element] = counts.get(element, 0.0) + count
    return counts


def _dynamic_variable_ids(model: MicrokineticModel) -> set[str]:
    referenced: set[str] = set()
    for step in model.steps:
        referenced.update(step.reactants)
        referenced.update(step.products)
    return (set(model.surface_species) | set(model.site_types)) & referenced


def _parameter_unit(parameters: RateParameterSet, parameter_id: str) -> str | None:
    if parameter_id in parameters.rate_constants:
        return parameters.rate_constants[parameter_id].unit
    if parameter_id in parameters.arrhenius:
        return parameters.arrhenius[parameter_id].pre_exponential_unit
    if parameter_id in parameters.eyring:
        return parameters.eyring[parameter_id].rate_constant_unit
    return None
