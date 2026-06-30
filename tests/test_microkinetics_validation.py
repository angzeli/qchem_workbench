from __future__ import annotations

import json

import pytest

from qchem_workbench.cli import main
from qchem_workbench.microkinetics.parameters import rate_parameter_set_from_mapping
from qchem_workbench.microkinetics.schema import (
    ElementaryStep,
    MicrokineticModel,
    MicrokineticSpecies,
    SiteType,
    load_microkinetic_model,
)
from qchem_workbench.microkinetics.validation import validate_microkinetic_model


def test_valid_model_has_clean_validation_report(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, include_formulas=True))
    parameters = _parameter_set()

    report = validate_microkinetic_model(
        model,
        parameters=parameters,
        initial_coverages={"star": 1.0, "CO_star": 0.0},
    )

    assert report.valid is True
    assert report.error_count == 0
    assert report.warning_count == 0
    json.dumps(report.to_dict())


def test_missing_rate_parameter_is_reported(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, include_formulas=True))
    parameters = rate_parameter_set_from_mapping(
        {
            "rate_constants": {
                "k_co_ads_f": {
                    "value": 1.0,
                    "unit": "s^-1",
                    "source": "synthetic fixture",
                }
            }
        }
    )

    report = validate_microkinetic_model(model, parameters=parameters)

    assert report.valid is False
    assert _codes(report) == {"missing_rate_constant"}


def test_disconnected_species_is_warning(tmp_path):
    model = load_microkinetic_model(
        _write_model(
            tmp_path,
            include_formulas=True,
            extra_species=(
                "      Ar_g:\n"
                "        phase: gas\n"
                "        formula: Ar\n"
            ),
        )
    )

    report = validate_microkinetic_model(model, parameters=_parameter_set())

    assert report.valid is True
    assert "disconnected_species" in _codes(report)


def test_site_imbalance_is_error():
    model = _manual_model(
        steps=(
            ElementaryStep(
                id="bad_site_balance",
                reversible=False,
                reactants={"CO_g": 1.0, "star": 1.0},
                products={"CO_star": 1.0, "star": 1.0},
                rate_constant_forward="k_co_ads_f",
            ),
        )
    )

    report = validate_microkinetic_model(model, parameters=_parameter_set())

    assert report.valid is False
    assert "site_imbalance" in _codes(report)


def test_elemental_imbalance_is_error():
    model = _manual_model(
        surface_species={
            "C_star": MicrokineticSpecies(
                id="C_star",
                phase="surface",
                formula="C",
                site_type="star",
            )
        },
        steps=(
            ElementaryStep(
                id="co_to_c",
                reversible=False,
                reactants={"CO_g": 1.0, "star": 1.0},
                products={"C_star": 1.0},
                rate_constant_forward="k_co_ads_f",
            ),
        ),
    )

    report = validate_microkinetic_model(model, parameters=_parameter_set())

    assert report.valid is False
    assert "elemental_imbalance" in _codes(report)


def test_unused_rate_parameter_is_warning(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, include_formulas=True))
    parameters = rate_parameter_set_from_mapping(
        {
            "rate_constants": {
                "k_co_ads_f": {
                    "value": 1.0,
                    "unit": "s^-1",
                    "source": "synthetic fixture",
                },
                "k_co_ads_r": {
                    "value": 1.0,
                    "unit": "s^-1",
                    "source": "synthetic fixture",
                },
                "k_unused": {
                    "value": 1.0,
                    "unit": "s^-1",
                    "source": "synthetic fixture",
                },
            }
        }
    )

    report = validate_microkinetic_model(model, parameters=parameters)

    assert report.valid is True
    assert "unused_rate_parameter" in _codes(report)


def test_missing_formula_warns_that_elemental_balance_was_not_checked(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, include_formulas=False))

    report = validate_microkinetic_model(model, parameters=_parameter_set())

    assert report.valid is True
    assert "missing_formula_for_elemental_balance" in _codes(report)


def test_impossible_initial_coverages_are_errors(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, include_formulas=True))

    report = validate_microkinetic_model(
        model,
        parameters=_parameter_set(),
        initial_coverages={"star": 0.8, "CO_star": 0.4},
    )

    assert report.valid is False
    assert "initial_coverage_exceeds_site_total" in _codes(report)


def test_invalid_initial_coverage_does_not_crash(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, include_formulas=True))

    report = validate_microkinetic_model(
        model,
        parameters=_parameter_set(),
        initial_coverages={"star": "full", "CO_star": 0.0},
    )

    assert report.valid is False
    assert "invalid_initial_coverage" in _codes(report)


def test_missing_product_definition_is_error():
    model = _manual_model(
        steps=(
            ElementaryStep(
                id="missing_products",
                reversible=False,
                reactants={"CO_g": 1.0, "star": 1.0},
                products={},
                rate_constant_forward="k_co_ads_f",
            ),
        )
    )

    report = validate_microkinetic_model(model, parameters=_parameter_set())

    assert report.valid is False
    assert "missing_products" in _codes(report)


def test_undefined_species_reference_is_reported():
    model = _manual_model(
        steps=(
            ElementaryStep(
                id="undefined_product",
                reversible=False,
                reactants={"CO_g": 1.0, "star": 1.0},
                products={"missing_star": 1.0},
                rate_constant_forward="k_co_ads_f",
            ),
        )
    )

    report = validate_microkinetic_model(model, parameters=_parameter_set())

    assert report.valid is False
    assert "undefined_species_or_site" in _codes(report)


def test_microkinetics_validate_cli(tmp_path, capsys):
    model_path = _write_model(tmp_path, include_formulas=True)
    parameters_path = tmp_path / "parameters.yaml"
    parameters_path.write_text(
        "schema_version: 1\n"
        "rate_parameters:\n"
        "  rate_constants:\n"
        "    k_co_ads_f:\n"
        "      value: 1.0\n"
        "      unit: s^-1\n"
        "      source: synthetic fixture\n"
        "    k_co_ads_r:\n"
        "      value: 1.0\n"
        "      unit: s^-1\n"
        "      source: synthetic fixture\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "microkinetics",
            "validate",
            str(model_path),
            "--parameters",
            str(parameters_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "valid\tTrue" in captured.out
    assert "errors\t0" in captured.out


def _codes(report):
    return {check.code for check in report.checks}


def _parameter_set():
    return rate_parameter_set_from_mapping(
        {
            "rate_constants": {
                "k_co_ads_f": {
                    "value": 1.0,
                    "unit": "s^-1",
                    "source": "synthetic fixture",
                },
                "k_co_ads_r": {
                    "value": 1.0,
                    "unit": "s^-1",
                    "source": "synthetic fixture",
                },
            }
        }
    )


def _manual_model(
    *,
    surface_species: dict[str, MicrokineticSpecies] | None = None,
    steps: tuple[ElementaryStep, ...],
) -> MicrokineticModel:
    site_types = {"star": SiteType(id="star", total_sites=1.0, unit="fraction")}
    gas_species = {
        "CO_g": MicrokineticSpecies(id="CO_g", phase="gas", formula="CO")
    }
    if surface_species is None:
        surface_species = {
            "CO_star": MicrokineticSpecies(
                id="CO_star",
                phase="surface",
                formula="CO",
                site_type="star",
            )
        }
    return MicrokineticModel(
        name="synthetic validation model",
        site_types=site_types,
        gas_species=gas_species,
        surface_species=surface_species,
        steps=steps,
        rate_parameter_ids=("k_co_ads_f", "k_co_ads_r"),
        declared_rate_parameter_ids=("k_co_ads_f", "k_co_ads_r"),
    )


def _write_model(
    tmp_path,
    *,
    include_formulas: bool,
    extra_species: str = "",
):
    formula_lines = (
        "        formula: CO\n"
        if include_formulas
        else ""
    )
    path = tmp_path / "microkinetic_model.yaml"
    path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic validation model\n"
        "  site_types:\n"
        "    - id: star\n"
        "      total_sites: 1.0\n"
        "      unit: fraction\n"
        "  species:\n"
        "    gas:\n"
        "      CO_g:\n"
        "        phase: gas\n"
        f"{formula_lines}"
        f"{extra_species}"
        "    surface:\n"
        "      CO_star:\n"
        "        phase: surface\n"
        f"{formula_lines}"
        "        site_type: star\n"
        "  steps:\n"
        "    - id: co_ads\n"
        "      reversible: true\n"
        "      reactants:\n"
        "        CO_g: 1\n"
        "        star: 1\n"
        "      products:\n"
        "        CO_star: 1\n"
        "      rate_constant_forward: k_co_ads_f\n"
        "      rate_constant_reverse: k_co_ads_r\n"
        "  rate_parameters:\n"
        "    - k_co_ads_f\n"
        "    - k_co_ads_r\n",
        encoding="utf-8",
    )
    return path
