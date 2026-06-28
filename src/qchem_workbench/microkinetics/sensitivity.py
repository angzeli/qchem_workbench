"""Finite-difference sensitivity utilities for microkinetic models."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from qchem_workbench.microkinetics.parameters import RateConstant, RateParameterSet
from qchem_workbench.microkinetics.rates import microkinetic_rate_analysis
from qchem_workbench.microkinetics.schema import MicrokineticModel
from qchem_workbench.microkinetics.simulation import solve_steady_state


@dataclass(frozen=True)
class SensitivityRow:
    parameter_id: str
    observable: str
    perturbation_ln: float
    baseline_value: float | None
    perturbed_value: float | None
    sensitivity: float | None
    baseline_converged: bool
    perturbed_converged: bool | None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, str | float | bool | None]:
        return {
            "parameter_id": self.parameter_id,
            "observable": self.observable,
            "perturbation_ln": self.perturbation_ln,
            "baseline_value": self.baseline_value,
            "perturbed_value": self.perturbed_value,
            "sensitivity": self.sensitivity,
            "baseline_converged": self.baseline_converged,
            "perturbed_converged": self.perturbed_converged,
            "warnings": ";".join(self.warnings),
        }


def microkinetic_sensitivity(
    model: MicrokineticModel,
    parameters: RateParameterSet,
    initial_guess: Mapping[str, float],
    conditions: Mapping[str, float],
    *,
    observable: str,
    temperature_K: float | None = None,
    perturbation_ln: float = 1e-2,
    active_site_count: float | None = None,
    max_function_evaluations: int | None = None,
) -> tuple[SensitivityRow, ...]:
    if perturbation_ln <= 0:
        raise ValueError("perturbation_ln must be positive")
    evaluated_parameters = _evaluated_parameter_set(model, parameters, temperature_K)
    baseline = solve_steady_state(
        model,
        evaluated_parameters,
        initial_guess,
        conditions,
        temperature_K=temperature_K,
        max_function_evaluations=max_function_evaluations,
    )
    baseline_value = _observable_value(
        model,
        evaluated_parameters,
        baseline.coverages,
        conditions,
        observable,
        temperature_K=temperature_K,
        active_site_count=active_site_count,
    )
    rows = []
    for parameter_id in evaluated_parameters.parameter_ids:
        warnings = list(baseline.warnings)
        if not baseline.success:
            warnings.append("baseline steady state did not converge")
            rows.append(
                SensitivityRow(
                    parameter_id=parameter_id,
                    observable=observable,
                    perturbation_ln=perturbation_ln,
                    baseline_value=baseline_value,
                    perturbed_value=None,
                    sensitivity=None,
                    baseline_converged=False,
                    perturbed_converged=None,
                    warnings=tuple(warnings),
                )
            )
            continue
        perturbed_parameters = _perturbed_parameters(
            evaluated_parameters,
            parameter_id,
            perturbation_ln,
        )
        perturbed = solve_steady_state(
            model,
            perturbed_parameters,
            baseline.coverages,
            conditions,
            temperature_K=temperature_K,
            max_function_evaluations=max_function_evaluations,
        )
        perturbed_value = _observable_value(
            model,
            perturbed_parameters,
            perturbed.coverages,
            conditions,
            observable,
            temperature_K=temperature_K,
            active_site_count=active_site_count,
        )
        if perturbed.warnings:
            warnings.extend(perturbed.warnings)
        if not perturbed.success:
            warnings.append("perturbed steady state did not converge")
        sensitivity = (
            None
            if baseline_value is None or perturbed_value is None
            else (perturbed_value - baseline_value) / perturbation_ln
        )
        rows.append(
            SensitivityRow(
                parameter_id=parameter_id,
                observable=observable,
                perturbation_ln=perturbation_ln,
                baseline_value=baseline_value,
                perturbed_value=perturbed_value,
                sensitivity=sensitivity,
                baseline_converged=True,
                perturbed_converged=perturbed.success,
                warnings=tuple(warnings),
            )
        )
    return tuple(rows)


def write_sensitivity_csv(rows: tuple[SensitivityRow, ...], path: Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "parameter_id",
                "observable",
                "perturbation_ln",
                "baseline_value",
                "perturbed_value",
                "sensitivity",
                "baseline_converged",
                "perturbed_converged",
                "warnings",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def _observable_value(
    model: MicrokineticModel,
    parameters: RateParameterSet,
    state: Mapping[str, float],
    conditions: Mapping[str, float],
    observable: str,
    *,
    temperature_K: float | None,
    active_site_count: float | None,
) -> float | None:
    if observable.startswith("product_rate:"):
        species_id = observable.split(":", 1)[1]
        analysis = microkinetic_rate_analysis(
            model,
            parameters,
            state,
            conditions,
            temperature_K=temperature_K,
        )
        for species_rate in analysis.species_rates:
            if species_rate.species_id == species_id:
                return species_rate.net_rate
        raise ValueError(f"observable species {species_id!r} is not defined")
    if observable.startswith("tof:"):
        species_id = observable.split(":", 1)[1]
        analysis = microkinetic_rate_analysis(
            model,
            parameters,
            state,
            conditions,
            temperature_K=temperature_K,
            tof_species=species_id,
            active_site_count=active_site_count,
        )
        return analysis.turnover_frequency
    raise ValueError(
        "observable must use a supported form such as 'product_rate:SPECIES' or 'tof:SPECIES'"
    )


def _evaluated_parameter_set(
    model: MicrokineticModel,
    parameters: RateParameterSet,
    temperature_K: float | None,
) -> RateParameterSet:
    evaluated = {}
    for parameter_id in model.rate_parameter_ids:
        rate = parameters.evaluate(parameter_id, temperature_K=temperature_K)
        evaluated[parameter_id] = rate
    return RateParameterSet(rate_constants=evaluated)


def _perturbed_parameters(
    parameters: RateParameterSet,
    parameter_id: str,
    perturbation_ln: float,
) -> RateParameterSet:
    updated = dict(parameters.rate_constants)
    rate = updated[parameter_id]
    updated[parameter_id] = RateConstant(
        id=rate.id,
        value=rate.value * math.exp(perturbation_ln),
        unit=rate.unit,
        temperature_K=rate.temperature_K,
        source=rate.source,
        provenance=rate.provenance,
        warnings=rate.warnings,
    )
    return RateParameterSet(rate_constants=updated)
