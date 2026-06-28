from __future__ import annotations

import csv

import pytest

from qchem_workbench.cli import main
from qchem_workbench.microkinetics.parameters import rate_parameter_set_from_mapping
from qchem_workbench.microkinetics.schema import load_microkinetic_model
from qchem_workbench.microkinetics.sensitivity import (
    microkinetic_sensitivity,
    write_sensitivity_csv,
)


def test_simple_two_step_sensitivity(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_two_step_model(tmp_path))

    rows = microkinetic_sensitivity(
        model,
        _parameters({"k_form": 1.0, "k_product": 1.0}),
        {"A_star": 0.2, "star": 0.8},
        {},
        observable="product_rate:P_g",
        perturbation_ln=1e-3,
    )

    by_parameter = {row.parameter_id: row for row in rows}
    assert by_parameter["k_form"].sensitivity == pytest.approx(0.25, rel=1e-2)
    assert by_parameter["k_product"].sensitivity == pytest.approx(0.25, rel=1e-2)
    assert all(row.perturbation_ln == pytest.approx(1e-3) for row in rows)


def test_perturbation_sign_is_visible(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_two_step_model(tmp_path))

    rows = microkinetic_sensitivity(
        model,
        _parameters({"k_form": 1.0, "k_product": 1.0}),
        {"A_star": 0.2, "star": 0.8},
        {},
        observable="product_rate:P_g",
    )

    assert all(row.perturbed_value > row.baseline_value for row in rows)


def test_missing_observable_is_error(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_two_step_model(tmp_path))

    with pytest.raises(ValueError, match="observable species"):
        microkinetic_sensitivity(
            model,
            _parameters({"k_form": 1.0, "k_product": 1.0}),
            {"A_star": 0.2, "star": 0.8},
            {},
            observable="product_rate:missing",
        )


def test_non_converged_baseline_is_reported(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_two_step_model(tmp_path))

    rows = microkinetic_sensitivity(
        model,
        _parameters({"k_form": 1.0, "k_product": 1.0}),
        {"A_star": 0.2, "star": 0.8},
        {},
        observable="product_rate:P_g",
        max_function_evaluations=1,
    )

    assert all(row.baseline_converged is False for row in rows)
    assert all("baseline steady state did not converge" in row.warnings for row in rows)


def test_sensitivity_csv_and_cli(tmp_path, capsys):
    pytest.importorskip("scipy")
    model_path = _write_two_step_model(tmp_path)
    parameter_path = _write_parameter_file(tmp_path)
    conditions_path = _write_conditions_file(tmp_path, parameter_path.name)
    direct_rows = microkinetic_sensitivity(
        load_microkinetic_model(model_path),
        _parameters({"k_form": 1.0, "k_product": 1.0}),
        {"A_star": 0.2, "star": 0.8},
        {},
        observable="product_rate:P_g",
    )
    direct_out = tmp_path / "direct_sensitivity.csv"
    cli_out = tmp_path / "results" / "sensitivity.csv"

    write_sensitivity_csv(direct_rows, direct_out)
    exit_code = main(
        [
            "microkinetics",
            "sensitivity",
            str(model_path),
            "--conditions",
            str(conditions_path),
            "--observable",
            "product_rate:P_g",
            "--out",
            str(cli_out),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "k_product" in captured.out
    assert cli_out.exists()
    with direct_out.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["perturbation_ln"] != ""


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
        "    k_form:\n"
        "      value: 1.0\n"
        "      unit: s^-1\n"
        "      source: synthetic test value\n"
        "    k_product:\n"
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


def _write_two_step_model(tmp_path):
    path = tmp_path / "two_step_model.yaml"
    path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic two-step production model\n"
        "  site_types:\n"
        "    - id: star\n"
        "      total_sites: 1.0\n"
        "      unit: fraction\n"
        "  species:\n"
        "    gas:\n"
        "      P_g:\n"
        "        phase: gas\n"
        "    surface:\n"
        "      A_star:\n"
        "        phase: surface\n"
        "        site_type: star\n"
        "  steps:\n"
        "    - id: formation\n"
        "      reversible: false\n"
        "      reactants:\n"
        "        star: 1\n"
        "      products:\n"
        "        A_star: 1\n"
        "      rate_constant_forward: k_form\n"
        "    - id: product_formation\n"
        "      reversible: false\n"
        "      reactants:\n"
        "        A_star: 1\n"
        "      products:\n"
        "        P_g: 1\n"
        "        star: 1\n"
        "      rate_constant_forward: k_product\n",
        encoding="utf-8",
    )
    return path
