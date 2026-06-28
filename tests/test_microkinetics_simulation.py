from __future__ import annotations

import csv

import pytest

from qchem_workbench.cli import main
from qchem_workbench.microkinetics.parameters import rate_parameter_set_from_mapping
from qchem_workbench.microkinetics.schema import load_microkinetic_model
from qchem_workbench.microkinetics.simulation import (
    load_microkinetic_conditions,
    simulate_coverages,
    write_simulation_csv,
)


def test_simple_decay_network(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_decay_model(tmp_path))
    parameters = _parameters({"k_decay": 1.0})

    result = simulate_coverages(
        model,
        parameters,
        {"A_star": 1.0, "star": 0.0},
        {},
        [0.0, 1.0, 2.0],
    )

    assert result.success is True
    assert result.coverages["A_star"][-1] == pytest.approx(0.1353, rel=1e-3)
    assert result.coverages["star"][-1] == pytest.approx(0.8647, rel=1e-3)


def test_reversible_two_state_network(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_reversible_model(tmp_path))
    parameters = _parameters({"k_forward": 1.0, "k_reverse": 1.0})

    result = simulate_coverages(
        model,
        parameters,
        {"A_star": 0.0, "star": 1.0},
        {},
        [0.0, 1.0, 5.0],
    )

    assert result.success is True
    assert result.coverages["A_star"][-1] == pytest.approx(0.5, rel=1e-2)
    assert result.coverages["star"][-1] == pytest.approx(0.5, rel=1e-2)


def test_invalid_initial_coverage_is_error(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_decay_model(tmp_path))

    with pytest.raises(ValueError, match="missing initial coverage"):
        simulate_coverages(model, _parameters({"k_decay": 1.0}), {"A_star": 1.0}, {}, [0, 1])


def test_simulation_csv_generation(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_decay_model(tmp_path))
    result = simulate_coverages(
        model,
        _parameters({"k_decay": 1.0}),
        {"A_star": 1.0, "star": 0.0},
        {},
        [0.0, 1.0],
    )
    out_path = tmp_path / "trajectory.csv"

    write_simulation_csv(result, out_path)

    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["time"] == "0.0"
    assert "A_star" in rows[0]
    assert "star" in rows[0]


def test_microkinetics_simulate_cli(tmp_path, capsys):
    pytest.importorskip("scipy")
    model_path = _write_decay_model(tmp_path)
    parameter_path = _write_parameter_file(tmp_path)
    conditions_path = _write_conditions_file(tmp_path, parameter_path.name)
    out_path = tmp_path / "results" / "trajectory.csv"

    exit_code = main(
        [
            "microkinetics",
            "simulate",
            str(model_path),
            "--conditions",
            str(conditions_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Wrote microkinetic trajectory" in captured.out
    assert out_path.exists()


def test_conditions_loader_resolves_parameter_path(tmp_path):
    parameter_path = _write_parameter_file(tmp_path)
    conditions_path = _write_conditions_file(tmp_path, parameter_path.name)

    conditions = load_microkinetic_conditions(conditions_path)

    assert conditions.rate_parameters_path == parameter_path.resolve()
    assert conditions.time_grid == (0.0, 1.0, 2.0)


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
        "    k_decay:\n"
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
        "  temperature_K: 500.0\n"
        f"  rate_parameters_path: {parameter_file_name}\n"
        "  variables: {}\n"
        "  initial_coverages:\n"
        "    A_star: 1.0\n"
        "    star: 0.0\n"
        "  time_grid: [0.0, 1.0, 2.0]\n",
        encoding="utf-8",
    )
    return path


def _write_decay_model(tmp_path):
    path = tmp_path / "decay_model.yaml"
    path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic decay model\n"
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
        "    - id: decay\n"
        "      reversible: false\n"
        "      reactants:\n"
        "        A_star: 1\n"
        "      products:\n"
        "        star: 1\n"
        "      rate_constant_forward: k_decay\n",
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
