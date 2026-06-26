from __future__ import annotations

import pytest

from qchem_workbench.analysis.che import (
    BOLTZMANN_EV_PER_K,
    DEFAULT_CHE_TEMPERATURE_K,
    LN_10,
    che_free_energy_table,
    load_che_pathway,
)
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.units import HARTREE_TO_EV


def test_load_neutral_che_reaction_with_zero_proton_electron_pairs(tmp_path):
    path = tmp_path / "che.yaml"
    path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r0\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n"
        "    proton_electron_pairs: 0\n"
        "    notes: synthetic fixture neutral bookkeeping step\n",
        encoding="utf-8",
    )

    pathway = load_che_pathway(path)

    reaction = pathway.reactions[0]
    assert reaction.id == "r0"
    assert reaction.proton_electron_pairs == 0.0
    assert reaction.potential_V is None


def test_load_one_proton_electron_pair_reaction(tmp_path):
    path = tmp_path / "che.yaml"
    path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n"
        "    proton_electron_pairs: 1\n"
        "    potential_V: 0.25\n"
        "    potential_reference: SHE\n"
        "    correction_terms:\n"
        "      - label: user supplied term\n"
        "        value_eV: 0.10\n"
        "        sign_convention: added to uncorrected delta G\n"
        "        source: synthetic fixture table\n",
        encoding="utf-8",
    )

    pathway = load_che_pathway(path)

    reaction = pathway.reactions[0]
    assert reaction.proton_electron_pairs == 1.0
    assert reaction.potential_V == 0.25
    assert reaction.potential_reference == "SHE"
    assert reaction.correction_terms[0].value_eV == 0.10


def test_load_pH_and_temperature_fields(tmp_path):
    path = tmp_path / "che.yaml"
    path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n"
        "    proton_electron_pairs: 1\n"
        "    pH: 7\n"
        "    potential_V: -0.1\n"
        "    potential_reference: user_defined\n"
        "    temperature_K: 298.15\n",
        encoding="utf-8",
    )

    reaction = load_che_pathway(path).reactions[0]

    assert reaction.pH == 7.0
    assert reaction.temperature_K == 298.15
    assert reaction.potential_reference == "user_defined"


def test_missing_potential_reference_is_error(tmp_path):
    path = tmp_path / "che.yaml"
    path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n"
        "    proton_electron_pairs: 1\n"
        "    potential_V: 0.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="potential_reference is required"):
        load_che_pathway(path)


def test_unsupported_potential_reference_is_error(tmp_path):
    path = tmp_path / "che.yaml"
    path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n"
        "    proton_electron_pairs: 1\n"
        "    potential_V: 0.0\n"
        "    potential_reference: unknown_reference\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported"):
        load_che_pathway(path)


def test_che_corrected_delta_g_at_zero_potential(tmp_path):
    pathway = _load_che_fixture(
        tmp_path,
        "    proton_electron_pairs: 1\n"
        "    potential_V: 0.0\n"
        "    potential_reference: SHE\n",
    )

    row = che_free_energy_table(pathway, _gibbs_results(a=-2.0, b=-1.9))[0]

    assert row.complete is True
    assert row.uncorrected_delta_g_ev == pytest.approx(0.1 * HARTREE_TO_EV)
    assert row.correction_total_eV == pytest.approx(0.0)
    assert row.corrected_delta_g_ev == pytest.approx(row.uncorrected_delta_g_ev)
    assert row.correction_terms[0].label == "CHE potential correction"


def test_che_corrected_delta_g_at_nonzero_potential(tmp_path):
    pathway = _load_che_fixture(
        tmp_path,
        "    proton_electron_pairs: 1\n"
        "    potential_V: 0.5\n"
        "    potential_reference: SHE\n",
    )

    row = che_free_energy_table(pathway, _gibbs_results(a=-2.0, b=-1.9))[0]

    assert row.correction_total_eV == pytest.approx(-0.5)
    assert row.corrected_delta_g_ev == pytest.approx(0.1 * HARTREE_TO_EV - 0.5)
    assert row.correction_terms[0].sign_convention.startswith("-n * U")


def test_che_pH_correction(tmp_path):
    pathway = _load_che_fixture(
        tmp_path,
        "    proton_electron_pairs: 1\n"
        "    pH: 7\n",
    )

    row = che_free_energy_table(pathway, _gibbs_results(a=-2.0, b=-2.0))[0]
    expected = BOLTZMANN_EV_PER_K * DEFAULT_CHE_TEMPERATURE_K * LN_10 * 7.0

    assert row.correction_total_eV == pytest.approx(expected)
    assert row.corrected_delta_g_ev == pytest.approx(expected)
    assert row.correction_terms[0].label == "CHE pH correction"


def test_che_missing_gibbs_remains_incomplete(tmp_path):
    pathway = _load_che_fixture(
        tmp_path,
        "    proton_electron_pairs: 1\n"
        "    potential_V: 0.5\n"
        "    potential_reference: SHE\n",
    )

    row = che_free_energy_table(
        pathway,
        [
            CalculationResult(
                species_name="A",
                backend="gaussian",
                method="b3lyp",
                basis="def2-svp",
                task="freq",
                success=True,
                gibbs_free_energy_hartree=-2.0,
            )
        ],
    )[0]

    assert row.complete is False
    assert row.uncorrected_delta_g_ev is None
    assert row.corrected_delta_g_ev is None
    assert row.missing_species == ("B",)
    assert row.correction_total_eV == pytest.approx(-0.5)


def _load_che_fixture(tmp_path, extra_fields: str):
    path = tmp_path / "che.yaml"
    path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n"
        f"{extra_fields}",
        encoding="utf-8",
    )
    return load_che_pathway(path)


def _gibbs_results(a: float, b: float):
    return [
        CalculationResult(
            species_name="A",
            backend="gaussian",
            method="b3lyp",
            basis="def2-svp",
            task="freq",
            success=True,
            gibbs_free_energy_hartree=a,
        ),
        CalculationResult(
            species_name="B",
            backend="gaussian",
            method="b3lyp",
            basis="def2-svp",
            task="freq",
            success=True,
            gibbs_free_energy_hartree=b,
        ),
    ]
