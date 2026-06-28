"""Uncertainty sampling for user-provided microkinetic parameters."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import yaml

from qchem_workbench.microkinetics.parameters import RateConstant, RateParameterSet
from qchem_workbench.microkinetics.rates import microkinetic_rate_analysis
from qchem_workbench.microkinetics.schema import MicrokineticModel
from qchem_workbench.microkinetics.simulation import solve_steady_state


PARAMETER_DISTRIBUTION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ParameterDistribution:
    id: str
    distribution: str
    unit: str
    values: dict[str, float]
    source: str | None = None
    warnings: tuple[str, ...] = ()

    def sample(self, rng: np.random.Generator) -> float:
        if self.distribution == "fixed":
            return self.values["value"]
        if self.distribution == "uniform":
            return float(rng.uniform(self.values["low"], self.values["high"]))
        if self.distribution == "normal":
            return float(rng.normal(self.values["mean"], self.values["std"]))
        if self.distribution == "loguniform":
            low = self.values["low"]
            high = self.values["high"]
            return float(np.exp(rng.uniform(np.log(low), np.log(high))))
        raise ValueError(f"unsupported distribution {self.distribution!r}")


@dataclass(frozen=True)
class UncertaintySampleRow:
    sample_index: int
    observable: str
    value: float | None
    success: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class UncertaintySummary:
    observable: str
    n_samples: int
    success_count: int
    failure_count: int
    mean: float | None = None
    median: float | None = None
    q05: float | None = None
    q95: float | None = None
    seed: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "observable": self.observable,
            "n_samples": self.n_samples,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "mean": self.mean,
            "median": self.median,
            "q05": self.q05,
            "q95": self.q95,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class UncertaintyResult:
    samples: tuple[UncertaintySampleRow, ...]
    summary: UncertaintySummary
    metadata: dict[str, Any] = field(default_factory=dict)


def load_parameter_distributions(path: Path) -> dict[str, ParameterDistribution]:
    distribution_path = Path(path)
    data = yaml.safe_load(distribution_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{distribution_path}: parameter distribution file must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != PARAMETER_DISTRIBUTION_SCHEMA_VERSION:
        raise ValueError(
            f"{distribution_path}: unsupported schema_version {schema_version!r}; "
            f"expected {PARAMETER_DISTRIBUTION_SCHEMA_VERSION}"
        )
    return parameter_distributions_from_mapping(data.get("parameter_distributions"))


def parameter_distributions_from_mapping(data: Any) -> dict[str, ParameterDistribution]:
    if not isinstance(data, dict) or not data:
        raise ValueError("parameter_distributions must be a non-empty mapping")
    return {
        str(parameter_id): _distribution_from_mapping(str(parameter_id), raw)
        for parameter_id, raw in data.items()
    }


def sample_rate_parameter_sets(
    distributions: Mapping[str, ParameterDistribution],
    *,
    n_samples: int,
    seed: int | None = None,
) -> tuple[RateParameterSet, ...]:
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    rng = np.random.default_rng(seed)
    samples = []
    for _index in range(n_samples):
        rate_constants = {
            parameter_id: RateConstant(
                id=parameter_id,
                value=distribution.sample(rng),
                unit=distribution.unit,
                source=distribution.source,
                warnings=distribution.warnings,
            )
            for parameter_id, distribution in distributions.items()
        }
        samples.append(RateParameterSet(rate_constants=rate_constants))
    return tuple(samples)


def microkinetic_uncertainty_sample(
    model: MicrokineticModel,
    distributions: Mapping[str, ParameterDistribution],
    initial_guess: Mapping[str, float],
    conditions: Mapping[str, float],
    *,
    observable: str,
    n_samples: int,
    seed: int | None = None,
    temperature_K: float | None = None,
    active_site_count: float | None = None,
) -> UncertaintyResult:
    parameter_sets = sample_rate_parameter_sets(
        distributions,
        n_samples=n_samples,
        seed=seed,
    )
    rows = []
    for sample_index, parameters in enumerate(parameter_sets):
        try:
            steady_state = solve_steady_state(
                model,
                parameters,
                initial_guess,
                conditions,
                temperature_K=temperature_K,
            )
            if not steady_state.success:
                rows.append(
                    UncertaintySampleRow(
                        sample_index=sample_index,
                        observable=observable,
                        value=None,
                        success=False,
                        warnings=steady_state.warnings,
                    )
                )
                continue
            value = _observable_value(
                model,
                parameters,
                steady_state.coverages,
                conditions,
                observable,
                temperature_K=temperature_K,
                active_site_count=active_site_count,
            )
            rows.append(
                UncertaintySampleRow(
                    sample_index=sample_index,
                    observable=observable,
                    value=value,
                    success=True,
                    warnings=steady_state.warnings,
                )
            )
        except Exception as exc:  # noqa: BLE001 - failed samples are reported explicitly.
            rows.append(
                UncertaintySampleRow(
                    sample_index=sample_index,
                    observable=observable,
                    value=None,
                    success=False,
                    warnings=(str(exc),),
                )
            )
    return UncertaintyResult(
        samples=tuple(rows),
        summary=uncertainty_summary(rows, observable=observable, seed=seed),
    )


def uncertainty_summary(
    rows: tuple[UncertaintySampleRow, ...] | list[UncertaintySampleRow],
    *,
    observable: str,
    seed: int | None = None,
) -> UncertaintySummary:
    values = np.array(
        [row.value for row in rows if row.success and row.value is not None],
        dtype=float,
    )
    failure_count = len(rows) - len(values)
    if len(values) == 0:
        return UncertaintySummary(
            observable=observable,
            n_samples=len(rows),
            success_count=0,
            failure_count=failure_count,
            seed=seed,
        )
    return UncertaintySummary(
        observable=observable,
        n_samples=len(rows),
        success_count=len(values),
        failure_count=failure_count,
        mean=float(np.mean(values)),
        median=float(np.median(values)),
        q05=float(np.quantile(values, 0.05)),
        q95=float(np.quantile(values, 0.95)),
        seed=seed,
    )


def write_uncertainty_csv(result: UncertaintyResult, path: Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "observable",
                "n_samples",
                "success_count",
                "failure_count",
                "mean",
                "median",
                "q05",
                "q95",
                "seed",
            ],
        )
        writer.writeheader()
        writer.writerow(result.summary.to_dict())


def _distribution_from_mapping(parameter_id: str, raw: Any) -> ParameterDistribution:
    if not isinstance(raw, dict):
        raise ValueError(f"distribution for {parameter_id!r} must be a mapping")
    distribution = _required_str(raw, "distribution")
    unit = _required_str(raw, "unit")
    source = _optional_str(raw.get("source"))
    warnings = () if source else ("parameter distribution source is missing",)
    if distribution == "fixed":
        values = {"value": _required_number(raw, "value")}
    elif distribution == "uniform":
        values = {
            "low": _required_number(raw, "low"),
            "high": _required_number(raw, "high"),
        }
        if values["low"] >= values["high"]:
            raise ValueError(f"uniform distribution for {parameter_id!r} requires low < high")
    elif distribution == "normal":
        values = {
            "mean": _required_number(raw, "mean"),
            "std": _required_number(raw, "std"),
        }
        if values["std"] <= 0:
            raise ValueError(f"normal distribution for {parameter_id!r} requires std > 0")
    elif distribution == "loguniform":
        values = {
            "low": _required_number(raw, "low"),
            "high": _required_number(raw, "high"),
        }
        if values["low"] <= 0 or values["low"] >= values["high"]:
            raise ValueError(
                f"loguniform distribution for {parameter_id!r} requires 0 < low < high"
            )
    else:
        raise ValueError(f"unsupported distribution {distribution!r}")
    return ParameterDistribution(
        id=parameter_id,
        distribution=distribution,
        unit=unit,
        values=values,
        source=source,
        warnings=warnings,
    )


def _observable_value(
    model: MicrokineticModel,
    parameters: RateParameterSet,
    state: Mapping[str, float],
    conditions: Mapping[str, float],
    observable: str,
    *,
    temperature_K: float | None,
    active_site_count: float | None,
) -> float:
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
        if analysis.turnover_frequency is None:
            raise ValueError(f"TOF observable {observable!r} could not be evaluated")
        return analysis.turnover_frequency
    raise ValueError(
        "observable must use a supported form such as 'product_rate:SPECIES' or 'tof:SPECIES'"
    )


def _required_number(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    return float(value)


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    stripped = value.strip()
    return stripped or None
