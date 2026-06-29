from __future__ import annotations

import pytest

from qchem_workbench.active_learning.objectives import (
    load_objective_spec,
    validate_objective_columns,
)


def test_minimise_objective(tmp_path):
    spec = load_objective_spec(_write_objectives(tmp_path))

    assert spec.objectives[0].id == "minimise_adsorption_energy"
    assert spec.objectives[0].direction == "minimise"
    assert spec.objectives[0].weight == 1.0


def test_maximise_objective(tmp_path):
    spec = load_objective_spec(
        _write_objectives(
            tmp_path,
            objectives=(
                "  - id: maximise_gap\n"
                "    source_column: gap_eV\n"
                "    direction: maximise\n"
                "    weight: 0.5\n"
            ),
        )
    )

    assert spec.objectives[0].direction == "maximise"
    assert spec.objectives[0].weight == 0.5


def test_target_objective(tmp_path):
    spec = load_objective_spec(
        _write_objectives(
            tmp_path,
            objectives=(
                "  - id: target_binding\n"
                "    source_column: adsorption_energy_eV\n"
                "    direction: target\n"
                "    target: -0.5\n"
            ),
        )
    )

    assert spec.objectives[0].target == -0.5


def test_numeric_constraint(tmp_path):
    spec = load_objective_spec(_write_objectives(tmp_path))

    constraint = spec.constraints[0]
    assert constraint.op == "equals"
    assert constraint.value == 0


def test_missing_column_error(tmp_path):
    spec = load_objective_spec(_write_objectives(tmp_path))

    with pytest.raises(ValueError, match="source column"):
        validate_objective_columns(spec, ["candidate_id", "adsorption_energy_eV"])


def test_invalid_operator_is_error(tmp_path):
    path = _write_objectives(
        tmp_path,
        constraints=(
            "  - id: bad_constraint\n"
            "    source_column: quality_error_count\n"
            "    op: approximately\n"
            "    value: 0\n"
        ),
    )

    with pytest.raises(ValueError, match="unsupported constraint operator"):
        load_objective_spec(path)


def _write_objectives(
    tmp_path,
    *,
    objectives: str = (
        "  - id: minimise_adsorption_energy\n"
        "    source_column: adsorption_energy_eV\n"
        "    direction: minimise\n"
        "    weight: 1.0\n"
    ),
    constraints: str = (
        "  - id: require_no_quality_errors\n"
        "    source_column: quality_error_count\n"
        "    op: equals\n"
        "    value: 0\n"
    ),
):
    path = tmp_path / "objectives.yaml"
    path.write_text(
        "schema_version: 1\n"
        "objectives:\n"
        f"{objectives}"
        "constraints:\n"
        f"{constraints}",
        encoding="utf-8",
    )
    return path
