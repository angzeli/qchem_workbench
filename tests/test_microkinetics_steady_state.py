from __future__ import annotations

import csv

import pytest

from qchem_workbench.cli import main
from qchem_workbench.microkinetics.parameters import rate_parameter_set_from_mapping
from qchem_workbench.microkinetics.schema import load_microkinetic_model
from qchem_workbench.microkinetics.simulation import (
    solve_steady_state,
    write_steady_state_csv,
)


def test_reversible_network_steady_state(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_reversible_model(tmp_path))
    parameters = _parameters({"k_forward": 1.0, "k_reverse": 1.0})

    result = solve_steady_state(
        model,
        parameters,
        {"A_star": 0.2, "star": 0.8},
        {},
    )

    assert result.success is True
    assert result.coverages["A_star"] == pytest.approx(0.5)
    assert result.coverages["star"] == pytest.approx(0.5)
    assert result.max_abs_residual <= 1e-8


def test_non_converged_when_tolerance_is_unrealistically_strict(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_reversible_model(tmp_path))
    parameters = _parameters({"k_forward": 1.0, "k_reverse": 1.0})

    result = solve_steady_state(
        model,
        parameters,
        {"A_star": 0.2, "star": 0.8},
        {},
        max_function_evaluations=1,
    )

    assert result.success is False
    assert result.warnings


def test_bad_initial_guess_is_error(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_reversible_model(tmp_path))

    with pytest.raises(ValueError, match="missing initial coverage"):
        solve_steady_state(
            model,
            _parameters({"k_forward": 1.0, "k_reverse": 1.0}),
            {"A_star": 0.2},
            {},
        )


def test_steady_state_csv_output(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_reversible_model(tmp_path))
    result = solve_steady_state(
        model,
        _parameters({"k_forward": 1.0, "k_reverse": 1.0}),
        {"A_star": 0.2, "star": 0.8},
        {},
    )
    out_path = tmp_path / "steady_state.csv"

    write_steady_state_csv(result, out_path)

    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["species"] for row in rows} == {"A_star", "star"}
    assert rows[0]["max_abs_residual"] != ""


def test_microkinetics_steady_state_cli(tmp_path, capsys):
    pytest.importorskip("scipy")
    model_path = _write_reversible_model(tmp_path)
    parameter_path = _write_parameter_file(tmp_path)
    conditions_path = _write_conditions_file(tmp_path, parameter_path.name)
    out_path = tmp_path / "results" / "steady_state.csv"

    exit_code = main(
        [
            "microkinetics",
            "steady-state",
            str(model_path),
            "--conditions",
            str(conditions_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "success\tTrue" in captured.out
    assert out_path.exists()


def _parameters(values):
    return rate_parameter_set_from_mapping(
        {
            "rate_constants": {
                key: {
                    "value": value,
                    "unit": "s^-1",
                    "source": "synthetic test value",
                }
                for key, value in values.items()
            }
        }
    )


def _write_parameter_file(tmp_path):
    path = tmp_path / "parameters.yaml"
    path.write_text(
        "schema_version: 1\n"
        "rate_parameters:\n"
        "  rate_constants:\n"
        "    k_forward:\n"
        "      value: 1.0\n"
        "      unit: s^-1\n"
        "      source: synthetic test value\n"
        "    k_reverse:\n"
        "      value: 1.0\n"
        "      unit: s^-1\n"
        "      source: synthetic test value\n",
        encoding="utf-8",
    )
    return path


def _write_conditions_file(tmp_path, parameter_file_name):
    path = tmp_path / "conditions.yaml"
    path.write_text(
        "schema_version: 1\n"
        "conditions:\n"
        f"  rate_parameters_path: {parameter_file_name}\n"
        "  variables: {}\n"
        "  initial_coverages:\n"
        "    A_star: 0.2\n"
        "    star: 0.8\n"
        "  time_grid: [0.0, 1.0]\n",
        encoding="utf-8",
    )
    return path


def _write_reversible_model(tmp_path):
    path = tmp_path / "reversible_model.yaml"
    path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic reversible model\n"
        "  site_types:\n"
        "    - id: star\n"
        "      total_sites: 1.0\n"
        "      unit: fraction\n"
        "  species:\n"
        "    surface:\n"
        "      A_star:\n"
        "        phase: surface\n"
        "        site_type: star\n"
        "  steps:\n"
        "    - id: forward\n"
        "      reversible: false\n"
        "      reactants:\n"
        "        star: 1\n"
        "      products:\n"
        "        A_star: 1\n"
        "      rate_constant_forward: k_forward\n"
        "    - id: reverse\n"
        "      reversible: false\n"
        "      reactants:\n"
        "        A_star: 1\n"
        "      products:\n"
        "        star: 1\n"
        "      rate_constant_forward: k_reverse\n",
        encoding="utf-8",
    )
    return path
