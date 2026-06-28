from __future__ import annotations

import csv

import pytest

from qchem_workbench.cli import main
from qchem_workbench.microkinetics.parameters import rate_parameter_set_from_mapping
from qchem_workbench.microkinetics.rates import (
    microkinetic_rate_analysis,
    write_rate_analysis_csv,
)
from qchem_workbench.microkinetics.schema import load_microkinetic_model


def test_net_step_rates_and_species_production(tmp_path):
    model = load_microkinetic_model(_write_production_model(tmp_path))
    analysis = microkinetic_rate_analysis(
        model,
        _parameters({"k_product": 2.0}),
        {"A_star": 0.25, "star": 0.75},
        {},
    )

    step = analysis.step_rates[0]
    species_rates = {row.species_id: row for row in analysis.species_rates}

    assert step.net_rate == pytest.approx(0.5)
    assert species_rates["A_star"].net_rate == pytest.approx(-0.5)
    assert species_rates["P_g"].net_rate == pytest.approx(0.5)


def test_tof_with_explicit_site_count(tmp_path):
    model = load_microkinetic_model(_write_production_model(tmp_path))

    analysis = microkinetic_rate_analysis(
        model,
        _parameters({"k_product": 2.0}),
        {"A_star": 0.25, "star": 0.75},
        {},
        tof_species="P_g",
        active_site_count=2.0,
    )

    assert analysis.turnover_frequency == pytest.approx(0.25)
    assert analysis.turnover_frequency_unit == "s^-1 per active_site"


def test_tof_missing_site_count_is_error(tmp_path):
    model = load_microkinetic_model(_write_production_model(tmp_path))

    with pytest.raises(ValueError, match="active_site_count"):
        microkinetic_rate_analysis(
            model,
            _parameters({"k_product": 2.0}),
            {"A_star": 0.25, "star": 0.75},
            {},
            tof_species="P_g",
        )


def test_rate_analysis_csv(tmp_path):
    model = load_microkinetic_model(_write_production_model(tmp_path))
    analysis = microkinetic_rate_analysis(
        model,
        _parameters({"k_product": 2.0}),
        {"A_star": 0.25, "star": 0.75},
        {},
        tof_species="P_g",
        active_site_count=2.0,
    )
    out_path = tmp_path / "rates.csv"

    write_rate_analysis_csv(analysis, out_path)

    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["row_type"] for row in rows} == {"step", "species", "tof"}


def test_microkinetics_rates_cli(tmp_path, capsys):
    model_path = _write_production_model(tmp_path)
    parameter_path = _write_parameter_file(tmp_path)
    conditions_path = _write_conditions_file(tmp_path, parameter_path.name)
    state_path = _write_state_file(tmp_path)
    out_path = tmp_path / "results" / "rates.csv"

    exit_code = main(
        [
            "microkinetics",
            "rates",
            str(model_path),
            "--state",
            str(state_path),
            "--conditions",
            str(conditions_path),
            "--tof-species",
            "P_g",
            "--site-count",
            "2.0",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "tof\tP_g" in captured.out
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
        "    k_product:\n"
        "      value: 2.0\n"
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
        "    A_star: 0.25\n"
        "    star: 0.75\n"
        "  time_grid: [0.0, 1.0]\n",
        encoding="utf-8",
    )
    return path


def _write_state_file(tmp_path):
    path = tmp_path / "steady_state.csv"
    path.write_text(
        "species,coverage,residual,success,max_abs_residual,solver_message\n"
        "A_star,0.25,0.0,True,0.0,synthetic\n"
        "star,0.75,0.0,True,0.0,synthetic\n",
        encoding="utf-8",
    )
    return path


def _write_production_model(tmp_path):
    path = tmp_path / "production_model.yaml"
    path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic product formation model\n"
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
