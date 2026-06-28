from __future__ import annotations

import pytest

from qchem_workbench.microkinetics.schema import load_microkinetic_model


def test_valid_minimal_network(tmp_path):
    path = _write_model(tmp_path)

    model = load_microkinetic_model(path)

    assert model.name == "synthetic co oxidation bookkeeping"
    assert set(model.site_types) == {"star"}
    assert set(model.gas_species) == {"CO_g"}
    assert set(model.surface_species) == {"CO_star"}
    assert model.steps[0].reversible is True
    assert model.rate_parameter_ids == ("k_co_ads_f", "k_co_ads_r")


def test_duplicate_species_id_across_phases_is_error(tmp_path):
    path = _write_model(
        tmp_path,
        species=(
            "  species:\n"
            "    gas:\n"
            "      CO_star:\n"
            "        phase: gas\n"
            "    surface:\n"
            "      CO_star:\n"
            "        phase: surface\n"
            "        site_type: star\n"
        ),
    )

    with pytest.raises(ValueError, match="duplicate species ID"):
        load_microkinetic_model(path)


def test_missing_rate_parameter_when_declared_set_is_error(tmp_path):
    path = _write_model(
        tmp_path,
        rate_parameters=(
            "  rate_parameters:\n"
            "    - k_co_ads_f\n"
        ),
    )

    with pytest.raises(ValueError, match="missing rate parameter"):
        load_microkinetic_model(path)


def test_missing_site_type_is_error(tmp_path):
    path = _write_model(
        tmp_path,
        site_types="  site_types: []\n",
    )

    with pytest.raises(ValueError, match="missing site type"):
        load_microkinetic_model(path)


def test_invalid_stoichiometry_is_error(tmp_path):
    path = _write_model(
        tmp_path,
        steps=(
            "  steps:\n"
            "    - id: bad_ads\n"
            "      reversible: false\n"
            "      reactants:\n"
            "        CO_g: 1\n"
            "        star: 0\n"
            "      products:\n"
            "        CO_star: 1\n"
            "      rate_constant_forward: k_bad\n"
        ),
    )

    with pytest.raises(ValueError, match="coefficient"):
        load_microkinetic_model(path)


def test_reversible_step_without_reverse_parameter_is_error(tmp_path):
    path = _write_model(
        tmp_path,
        steps=(
            "  steps:\n"
            "    - id: bad_reversible\n"
            "      reversible: true\n"
            "      reactants:\n"
            "        CO_g: 1\n"
            "        star: 1\n"
            "      products:\n"
            "        CO_star: 1\n"
            "      rate_constant_forward: k_bad\n"
        ),
    )

    with pytest.raises(ValueError, match="rate_constant_reverse"):
        load_microkinetic_model(path)


def _write_model(
    tmp_path,
    *,
    site_types: str = (
        "  site_types:\n"
        "    - id: star\n"
        "      total_sites: 1.0\n"
        "      unit: fraction\n"
    ),
    species: str = (
        "  species:\n"
        "    gas:\n"
        "      CO_g:\n"
        "        phase: gas\n"
        "    surface:\n"
        "      CO_star:\n"
        "        phase: surface\n"
        "        site_type: star\n"
    ),
    steps: str = (
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
    ),
    rate_parameters: str = (
        "  rate_parameters:\n"
        "    - k_co_ads_f\n"
        "    - k_co_ads_r\n"
    ),
):
    path = tmp_path / "microkinetic_model.yaml"
    path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic co oxidation bookkeeping\n"
        f"{site_types}"
        f"{species}"
        f"{steps}"
        f"{rate_parameters}",
        encoding="utf-8",
    )
    return path
