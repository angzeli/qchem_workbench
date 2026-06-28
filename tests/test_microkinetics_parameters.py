from __future__ import annotations

import math

import pytest

from qchem_workbench.microkinetics.parameters import (
    BOLTZMANN_EV_PER_K,
    PLANCK_EV_S,
    load_rate_parameter_set,
)


def test_direct_rate_constant(tmp_path):
    path = _write_parameters(
        tmp_path,
        rate_constants=(
            "    k_decay:\n"
            "      value: 0.25\n"
            "      unit: s^-1\n"
            "      source: synthetic test value\n"
        ),
    )

    parameters = load_rate_parameter_set(path)
    rate = parameters.evaluate("k_decay")

    assert rate.value == pytest.approx(0.25)
    assert rate.unit == "s^-1"
    assert rate.warnings == ()


def test_arrhenius_evaluation(tmp_path):
    path = _write_parameters(
        tmp_path,
        arrhenius=(
            "    k_arr:\n"
            "      pre_exponential: 10000000000000.0\n"
            "      pre_exponential_unit: s^-1\n"
            "      activation_energy_eV: 0.5\n"
            "      source: synthetic test value\n"
        ),
    )

    parameters = load_rate_parameter_set(path)
    rate = parameters.evaluate("k_arr", temperature_K=500.0)

    expected = 1.0e13 * math.exp(-0.5 / (BOLTZMANN_EV_PER_K * 500.0))
    assert rate.value == pytest.approx(expected)
    assert rate.temperature_K == 500.0


def test_eyring_evaluation(tmp_path):
    path = _write_parameters(
        tmp_path,
        eyring=(
            "    k_eyring:\n"
            "      activation_free_energy_eV: 0.65\n"
            "      temperature_K: 298.15\n"
            "      rate_constant_unit: s^-1\n"
            "      standard_state_note: synthetic example state\n"
            "      source: synthetic test value\n"
        ),
    )

    parameters = load_rate_parameter_set(path)
    rate = parameters.evaluate("k_eyring")

    expected = (BOLTZMANN_EV_PER_K * 298.15 / PLANCK_EV_S) * math.exp(
        -0.65 / (BOLTZMANN_EV_PER_K * 298.15)
    )
    assert rate.value == pytest.approx(expected)
    assert rate.unit == "s^-1"


def test_missing_units_are_errors(tmp_path):
    path = _write_parameters(
        tmp_path,
        rate_constants=(
            "    k_bad:\n"
            "      value: 1.0\n"
            "      source: synthetic test value\n"
        ),
    )

    with pytest.raises(ValueError, match="unit"):
        load_rate_parameter_set(path)


def test_missing_provenance_is_warning(tmp_path):
    path = _write_parameters(
        tmp_path,
        rate_constants=(
            "    k_unlabelled:\n"
            "      value: 1.0\n"
            "      unit: s^-1\n"
        ),
    )

    parameters = load_rate_parameter_set(path)
    rate = parameters.evaluate("k_unlabelled")

    assert rate.warnings == ("rate parameter source/provenance is missing",)


def _write_parameters(
    tmp_path,
    *,
    rate_constants: str = "",
    arrhenius: str = "",
    eyring: str = "",
):
    path = tmp_path / "rate_parameters.yaml"
    path.write_text(
        "schema_version: 1\n"
        "rate_parameters:\n"
        "  rate_constants:\n"
        f"{rate_constants}"
        "  arrhenius:\n"
        f"{arrhenius}"
        "  eyring:\n"
        f"{eyring}",
        encoding="utf-8",
    )
    return path
