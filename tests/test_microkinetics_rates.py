from __future__ import annotations

import pytest

from qchem_workbench.microkinetics.parameters import rate_parameter_set_from_mapping
from qchem_workbench.microkinetics.rates import build_rate_evaluator
from qchem_workbench.microkinetics.schema import load_microkinetic_model


def test_single_irreversible_step_rate_vector(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, reversible=False))
    evaluator = build_rate_evaluator(model, _parameters({"k_ads": 2.0}))

    rates = evaluator.step_rates({"star": 0.5, "CO_star": 0.0}, {"CO_g": 3.0})
    vector = evaluator.rate_vector({"star": 0.5, "CO_star": 0.0}, {"CO_g": 3.0})

    assert rates["co_ads"].net_rate == pytest.approx(3.0)
    assert vector["star"] == pytest.approx(-3.0)
    assert vector["CO_star"] == pytest.approx(3.0)


def test_reversible_adsorption_step(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, reversible=True))
    evaluator = build_rate_evaluator(model, _parameters({"k_ads_f": 2.0, "k_ads_r": 1.0}))

    rates = evaluator.step_rates({"star": 0.5, "CO_star": 0.25}, {"CO_g": 1.0})

    assert rates["co_ads"].forward_rate == pytest.approx(1.0)
    assert rates["co_ads"].reverse_rate == pytest.approx(0.25)
    assert rates["co_ads"].net_rate == pytest.approx(0.75)


def test_two_step_network(tmp_path):
    model = load_microkinetic_model(
        _write_model(
            tmp_path,
            extra_step=(
                "    - id: co_desorb\n"
                "      reversible: false\n"
                "      reactants:\n"
                "        CO_star: 1\n"
                "      products:\n"
                "        CO_g: 1\n"
                "        star: 1\n"
                "      rate_constant_forward: k_des\n"
            ),
        )
    )
    evaluator = build_rate_evaluator(
        model,
        _parameters({"k_ads": 1.0, "k_des": 0.5}),
    )

    vector = evaluator.rate_vector({"star": 0.8, "CO_star": 0.2}, {"CO_g": 1.0})

    assert vector["CO_star"] == pytest.approx(0.7)
    assert vector["star"] == pytest.approx(-0.7)


def test_missing_external_condition_is_error(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, reversible=False))
    evaluator = build_rate_evaluator(model, _parameters({"k_ads": 1.0}))

    with pytest.raises(ValueError, match="gas activity/pressure"):
        evaluator.step_rates({"star": 1.0, "CO_star": 0.0}, {})


def test_site_balance_check(tmp_path):
    model = load_microkinetic_model(_write_model(tmp_path, reversible=False))
    evaluator = build_rate_evaluator(model, _parameters({"k_ads": 1.0}))

    residuals = evaluator.site_balance_residuals({"star": 0.4, "CO_star": 0.6})
    warnings = evaluator.site_balance_warnings({"star": 0.4, "CO_star": 0.5})

    assert residuals[0].residual == pytest.approx(0.0)
    assert warnings


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


def _write_model(tmp_path, *, reversible: bool = False, extra_step: str = ""):
    path = tmp_path / "model.yaml"
    reverse = "      rate_constant_reverse: k_ads_r\n" if reversible else ""
    forward_id = "k_ads_f" if reversible else "k_ads"
    path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic adsorption network\n"
        "  site_types:\n"
        "    - id: star\n"
        "      total_sites: 1.0\n"
        "      unit: fraction\n"
        "  species:\n"
        "    gas:\n"
        "      CO_g:\n"
        "        phase: gas\n"
        "    surface:\n"
        "      CO_star:\n"
        "        phase: surface\n"
        "        site_type: star\n"
        "  steps:\n"
        "    - id: co_ads\n"
        f"      reversible: {str(reversible).lower()}\n"
        "      reactants:\n"
        "        CO_g: 1\n"
        "        star: 1\n"
        "      products:\n"
        "        CO_star: 1\n"
        f"      rate_constant_forward: {forward_id}\n"
        f"{reverse}"
        f"{extra_step}",
        encoding="utf-8",
    )
    return path
