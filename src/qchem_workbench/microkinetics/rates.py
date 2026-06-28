"""Mass-action rate expressions for validated microkinetic networks."""

from __future__ import annotations

from dataclasses import dataclass
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


def _state_value(state: Mapping[str, float], species_id: str) -> float:
    if species_id not in state:
        return 0.0
    return float(state[species_id])
