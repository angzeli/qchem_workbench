"""Transparent objective transformations and scoring utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from qchem_workbench.active_learning.objectives import (
    ObjectiveConstraint,
    ObjectiveDefinition,
    ObjectiveSpec,
    validate_objective_columns,
)


@dataclass(frozen=True)
class ScoredDataset:
    headers: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


def score_dataset_rows(
    rows: Iterable[dict[str, Any]],
    headers: Iterable[str],
    spec: ObjectiveSpec,
) -> ScoredDataset:
    input_rows = [dict(row) for row in rows]
    input_headers = tuple(headers)
    validate_objective_columns(spec, input_headers)
    scored_rows = [_score_row(row, spec) for row in input_rows]
    output_headers = _headers(input_headers, spec, scored_rows)
    _assign_ranks(scored_rows)
    return ScoredDataset(headers=output_headers, rows=tuple(scored_rows))


def write_scored_dataset_csv(dataset: ScoredDataset, path: Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dataset.headers))
        writer.writeheader()
        writer.writerows(dataset.rows)


def _score_row(row: dict[str, Any], spec: ObjectiveSpec) -> dict[str, Any]:
    output = dict(row)
    reasons: list[str] = []
    score = 0.0
    for objective in spec.objectives:
        raw_value = _numeric_value(row.get(objective.source_column))
        raw_column = f"objective_{objective.id}_raw"
        value_column = f"objective_{objective.id}_value"
        transform_column = f"objective_{objective.id}_transformation"
        component_column = f"score_component_{objective.id}"
        output[raw_column] = row.get(objective.source_column, "")
        if raw_value is None:
            output[value_column] = ""
            output[transform_column] = _transformation_name(objective)
            output[component_column] = ""
            reasons.append(f"missing_descriptor:{objective.source_column}")
            continue
        transformed = _transform_objective(raw_value, objective)
        component = transformed * objective.weight
        output[value_column] = transformed
        output[transform_column] = _transformation_name(objective)
        output[component_column] = component
        score += component

    for constraint in spec.constraints:
        passed, reason = _constraint_result(row, constraint)
        output[f"constraint_{constraint.id}_pass"] = passed
        if not passed:
            reasons.append(reason)
        output[f"constraint_{constraint.id}_reason"] = "" if passed else reason

    unique_reasons = tuple(dict.fromkeys(reasons))
    output["al_score"] = "" if unique_reasons else score
    output["al_status"] = "excluded" if unique_reasons else "ranked"
    output["al_reasons"] = ";".join(unique_reasons)
    output["al_rank"] = ""
    return output


def _assign_ranks(rows: list[dict[str, Any]]) -> None:
    ranked = [row for row in rows if row["al_status"] == "ranked"]
    ranked.sort(key=lambda row: (-float(row["al_score"]), str(row.get("candidate_id", ""))))
    for rank, row in enumerate(ranked, start=1):
        row["al_rank"] = rank


def _transform_objective(value: float, objective: ObjectiveDefinition) -> float:
    transformation = objective.transformation
    if transformation is None:
        if objective.direction in {"minimise", "minimize"}:
            transformation = "negate"
        elif objective.direction in {"maximise", "maximize"}:
            transformation = "identity"
        else:
            transformation = "target_distance_negated"

    if transformation == "identity":
        return value
    if transformation == "negate":
        return -value
    if transformation in {"absolute_distance_to_target", "target_distance"}:
        if objective.target is None:
            raise ValueError(f"objective {objective.id!r} requires target")
        return abs(value - objective.target)
    if transformation == "target_distance_negated":
        if objective.target is None:
            raise ValueError(f"objective {objective.id!r} requires target")
        return -abs(value - objective.target)
    if transformation == "standardise" or transformation == "standardize":
        if objective.mean is None or objective.std is None or objective.std == 0:
            raise ValueError(f"objective {objective.id!r} requires nonzero mean/std")
        return (value - objective.mean) / objective.std
    if transformation == "min_max":
        lower, upper = _bounds(objective)
        return (value - lower) / (upper - lower)
    if transformation == "clip":
        lower, upper = _bounds(objective)
        return min(max(value, lower), upper)
    raise ValueError(f"unsupported objective transformation {transformation!r}")


def _constraint_result(
    row: dict[str, Any],
    constraint: ObjectiveConstraint,
) -> tuple[bool, str]:
    value = row.get(constraint.source_column)
    if constraint.op == "is_not_missing":
        passed = _present(value)
        return passed, f"constraint_failed:{constraint.id}"
    if not _present(value):
        return False, f"missing_constraint_column:{constraint.source_column}"

    if constraint.op == "equals":
        passed = str(value) == str(constraint.value)
    elif constraint.op == "not_equals":
        passed = str(value) != str(constraint.value)
    elif constraint.op == "less_than":
        passed = _numeric_or_error(value, constraint) < float(constraint.value)
    elif constraint.op == "less_equal":
        passed = _numeric_or_error(value, constraint) <= float(constraint.value)
    elif constraint.op == "greater_than":
        passed = _numeric_or_error(value, constraint) > float(constraint.value)
    elif constraint.op == "greater_equal":
        passed = _numeric_or_error(value, constraint) >= float(constraint.value)
    elif constraint.op == "between":
        low, high = constraint.value
        numeric = _numeric_or_error(value, constraint)
        passed = float(low) <= numeric <= float(high)
    else:
        raise ValueError(f"unsupported constraint operator {constraint.op!r}")
    return passed, f"constraint_failed:{constraint.id}"


def _headers(
    input_headers: tuple[str, ...],
    spec: ObjectiveSpec,
    rows: list[dict[str, Any]],
) -> tuple[str, ...]:
    generated = [
        "al_rank",
        "al_status",
        "al_score",
        "al_reasons",
    ]
    for objective in spec.objectives:
        generated.extend(
            [
                f"objective_{objective.id}_raw",
                f"objective_{objective.id}_value",
                f"objective_{objective.id}_transformation",
                f"score_component_{objective.id}",
            ]
        )
    for constraint in spec.constraints:
        generated.extend(
            [
                f"constraint_{constraint.id}_pass",
                f"constraint_{constraint.id}_reason",
            ]
        )
    headers = [*generated, *input_headers]
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)
    return tuple(headers)


def _transformation_name(objective: ObjectiveDefinition) -> str:
    if objective.transformation:
        return objective.transformation
    if objective.direction in {"minimise", "minimize"}:
        return "negate"
    if objective.direction in {"maximise", "maximize"}:
        return "identity"
    return "target_distance_negated"


def _bounds(objective: ObjectiveDefinition) -> tuple[float, float]:
    if objective.lower is None or objective.upper is None or objective.lower == objective.upper:
        raise ValueError(f"objective {objective.id!r} requires distinct lower/upper bounds")
    return objective.lower, objective.upper


def _numeric_or_error(value: Any, constraint: ObjectiveConstraint) -> float:
    numeric = _numeric_value(value)
    if numeric is None:
        raise ValueError(f"constraint {constraint.id!r} requires numeric values")
    return numeric


def _numeric_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _present(value: Any) -> bool:
    return value not in (None, "")
