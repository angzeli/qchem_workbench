"""Generic plane-wave convergence study bookkeeping."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.units import hartree_to_ev


CONVERGENCE_SCHEMA_VERSION = 1
SUPPORTED_VARIABLE_TYPES = {"ecutwfc", "ecutrho", "kpoints"}
SUPPORTED_TOLERANCE_UNITS = {"eV", "eV_per_atom"}


@dataclass(frozen=True)
class ConvergenceVariable:
    type: str
    values: tuple[Any, ...]


@dataclass(frozen=True)
class ConvergenceTolerance:
    value: float
    unit: str


@dataclass(frozen=True)
class ConvergenceStudy:
    name: str
    quantity: str
    variable: ConvergenceVariable
    fixed_settings: dict[str, Any] = field(default_factory=dict)
    tolerance: ConvergenceTolerance | None = None


@dataclass(frozen=True)
class ConvergenceRow:
    variable_value: Any
    complete: bool
    energy_ev: float | None = None
    delta_from_previous_ev: float | None = None
    delta_from_previous_ev_per_atom: float | None = None
    within_tolerance: bool | None = None
    n_atoms: int | None = None
    missing_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_value": self.variable_value,
            "complete": self.complete,
            "energy_ev": self.energy_ev,
            "delta_from_previous_ev": self.delta_from_previous_ev,
            "delta_from_previous_ev_per_atom": self.delta_from_previous_ev_per_atom,
            "within_tolerance": self.within_tolerance,
            "n_atoms": self.n_atoms,
            "missing_reason": self.missing_reason,
        }


def load_convergence_study(path: Path) -> ConvergenceStudy:
    study_path = Path(path)
    data = yaml.safe_load(study_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{study_path}: convergence study must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != CONVERGENCE_SCHEMA_VERSION:
        raise ValueError(
            f"{study_path}: unsupported schema_version {schema_version!r}; "
            f"expected {CONVERGENCE_SCHEMA_VERSION}"
        )
    raw_study = data.get("convergence_study")
    if not isinstance(raw_study, dict):
        raise ValueError(f"{study_path}: convergence_study must be a mapping")

    name = _required_str(study_path, raw_study, "name")
    quantity = _required_str(study_path, raw_study, "quantity")
    variable = _variable(study_path, raw_study.get("variable"))
    tolerance = _tolerance(study_path, raw_study.get("tolerance"))
    fixed_settings = raw_study.get("fixed_settings", {})
    if not isinstance(fixed_settings, dict):
        raise ValueError(f"{study_path}: fixed_settings must be a mapping")
    return ConvergenceStudy(
        name=name,
        quantity=quantity,
        variable=variable,
        fixed_settings=dict(fixed_settings),
        tolerance=tolerance,
    )


def generate_convergence_settings(study: ConvergenceStudy) -> list[dict[str, Any]]:
    settings = []
    for value in study.variable.values:
        row = dict(study.fixed_settings)
        row[study.variable.type] = value
        settings.append(row)
    return settings


def convergence_table(
    study: ConvergenceStudy,
    results: Iterable[CalculationResult],
) -> list[ConvergenceRow]:
    results_by_value = {
        _normalise_value(_result_variable_value(result, study.variable.type)): result
        for result in results
        if _result_variable_value(result, study.variable.type) is not None
    }
    rows: list[ConvergenceRow] = []
    previous_energy_ev: float | None = None
    previous_n_atoms: int | None = None
    for value in study.variable.values:
        result = results_by_value.get(_normalise_value(value))
        if result is None:
            rows.append(
                ConvergenceRow(
                    variable_value=value,
                    complete=False,
                    missing_reason="missing_result",
                )
            )
            previous_energy_ev = None
            previous_n_atoms = None
            continue

        energy_ev = _result_energy_ev(result)
        n_atoms = _result_n_atoms(result)
        if energy_ev is None:
            rows.append(
                ConvergenceRow(
                    variable_value=value,
                    complete=False,
                    n_atoms=n_atoms,
                    missing_reason="missing_total_energy",
                )
            )
            previous_energy_ev = None
            previous_n_atoms = None
            continue

        delta_ev = (
            energy_ev - previous_energy_ev
            if previous_energy_ev is not None
            else None
        )
        delta_per_atom = None
        if delta_ev is not None and n_atoms:
            delta_per_atom = delta_ev / n_atoms
        within_tolerance = _within_tolerance(
            study.tolerance,
            delta_ev,
            delta_per_atom,
        )
        rows.append(
            ConvergenceRow(
                variable_value=value,
                complete=True,
                energy_ev=energy_ev,
                delta_from_previous_ev=delta_ev,
                delta_from_previous_ev_per_atom=delta_per_atom,
                within_tolerance=within_tolerance,
                n_atoms=n_atoms,
            )
        )
        previous_energy_ev = energy_ev
        previous_n_atoms = n_atoms
        if previous_n_atoms is None:
            previous_n_atoms = n_atoms
    return rows


def _variable(path: Path, data: Any) -> ConvergenceVariable:
    if not isinstance(data, dict):
        raise ValueError(f"{path}: variable must be a mapping")
    variable_type = _required_str(path, data, "type")
    if variable_type not in SUPPORTED_VARIABLE_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_VARIABLE_TYPES))
        raise ValueError(f"{path}: unsupported variable type {variable_type!r}; {allowed}")
    values = data.get("values")
    if not isinstance(values, list) or not values:
        raise ValueError(f"{path}: variable.values must be a non-empty list")
    return ConvergenceVariable(type=variable_type, values=tuple(values))


def _tolerance(path: Path, data: Any) -> ConvergenceTolerance:
    if not isinstance(data, dict):
        raise ValueError(f"{path}: tolerance must be provided")
    value = data.get("value")
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{path}: tolerance.value must be positive")
    unit = _required_str(path, data, "unit")
    if unit not in SUPPORTED_TOLERANCE_UNITS:
        allowed = ", ".join(sorted(SUPPORTED_TOLERANCE_UNITS))
        raise ValueError(f"{path}: unsupported tolerance unit {unit!r}; {allowed}")
    return ConvergenceTolerance(value=float(value), unit=unit)


def _required_str(path: Path, data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {key} must be a non-empty string")
    return value.strip()


def _result_variable_value(result: CalculationResult, variable_type: str) -> Any:
    if variable_type in result.metadata:
        return result.metadata[variable_type]
    settings = result.metadata.get("qe_settings")
    if isinstance(settings, dict):
        return settings.get(variable_type)
    return None


def _result_energy_ev(result: CalculationResult) -> float | None:
    value = result.metadata.get("total_energy_ev")
    if isinstance(value, (int, float)):
        return float(value)
    return hartree_to_ev(result.electronic_energy_hartree)


def _result_n_atoms(result: CalculationResult) -> int | None:
    value = result.metadata.get("n_atoms")
    return int(value) if isinstance(value, int) and value > 0 else None


def _within_tolerance(
    tolerance: ConvergenceTolerance | None,
    delta_ev: float | None,
    delta_ev_per_atom: float | None,
) -> bool | None:
    if tolerance is None or delta_ev is None:
        return None
    if tolerance.unit == "eV":
        return abs(delta_ev) <= tolerance.value
    if delta_ev_per_atom is None:
        return None
    return abs(delta_ev_per_atom) <= tolerance.value


def _normalise_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    return str(value)
