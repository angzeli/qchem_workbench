"""Explicit rate-parameter models for microkinetic workflows."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


RATE_PARAMETER_SCHEMA_VERSION = 1
BOLTZMANN_EV_PER_K = 8.617333262145e-5
PLANCK_EV_S = 4.135667696e-15


@dataclass(frozen=True)
class RateConstant:
    id: str
    value: float
    unit: str
    temperature_K: float | None = None
    source: str | None = None
    provenance: str | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_id(self.id)
        _validate_unit(self.unit, f"rate constant {self.id!r}")
        object.__setattr__(self, "value", float(self.value))
        if self.temperature_K is not None and self.temperature_K <= 0:
            raise ValueError(f"rate constant {self.id!r} temperature_K must be positive")

    def evaluate(self, temperature_K: float | None = None) -> "RateConstant":
        return RateConstant(
            id=self.id,
            value=self.value,
            unit=self.unit,
            temperature_K=temperature_K if temperature_K is not None else self.temperature_K,
            source=self.source,
            provenance=self.provenance,
            warnings=self.warnings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "value": self.value,
            "unit": self.unit,
            "temperature_K": self.temperature_K,
            "source": self.source,
            "provenance": self.provenance,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ArrheniusParameter:
    id: str
    pre_exponential: float
    pre_exponential_unit: str
    activation_energy_eV: float
    valid_temperature_range_K: tuple[float, float] | None = None
    source: str | None = None
    provenance: str | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_id(self.id)
        _validate_unit(self.pre_exponential_unit, f"Arrhenius parameter {self.id!r}")
        object.__setattr__(self, "pre_exponential", float(self.pre_exponential))
        object.__setattr__(self, "activation_energy_eV", float(self.activation_energy_eV))
        if self.valid_temperature_range_K is not None:
            low, high = self.valid_temperature_range_K
            if low <= 0 or high <= 0 or low >= high:
                raise ValueError(
                    f"Arrhenius parameter {self.id!r} valid temperature range is invalid"
                )

    def evaluate(self, temperature_K: float) -> RateConstant:
        """Evaluate k = A exp(-Ea / kBT), with Ea in eV and T in K."""

        _validate_temperature(temperature_K)
        value = self.pre_exponential * math.exp(
            -self.activation_energy_eV / (BOLTZMANN_EV_PER_K * temperature_K)
        )
        return RateConstant(
            id=self.id,
            value=value,
            unit=self.pre_exponential_unit,
            temperature_K=temperature_K,
            source=self.source,
            provenance=self.provenance,
            warnings=self.warnings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pre_exponential": self.pre_exponential,
            "pre_exponential_unit": self.pre_exponential_unit,
            "activation_energy_eV": self.activation_energy_eV,
            "valid_temperature_range_K": list(self.valid_temperature_range_K)
            if self.valid_temperature_range_K
            else None,
            "source": self.source,
            "provenance": self.provenance,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class EyringParameter:
    id: str
    activation_free_energy_eV: float
    temperature_K: float
    rate_constant_unit: str = "s^-1"
    standard_state_note: str | None = None
    source: str | None = None
    provenance: str | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_id(self.id)
        _validate_unit(self.rate_constant_unit, f"Eyring parameter {self.id!r}")
        object.__setattr__(
            self,
            "activation_free_energy_eV",
            float(self.activation_free_energy_eV),
        )
        _validate_temperature(self.temperature_K)

    def evaluate(self, temperature_K: float | None = None) -> RateConstant:
        """Evaluate k = (kBT/h) exp(-DeltaG‡ / kBT), using eV units."""

        temperature = temperature_K if temperature_K is not None else self.temperature_K
        _validate_temperature(temperature)
        value = (BOLTZMANN_EV_PER_K * temperature / PLANCK_EV_S) * math.exp(
            -self.activation_free_energy_eV / (BOLTZMANN_EV_PER_K * temperature)
        )
        return RateConstant(
            id=self.id,
            value=value,
            unit=self.rate_constant_unit,
            temperature_K=temperature,
            source=self.source,
            provenance=self.provenance,
            warnings=self.warnings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "activation_free_energy_eV": self.activation_free_energy_eV,
            "temperature_K": self.temperature_K,
            "rate_constant_unit": self.rate_constant_unit,
            "standard_state_note": self.standard_state_note,
            "source": self.source,
            "provenance": self.provenance,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class RateParameterSet:
    rate_constants: dict[str, RateConstant] = field(default_factory=dict)
    arrhenius: dict[str, ArrheniusParameter] = field(default_factory=dict)
    eyring: dict[str, EyringParameter] = field(default_factory=dict)

    def __post_init__(self) -> None:
        duplicate_ids = (
            set(self.rate_constants) & set(self.arrhenius)
            | set(self.rate_constants) & set(self.eyring)
            | set(self.arrhenius) & set(self.eyring)
        )
        if duplicate_ids:
            raise ValueError(
                "duplicate rate parameter ID(s): " + ", ".join(sorted(duplicate_ids))
            )

    @property
    def parameter_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.rate_constants) | set(self.arrhenius) | set(self.eyring)))

    def evaluate(self, parameter_id: str, temperature_K: float | None = None) -> RateConstant:
        if parameter_id in self.rate_constants:
            return self.rate_constants[parameter_id].evaluate(temperature_K)
        if parameter_id in self.arrhenius:
            if temperature_K is None:
                raise ValueError(
                    f"temperature_K is required to evaluate Arrhenius parameter {parameter_id!r}"
                )
            return self.arrhenius[parameter_id].evaluate(temperature_K)
        if parameter_id in self.eyring:
            return self.eyring[parameter_id].evaluate(temperature_K)
        raise KeyError(f"unknown rate parameter {parameter_id!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RATE_PARAMETER_SCHEMA_VERSION,
            "rate_parameters": {
                "rate_constants": {
                    key: value.to_dict() for key, value in sorted(self.rate_constants.items())
                },
                "arrhenius": {
                    key: value.to_dict() for key, value in sorted(self.arrhenius.items())
                },
                "eyring": {
                    key: value.to_dict() for key, value in sorted(self.eyring.items())
                },
            },
        }


def load_rate_parameter_set(path: Path) -> RateParameterSet:
    parameter_path = Path(path)
    data = yaml.safe_load(parameter_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{parameter_path}: rate parameter file must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != RATE_PARAMETER_SCHEMA_VERSION:
        raise ValueError(
            f"{parameter_path}: unsupported schema_version {schema_version!r}; "
            f"expected {RATE_PARAMETER_SCHEMA_VERSION}"
        )
    return rate_parameter_set_from_mapping(data.get("rate_parameters"), source_path=parameter_path)


def rate_parameter_set_from_mapping(
    data: Any,
    *,
    source_path: Path | None = None,
) -> RateParameterSet:
    if data is None:
        return RateParameterSet()
    if not isinstance(data, dict):
        label = f"{source_path}: " if source_path else ""
        raise ValueError(f"{label}rate_parameters must be a mapping")
    return RateParameterSet(
        rate_constants=_rate_constants(data.get("rate_constants", {}), source_path),
        arrhenius=_arrhenius_parameters(data.get("arrhenius", {}), source_path),
        eyring=_eyring_parameters(data.get("eyring", {}), source_path),
    )


def _rate_constants(raw_parameters: Any, source_path: Path | None) -> dict[str, RateConstant]:
    if raw_parameters is None:
        return {}
    if not isinstance(raw_parameters, dict):
        raise ValueError(_prefix(source_path) + "rate_constants must be a mapping")
    parsed: dict[str, RateConstant] = {}
    for parameter_id, raw in raw_parameters.items():
        raw = _parameter_mapping(source_path, parameter_id, raw)
        unit = _required_str(source_path, raw, "unit")
        parsed[str(parameter_id)] = RateConstant(
            id=str(parameter_id),
            value=_required_number(source_path, raw, "value"),
            unit=unit,
            temperature_K=_optional_number(raw.get("temperature_K")),
            source=_optional_str(raw.get("source")),
            provenance=_optional_str(raw.get("provenance")),
            warnings=_provenance_warnings(raw),
        )
    return parsed


def _arrhenius_parameters(
    raw_parameters: Any,
    source_path: Path | None,
) -> dict[str, ArrheniusParameter]:
    if raw_parameters is None:
        return {}
    if not isinstance(raw_parameters, dict):
        raise ValueError(_prefix(source_path) + "arrhenius must be a mapping")
    parsed: dict[str, ArrheniusParameter] = {}
    for parameter_id, raw in raw_parameters.items():
        raw = _parameter_mapping(source_path, parameter_id, raw)
        pre_exponential_unit = _required_str(source_path, raw, "pre_exponential_unit")
        activation_energy_eV = raw.get("activation_energy_eV")
        if activation_energy_eV is None:
            activation_energy_unit = _required_str(source_path, raw, "activation_energy_unit")
            if activation_energy_unit != "eV":
                raise ValueError(
                    _prefix(source_path)
                    + f"Arrhenius parameter {parameter_id!r} only supports eV activation energies"
                )
            activation_energy_eV = _required_number(source_path, raw, "activation_energy")
        parsed[str(parameter_id)] = ArrheniusParameter(
            id=str(parameter_id),
            pre_exponential=_required_number(source_path, raw, "pre_exponential"),
            pre_exponential_unit=pre_exponential_unit,
            activation_energy_eV=float(activation_energy_eV),
            valid_temperature_range_K=_temperature_range(raw.get("valid_temperature_range_K")),
            source=_optional_str(raw.get("source")),
            provenance=_optional_str(raw.get("provenance")),
            warnings=_provenance_warnings(raw),
        )
    return parsed


def _eyring_parameters(raw_parameters: Any, source_path: Path | None) -> dict[str, EyringParameter]:
    if raw_parameters is None:
        return {}
    if not isinstance(raw_parameters, dict):
        raise ValueError(_prefix(source_path) + "eyring must be a mapping")
    parsed: dict[str, EyringParameter] = {}
    for parameter_id, raw in raw_parameters.items():
        raw = _parameter_mapping(source_path, parameter_id, raw)
        activation_free_energy_eV = raw.get("activation_free_energy_eV")
        if activation_free_energy_eV is None:
            activation_free_energy_unit = _required_str(
                source_path,
                raw,
                "activation_free_energy_unit",
            )
            if activation_free_energy_unit != "eV":
                raise ValueError(
                    _prefix(source_path)
                    + f"Eyring parameter {parameter_id!r} only supports eV activation free energies"
                )
            activation_free_energy_eV = _required_number(
                source_path,
                raw,
                "activation_free_energy",
            )
        parsed[str(parameter_id)] = EyringParameter(
            id=str(parameter_id),
            activation_free_energy_eV=float(activation_free_energy_eV),
            temperature_K=_required_number(source_path, raw, "temperature_K"),
            rate_constant_unit=_required_str(source_path, raw, "rate_constant_unit"),
            standard_state_note=_optional_str(raw.get("standard_state_note")),
            source=_optional_str(raw.get("source")),
            provenance=_optional_str(raw.get("provenance")),
            warnings=_provenance_warnings(raw),
        )
    return parsed


def _parameter_mapping(
    source_path: Path | None,
    parameter_id: Any,
    raw: Any,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(_prefix(source_path) + f"rate parameter {parameter_id!r} must be a mapping")
    return raw


def _required_number(source_path: Path | None, data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(_prefix(source_path) + f"{key} must be numeric")
    return float(value)


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError("optional numeric value must be numeric when provided")
    return float(value)


def _required_str(source_path: Path | None, data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(_prefix(source_path) + f"{key} must be a non-empty string")
    return value.strip()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    stripped = value.strip()
    return stripped or None


def _temperature_range(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("valid_temperature_range_K must contain two values")
    low, high = float(value[0]), float(value[1])
    return (low, high)


def _provenance_warnings(data: dict[str, Any]) -> tuple[str, ...]:
    if _optional_str(data.get("source")) is None and _optional_str(data.get("provenance")) is None:
        return ("rate parameter source/provenance is missing",)
    return ()


def _validate_id(parameter_id: str) -> None:
    if not isinstance(parameter_id, str) or not parameter_id.strip():
        raise ValueError("rate parameter id must be a non-empty string")


def _validate_unit(unit: str, label: str) -> None:
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError(f"{label} unit must be explicit")


def _validate_temperature(temperature_K: float) -> None:
    if not isinstance(temperature_K, (int, float)) or temperature_K <= 0:
        raise ValueError("temperature_K must be positive")


def _prefix(source_path: Path | None) -> str:
    return f"{source_path}: " if source_path is not None else ""
