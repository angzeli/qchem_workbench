from __future__ import annotations

from pathlib import Path

import pytest

from qchem_workbench.analysis.reactions import load_pathway
from qchem_workbench.core.species import Species


def _species(name: str) -> Species:
    return Species(
        name=name,
        formula=None,
        charge=0,
        multiplicity=1,
        geometry_path=Path(f"xyz/{name}.xyz"),
    )


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
