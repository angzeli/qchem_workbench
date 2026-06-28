"""ODE simulation utilities for microkinetic coverage trajectories."""

from __future__ import annotations

import csv
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from qchem_workbench.microkinetics.parameters import RateParameterSet
from qchem_workbench.microkinetics.rates import build_rate_evaluator
from qchem_workbench.microkinetics.schema import MicrokineticModel


MICROKINETIC_CONDITIONS_SCHEMA_VERSION = 1


class SciPyUnavailableError(RuntimeError):
    """Raised when optional SciPy integration is requested but unavailable."""


@dataclass(frozen=True)
class MicrokineticConditions:
    temperature_K: float | None = None
    variables: dict[str, float] = field(default_factory=dict)
    initial_coverages: dict[str, float] = field(default_factory=dict)
    time_grid: tuple[float, ...] = ()
    rate_parameters_path: Path | None = None
    rate_parameters: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationResult:
    times: tuple[float, ...]
    coverages: dict[str, tuple[float, ...]]
    success: bool
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def rows(self) -> list[dict[str, float]]:
        rows: list[dict[str, float]] = []
        for index, time in enumerate(self.times):
            row = {"time": time}
            for species_id in sorted(self.coverages):
                row[species_id] = self.coverages[species_id][index]
            rows.append(row)
        return rows


def load_microkinetic_conditions(path: Path) -> MicrokineticConditions:
    conditions_path = Path(path)
    data = yaml.safe_load(conditions_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{conditions_path}: conditions file must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != MICROKINETIC_CONDITIONS_SCHEMA_VERSION:
        raise ValueError(
            f"{conditions_path}: unsupported schema_version {schema_version!r}; "
            f"expected {MICROKINETIC_CONDITIONS_SCHEMA_VERSION}"
        )
    raw_conditions = data.get("conditions")
    if not isinstance(raw_conditions, dict):
        raise ValueError(f"{conditions_path}: conditions must be a mapping")

    rate_parameters_path = raw_conditions.get("rate_parameters_path")
    resolved_rate_parameters_path = None
    if rate_parameters_path is not None:
        if not isinstance(rate_parameters_path, str) or not rate_parameters_path.strip():
            raise ValueError(f"{conditions_path}: rate_parameters_path must be a string")
        resolved_rate_parameters_path = (conditions_path.parent / rate_parameters_path).resolve()

    return MicrokineticConditions(
        temperature_K=_optional_positive_number(raw_conditions.get("temperature_K")),
        variables=_numeric_mapping(conditions_path, raw_conditions.get("variables", {}), "variables"),
        initial_coverages=_numeric_mapping(
            conditions_path,
            raw_conditions.get("initial_coverages", {}),
            "initial_coverages",
        ),
        time_grid=_time_grid(conditions_path, raw_conditions.get("time_grid", [])),
        rate_parameters_path=resolved_rate_parameters_path,
        rate_parameters=raw_conditions.get("rate_parameters")
        if isinstance(raw_conditions.get("rate_parameters"), dict)
        else data.get("rate_parameters"),
        metadata=dict(raw_conditions.get("metadata", {}))
        if isinstance(raw_conditions.get("metadata", {}), dict)
        else {},
    )


def simulate_coverages(
    model: MicrokineticModel,
    parameters: RateParameterSet,
    initial_coverages: Mapping[str, float],
    conditions: Mapping[str, float],
    times: tuple[float, ...] | list[float],
    *,
    temperature_K: float | None = None,
    rtol: float = 1e-6,
    atol: float = 1e-9,
    negative_tolerance: float = 1e-8,
) -> SimulationResult:
    solve_ivp = _solve_ivp()
    time_grid = _validated_time_grid(times)
    evaluator = build_rate_evaluator(model, parameters, temperature_K=temperature_K)
    variable_ids = evaluator.dynamic_variable_ids
    _validate_initial_coverages(variable_ids, initial_coverages)
    initial_vector = [float(initial_coverages[species_id]) for species_id in variable_ids]

    def rhs(_time: float, vector: list[float]) -> list[float]:
        state = {
            species_id: float(vector[index])
            for index, species_id in enumerate(variable_ids)
        }
        derivatives = evaluator.rate_vector(state, conditions)
        return [derivatives[species_id] for species_id in variable_ids]

    solution = solve_ivp(
        rhs,
        (time_grid[0], time_grid[-1]),
        initial_vector,
        t_eval=list(time_grid),
        rtol=rtol,
        atol=atol,
    )
    warnings = list(evaluator.site_balance_warnings(initial_coverages))
    success = bool(solution.success)
    if not solution.success:
        warnings.append(f"SciPy solve_ivp did not converge: {solution.message}")

    coverages: dict[str, tuple[float, ...]] = {}
    for index, species_id in enumerate(variable_ids):
        values = tuple(float(value) for value in solution.y[index])
        if any(value < -negative_tolerance for value in values):
            warnings.append(
                f"coverage for {species_id!r} became negative beyond numerical tolerance"
            )
        coverages[species_id] = values

    return SimulationResult(
        times=tuple(float(value) for value in solution.t),
        coverages=coverages,
        success=success,
        warnings=tuple(warnings),
        metadata={
            "temperature_K": temperature_K,
            "rtol": rtol,
            "atol": atol,
            "solver": "scipy.integrate.solve_ivp",
        },
    )


def write_simulation_csv(result: SimulationResult, path: Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["time", *sorted(result.coverages)]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in result.rows():
            writer.writerow(row)


def _solve_ivp():
    if importlib.util.find_spec("scipy") is None:
        raise SciPyUnavailableError(
            "SciPy is required for microkinetic ODE simulation. "
            "Install the optional dependency with qchem-workbench[scipy]."
        )
    from scipy.integrate import solve_ivp

    return solve_ivp


def _validated_time_grid(times: tuple[float, ...] | list[float]) -> tuple[float, ...]:
    if len(times) < 2:
        raise ValueError("time grid must contain at least two points")
    time_grid = tuple(float(time) for time in times)
    if any(later <= earlier for earlier, later in zip(time_grid, time_grid[1:])):
        raise ValueError("time grid must be strictly increasing")
    return time_grid


def _validate_initial_coverages(
    variable_ids: tuple[str, ...],
    initial_coverages: Mapping[str, float],
) -> None:
    missing = [species_id for species_id in variable_ids if species_id not in initial_coverages]
    if missing:
        raise ValueError("missing initial coverage(s): " + ", ".join(missing))
    for species_id in variable_ids:
        value = initial_coverages[species_id]
        if not isinstance(value, (int, float)):
            raise ValueError(f"initial coverage for {species_id!r} must be numeric")


def _numeric_mapping(path: Path, data: Any, label: str) -> dict[str, float]:
    if not isinstance(data, dict):
        raise ValueError(f"{path}: conditions.{label} must be a mapping")
    parsed = {}
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{path}: conditions.{label} keys must be non-empty strings")
        if not isinstance(value, (int, float)):
            raise ValueError(f"{path}: conditions.{label}.{key} must be numeric")
        parsed[key] = float(value)
    return parsed


def _time_grid(path: Path, data: Any) -> tuple[float, ...]:
    if not isinstance(data, list):
        raise ValueError(f"{path}: conditions.time_grid must be a list")
    return _validated_time_grid(data)


def _optional_positive_number(value: Any) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError("temperature_K must be positive")
    return float(value)
