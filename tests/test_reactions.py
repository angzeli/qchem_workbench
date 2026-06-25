from __future__ import annotations

from pathlib import Path

import pytest

from qchem_workbench.analysis.reactions import HARTREE_TO_KJ_MOL
from qchem_workbench.analysis.reactions import load_pathway
from qchem_workbench.analysis.reactions import reaction_electronic_energy_table
from qchem_workbench.analysis.reactions import reaction_gibbs_free_energy_table
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species
from qchem_workbench.core.units import HARTREE_TO_EV


def _species(name: str) -> Species:
    return Species(
        name=name,
        formula=None,
        charge=0,
        multiplicity=1,
        geometry_path=Path(f"xyz/{name}.xyz"),
    )


def _result(name: str, energy: float | None) -> CalculationResult:
    return CalculationResult(
        species_name=name,
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="single_point",
        success=True,
        electronic_energy_hartree=energy,
    )


def _gibbs_result(
    name: str,
    electronic_energy: float | None,
    gibbs_energy: float | None,
) -> CalculationResult:
    result = _result(name, electronic_energy)
    result.gibbs_free_energy_hartree = gibbs_energy
    return result


def test_load_valid_reaction_pathway(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    label: A to B\n"
        "    reactants:\n"
        "      A: 1\n"
        "    products:\n"
        "      B: 1\n"
        "    electrons: 0\n"
        "    protons: 0\n"
        "    notes: Example reaction\n",
        encoding="utf-8",
    )

    pathway = load_pathway(pathway_path, species_registry=[_species("A"), _species("B")])

    assert pathway.reactions[0].id == "r1"
    assert pathway.reactions[0].reactants == {"A": 1.0}
    assert pathway.reactions[0].products == {"B": 1.0}


def test_pathway_missing_species_is_error(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown species B"):
        load_pathway(pathway_path, species_registry=[_species("A")])


def test_duplicate_reaction_id_is_error(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n"
        "  - id: r1\n"
        "    reactants: {B: 1}\n"
        "    products: {A: 1}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate reaction id"):
        load_pathway(pathway_path)


def test_pathway_supports_integer_and_float_coefficients(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants:\n"
        "      A: 2\n"
        "    products:\n"
        "      B: 0.5\n",
        encoding="utf-8",
    )

    reaction = load_pathway(pathway_path).reactions[0]

    assert reaction.reactants["A"] == 2.0
    assert reaction.products["B"] == 0.5


def test_reaction_electronic_energy_a_to_b(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )

    row = reaction_electronic_energy_table(
        load_pathway(pathway_path), [_result("A", -2.0), _result("B", -1.5)]
    )[0]

    assert row.complete is True
    assert row.quantity == "delta_e_electronic"
    assert row.delta_hartree == pytest.approx(0.5)
    assert row.notes == "Sign convention: products minus reactants."


def test_reaction_electronic_energy_with_coefficients(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 2}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )

    row = reaction_electronic_energy_table(
        load_pathway(pathway_path), [_result("A", -1.0), _result("B", -3.0)]
    )[0]

    assert row.delta_hartree == pytest.approx(-1.0)


def test_reaction_electronic_energy_missing_data(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )

    row = reaction_electronic_energy_table(
        load_pathway(pathway_path), [_result("A", -1.0), _result("B", None)]
    )[0]

    assert row.complete is False
    assert row.delta_hartree is None
    assert row.missing_species == ("B",)


def test_reaction_electronic_energy_unit_conversion(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )

    row = reaction_electronic_energy_table(
        load_pathway(pathway_path), [_result("A", -1.0), _result("B", 0.0)]
    )[0]

    assert row.delta_ev == pytest.approx(HARTREE_TO_EV)
    assert row.delta_kj_mol == pytest.approx(HARTREE_TO_KJ_MOL)


def test_reaction_gibbs_free_energy_complete_data(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )

    row = reaction_gibbs_free_energy_table(
        load_pathway(pathway_path),
        [_gibbs_result("A", -100.0, -2.0), _gibbs_result("B", -99.0, -1.25)],
    )[0]

    assert row.complete is True
    assert row.quantity == "delta_g_gibbs"
    assert row.delta_hartree == pytest.approx(0.75)
    assert "No standard-state" in row.notes


def test_reaction_gibbs_free_energy_missing_data(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )

    row = reaction_gibbs_free_energy_table(
        load_pathway(pathway_path),
        [_gibbs_result("A", -100.0, -2.0), _gibbs_result("B", -99.0, None)],
    )[0]

    assert row.complete is False
    assert row.delta_hartree is None
    assert row.missing_species == ("B",)


def test_reaction_gibbs_free_energy_does_not_fallback_to_electronic(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )

    row = reaction_gibbs_free_energy_table(
        load_pathway(pathway_path), [_result("A", -2.0), _result("B", -1.0)]
    )[0]

    assert row.complete is False
    assert row.missing_species == ("A", "B")
