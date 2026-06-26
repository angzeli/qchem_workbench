from __future__ import annotations

import pytest

from qchem_workbench.analysis.che import load_che_pathway


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
