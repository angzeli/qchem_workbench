"""Mass-action rate expressions for validated microkinetic networks."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from qchem_workbench.microkinetics.parameters import RateParameterSet
from qchem_workbench.microkinetics.schema import ElementaryStep, MicrokineticModel


@dataclass(frozen=True)
class StepRate:
    step_id: str
    forward_rate: float
    reverse_rate: float
    net_rate: float
    unit: str | None = None

    def to_dict(self) -> dict[str, float | str | None]:
        return {
            "step_id": self.step_id,
            "forward_rate": self.forward_rate,
            "reverse_rate": self.reverse_rate,
            "net_rate": self.net_rate,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class SpeciesProductionRate:
    species_id: str
    phase: str
    net_rate: float
    unit: str | None = None

    def to_dict(self) -> dict[str, float | str | None]:
        return {
            "species_id": self.species_id,
            "phase": self.phase,
            "net_rate": self.net_rate,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class MicrokineticRateAnalysis:
    step_rates: tuple[StepRate, ...]
    species_rates: tuple[SpeciesProductionRate, ...]
    tof_species: str | None = None
    turnover_frequency: float | None = None
    turnover_frequency_unit: str | None = None
    active_site_count: float | None = None
    warnings: tuple[str, ...] = ()

    def to_rows(self) -> list[dict[str, str | float | None]]:
        rows: list[dict[str, str | float | None]] = []
        for row in self.step_rates:
            rows.append(
                {
                    "row_type": "step",
                    "id": row.step_id,
                    "phase": None,
                    "rate": row.net_rate,
                    "forward_rate": row.forward_rate,
                    "reverse_rate": row.reverse_rate,
                    "unit": row.unit,
                    "active_site_count": None,
                    "notes": None,
                }
            )
        for row in self.species_rates:
            rows.append(
                {
                    "row_type": "species",
                    "id": row.species_id,
                    "phase": row.phase,
                    "rate": row.net_rate,
                    "forward_rate": None,
                    "reverse_rate": None,
                    "unit": row.unit,
                    "active_site_count": None,
                    "notes": None,
                }
            )
        if self.tof_species is not None:
            rows.append(
                {
                    "row_type": "tof",
                    "id": self.tof_species,
                    "phase": None,
                    "rate": self.turnover_frequency,
                    "forward_rate": None,
                    "reverse_rate": None,
                    "unit": self.turnover_frequency_unit,
                    "active_site_count": self.active_site_count,
                    "notes": "TOF = net production rate / explicit active_site_count",
                }
            )
        return rows


@dataclass(frozen=True)
class SiteBalanceResidual:
    site_type: str
    total_sites: float
    occupied_sites: float
    residual: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "site_type": self.site_type,
            "total_sites": self.total_sites,
            "occupied_sites": self.occupied_sites,
            "residual": self.residual,
        }


@dataclass(frozen=True)
class RateEvaluator:
    model: MicrokineticModel
    parameters: RateParameterSet
    temperature_K: float | None = None

    @property
    def dynamic_variable_ids(self) -> tuple[str, ...]:
        referenced = set()
        for step in self.model.steps:
            referenced.update(step.reactants)
            referenced.update(step.products)
        dynamic = (set(self.model.surface_species) | set(self.model.site_types)) & referenced
        return tuple(sorted(dynamic))

    def step_rates(
        self,
        state: Mapping[str, float],
        conditions: Mapping[str, float],
    ) -> dict[str, StepRate]:
        rates: dict[str, StepRate] = {}
        for step in self.model.steps:
            forward_constant = self.parameters.evaluate(
                step.rate_constant_forward,
                temperature_K=self.temperature_K,
            )
            forward_rate = forward_constant.value * self._mass_action_factor(
                step,
                step.reactants,
                state,
                conditions,
            )
            reverse_rate = 0.0
            if step.reversible and step.rate_constant_reverse is not None:
                reverse_constant = self.parameters.evaluate(
                    step.rate_constant_reverse,
                    temperature_K=self.temperature_K,
                )
                reverse_rate = reverse_constant.value * self._mass_action_factor(
                    step,
                    step.products,
                    state,
                    conditions,
                )
            rates[step.id] = StepRate(
                step_id=step.id,
                forward_rate=forward_rate,
                reverse_rate=reverse_rate,
                net_rate=forward_rate - reverse_rate,
                unit=forward_constant.unit,
            )
        return rates

    def rate_vector(
        self,
        state: Mapping[str, float],
        conditions: Mapping[str, float],
    ) -> dict[str, float]:
        derivatives = {species_id: 0.0 for species_id in self.dynamic_variable_ids}
        step_rates = self.step_rates(state, conditions)
        for step in self.model.steps:
            net_rate = step_rates[step.id].net_rate
            for species_id, coefficient in step.reactants.items():
                if species_id in derivatives:
                    derivatives[species_id] -= coefficient * net_rate
            for species_id, coefficient in step.products.items():
                if species_id in derivatives:
                    derivatives[species_id] += coefficient * net_rate
        return derivatives

    def site_balance_residuals(
        self,
        state: Mapping[str, float],
    ) -> tuple[SiteBalanceResidual, ...]:
        residuals: list[SiteBalanceResidual] = []
        for site_id, site_type in self.model.site_types.items():
            if site_type.total_sites is None:
                continue
            occupied = _state_value(state, site_id)
            for species in self.model.surface_species.values():
                if species.site_type == site_id:
                    occupied += _state_value(state, species.id)
            residuals.append(
                SiteBalanceResidual(
                    site_type=site_id,
                    total_sites=site_type.total_sites,
                    occupied_sites=occupied,
                    residual=site_type.total_sites - occupied,
                )
            )
        return tuple(residuals)

    def site_balance_warnings(
        self,
        state: Mapping[str, float],
        *,
        tolerance: float = 1e-8,
    ) -> tuple[str, ...]:
        warnings = []
        for residual in self.site_balance_residuals(state):
            if abs(residual.residual) > tolerance:
                warnings.append(
                    f"site balance for {residual.site_type!r} differs from total_sites "
                    f"by {residual.residual:g}"
                )
        return tuple(warnings)

    def _mass_action_factor(
        self,
        step: ElementaryStep,
        stoichiometry: Mapping[str, float],
        state: Mapping[str, float],
        conditions: Mapping[str, float],
    ) -> float:
        factor = 1.0
        for species_id, coefficient in stoichiometry.items():
            value = self._species_value(step, species_id, state, conditions)
            factor *= value**coefficient
        return factor

    def _species_value(
        self,
        step: ElementaryStep,
        species_id: str,
        state: Mapping[str, float],
        conditions: Mapping[str, float],
    ) -> float:
        if species_id in self.model.gas_species:
            if species_id not in conditions:
                raise ValueError(
                    f"step {step.id!r} requires gas activity/pressure {species_id!r}"
                )
            return float(conditions[species_id])
        if species_id in self.model.surface_species or species_id in self.model.site_types:
            if species_id not in state:
                raise ValueError(
                    f"step {step.id!r} requires surface state variable {species_id!r}"
                )
            return float(state[species_id])
        raise ValueError(f"step {step.id!r} references unknown species/site {species_id!r}")


def build_rate_evaluator(
    model: MicrokineticModel,
    parameters: RateParameterSet,
    *,
    temperature_K: float | None = None,
) -> RateEvaluator:
    return RateEvaluator(model=model, parameters=parameters, temperature_K=temperature_K)


def microkinetic_rate_analysis(
    model: MicrokineticModel,
    parameters: RateParameterSet,
    state: Mapping[str, float],
    conditions: Mapping[str, float],
    *,
    temperature_K: float | None = None,
    tof_species: str | None = None,
    active_site_count: float | None = None,
) -> MicrokineticRateAnalysis:
    evaluator = build_rate_evaluator(model, parameters, temperature_K=temperature_K)
    step_rates_by_id = evaluator.step_rates(state, conditions)
    step_rates = tuple(step_rates_by_id[step.id] for step in model.steps)
    species_rates = _species_production_rates(model, step_rates_by_id)
    warnings = list(evaluator.site_balance_warnings(state))
    turnover_frequency = None
    turnover_frequency_unit = None
    if tof_species is not None:
        if active_site_count is None:
            raise ValueError("active_site_count is required for TOF calculation")
        if active_site_count <= 0:
            raise ValueError("active_site_count must be positive")
        species_rate = _find_species_rate(species_rates, tof_species)
        turnover_frequency = species_rate.net_rate / active_site_count
        turnover_frequency_unit = (
            None
            if species_rate.unit is None
            else f"{species_rate.unit} per active_site"
        )
    return MicrokineticRateAnalysis(
        step_rates=step_rates,
        species_rates=species_rates,
        tof_species=tof_species,
        turnover_frequency=turnover_frequency,
        turnover_frequency_unit=turnover_frequency_unit,
        active_site_count=active_site_count,
        warnings=tuple(warnings),
    )


def write_rate_analysis_csv(analysis: MicrokineticRateAnalysis, path: Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "row_type",
                "id",
                "phase",
                "rate",
                "forward_rate",
                "reverse_rate",
                "unit",
                "active_site_count",
                "notes",
            ],
        )
        writer.writeheader()
        for row in analysis.to_rows():
            writer.writerow(row)


def _species_production_rates(
    model: MicrokineticModel,
    step_rates: Mapping[str, StepRate],
) -> tuple[SpeciesProductionRate, ...]:
    rates = {species_id: 0.0 for species_id in model.species}
    units: dict[str, str | None] = {species_id: None for species_id in model.species}
    for step in model.steps:
        step_rate = step_rates[step.id]
        for species_id, coefficient in step.reactants.items():
            if species_id in rates:
                rates[species_id] -= coefficient * step_rate.net_rate
                units[species_id] = step_rate.unit
        for species_id, coefficient in step.products.items():
            if species_id in rates:
                rates[species_id] += coefficient * step_rate.net_rate
                units[species_id] = step_rate.unit
    rows = []
    for species_id in sorted(rates):
        species = model.species[species_id]
        rows.append(
            SpeciesProductionRate(
                species_id=species_id,
                phase=species.phase,
                net_rate=rates[species_id],
                unit=units[species_id],
            )
        )
    return tuple(rows)


def _find_species_rate(
    species_rates: tuple[SpeciesProductionRate, ...],
    species_id: str,
) -> SpeciesProductionRate:
    for row in species_rates:
        if row.species_id == species_id:
            return row
    raise ValueError(f"TOF species {species_id!r} is not defined in the microkinetic model")


def _state_value(state: Mapping[str, float], species_id: str) -> float:
    if species_id not in state:
        return 0.0
    return float(state[species_id])
