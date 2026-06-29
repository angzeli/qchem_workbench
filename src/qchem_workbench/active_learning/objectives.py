"""Objective and constraint schemas for active-learning datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


ACTIVE_LEARNING_OBJECTIVE_SCHEMA_VERSION = 1
SUPPORTED_OBJECTIVE_DIRECTIONS = {"minimise", "minimize", "maximise", "maximize", "target"}
SUPPORTED_CONSTRAINT_OPERATORS = {
    "equals",
    "not_equals",
    "less_than",
    "less_equal",
    "greater_than",
    "greater_equal",
    "between",
    "is_not_missing",
}


@dataclass(frozen=True)
class ObjectiveDefinition:
    id: str
    source_column: str
    direction: str
    weight: float = 1.0
    target: float | None = None
    transformation: str | None = None
    mean: float | None = None
    std: float | None = None
    lower: float | None = None
    upper: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObjectiveConstraint:
    id: str
    source_column: str
    op: str
    value: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObjectiveSpec:
    objectives: tuple[ObjectiveDefinition, ...]
    constraints: tuple[ObjectiveConstraint, ...] = ()
    source_path: Path | None = None


def load_objective_spec(path: Path) -> ObjectiveSpec:
    spec_path = Path(path)
    data = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{spec_path}: objective file must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != ACTIVE_LEARNING_OBJECTIVE_SCHEMA_VERSION:
        raise ValueError(
            f"{spec_path}: unsupported schema_version {schema_version!r}; "
            f"expected {ACTIVE_LEARNING_OBJECTIVE_SCHEMA_VERSION}"
        )
    return ObjectiveSpec(
        objectives=_objectives(spec_path, data.get("objectives", [])),
        constraints=_constraints(spec_path, data.get("constraints", [])),
        source_path=spec_path,
    )


def validate_objective_columns(spec: ObjectiveSpec, columns: Iterable[str]) -> None:
    available = set(columns)
    missing = []
    for objective in spec.objectives:
        if objective.source_column not in available:
            missing.append(objective.source_column)
    for constraint in spec.constraints:
        if constraint.source_column not in available:
            missing.append(constraint.source_column)
    if missing:
        raise ValueError(
            "objective/constraint source column(s) missing from dataset: "
            + ", ".join(sorted(set(missing)))
        )


def _objectives(path: Path, raw_objectives: Any) -> tuple[ObjectiveDefinition, ...]:
    items = _mapping_list(path, raw_objectives, "objectives")
    seen: set[str] = set()
    objectives = []
    for index, item in enumerate(items):
        objective_id = _required_string(path, item, "id", f"objectives[{index}]")
        if objective_id in seen:
            raise ValueError(f"{path}: duplicate objective ID {objective_id!r}")
        seen.add(objective_id)
        direction = _required_string(path, item, "direction", f"objectives[{index}]")
        if direction not in SUPPORTED_OBJECTIVE_DIRECTIONS:
            raise ValueError(f"{path}: unsupported objective direction {direction!r}")
        target = _optional_float(path, item, "target", f"objectives[{index}]")
        if direction == "target" and target is None:
            raise ValueError(f"{path}: target objective {objective_id!r} requires target")
        metadata = {
            key: value
            for key, value in item.items()
            if key
            not in {
                "id",
                "source_column",
                "direction",
                "weight",
                "target",
                "transformation",
                "mean",
                "std",
                "lower",
                "upper",
            }
        }
        objectives.append(
            ObjectiveDefinition(
                id=objective_id,
                source_column=_required_string(
                    path,
                    item,
                    "source_column",
                    f"objectives[{index}]",
                ),
                direction=direction,
                weight=_optional_float(path, item, "weight", f"objectives[{index}]")
                or 1.0,
                target=target,
                transformation=_optional_string(item, "transformation"),
                mean=_optional_float(path, item, "mean", f"objectives[{index}]"),
                std=_optional_float(path, item, "std", f"objectives[{index}]"),
                lower=_optional_float(path, item, "lower", f"objectives[{index}]"),
                upper=_optional_float(path, item, "upper", f"objectives[{index}]"),
                metadata=metadata,
            )
        )
    return tuple(objectives)


def _constraints(path: Path, raw_constraints: Any) -> tuple[ObjectiveConstraint, ...]:
    items = _mapping_list(path, raw_constraints, "constraints")
    seen: set[str] = set()
    constraints = []
    for index, item in enumerate(items):
        constraint_id = _required_string(path, item, "id", f"constraints[{index}]")
        if constraint_id in seen:
            raise ValueError(f"{path}: duplicate constraint ID {constraint_id!r}")
        seen.add(constraint_id)
        op = _required_string(path, item, "op", f"constraints[{index}]")
        if op not in SUPPORTED_CONSTRAINT_OPERATORS:
            raise ValueError(f"{path}: unsupported constraint operator {op!r}")
        if op == "between":
            value = item.get("value")
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError(f"{path}: between constraint {constraint_id!r} needs two values")
        elif op != "is_not_missing" and "value" not in item:
            raise ValueError(f"{path}: constraint {constraint_id!r} requires value")
        metadata = {
            key: value
            for key, value in item.items()
            if key not in {"id", "source_column", "op", "value"}
        }
        constraints.append(
            ObjectiveConstraint(
                id=constraint_id,
                source_column=_required_string(
                    path,
                    item,
                    "source_column",
                    f"constraints[{index}]",
                ),
                op=op,
                value=item.get("value"),
                metadata=metadata,
            )
        )
    return tuple(constraints)


def _mapping_list(path: Path, value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError(f"{path}: {label} must be a list")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: {label}[{index}] must be a mapping")
    return value


def _required_string(path: Path, data: dict[str, Any], key: str, label: str) -> str:
    value = _optional_string(data, key)
    if value is None:
        raise ValueError(f"{path}: {label}.{key} must be a non-empty string")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string when provided")
    return value.strip()


def _optional_float(
    path: Path,
    data: dict[str, Any],
    key: str,
    label: str,
) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"{path}: {label}.{key} must be numeric")
    return float(value)
