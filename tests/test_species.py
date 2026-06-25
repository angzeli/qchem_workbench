from __future__ import annotations

from pathlib import Path

import pytest

from qchem_workbench.core.species import Species


def test_neutral_singlet_species():
    species = Species(
        name="water",
        formula="H2O",
        charge=0,
        multiplicity=1,
        geometry_path=Path("xyz/water.xyz"),
    )

    assert species.pyscf_spin == 0


def test_anion_doublet_species():
    species = Species(
        name="oxygen_anion",
        formula="O",
        charge=-1,
        multiplicity=2,
        geometry_path=Path("xyz/oxygen_anion.xyz"),
        tags=("synthetic-fixture",),
    )

    assert species.charge == -1
    assert species.pyscf_spin == 1


def test_empty_name_is_invalid():
    with pytest.raises(ValueError, match="name"):
        Species(
            name=" ",
            formula=None,
            charge=0,
            multiplicity=1,
            geometry_path=Path("xyz/species.xyz"),
        )


def test_invalid_multiplicity_is_invalid():
    with pytest.raises(ValueError, match="multiplicity"):
        Species(
            name="invalid",
            formula=None,
            charge=0,
            multiplicity=0,
            geometry_path=Path("xyz/species.xyz"),
        )
