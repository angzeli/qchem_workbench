from __future__ import annotations

import pytest

from qchem_workbench.core.geometry import Atom, MoleculeGeometry
from qchem_workbench.core.structure import AtomisticStructure


def test_molecule_structure_is_nonperiodic_and_serializable():
    structure = AtomisticStructure(
        atoms=(
            Atom("O", 0.0, 0.0, 0.0),
            Atom("H", 0.0, 0.757, 0.586),
            Atom("H", 0.0, -0.757, 0.586),
        ),
        charge=0,
        multiplicity=1,
        metadata={"label": "synthetic fixture water"},
    )

    payload = structure.to_dict()
    round_tripped = AtomisticStructure.from_dict(payload)

    assert structure.is_molecular is True
    assert structure.is_periodic is False
    assert payload["cell"] is None
    assert payload["pbc"] == [False, False, False]
    assert round_tripped == structure


def test_periodic_structure_with_3x3_cell():
    structure = AtomisticStructure(
        atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
        cell=((3.6, 0.0, 0.0), (0.0, 3.6, 0.0), (0.0, 0.0, 3.6)),
        pbc=(True, True, True),
        metadata={"label": "synthetic fixture cubic cell"},
    )

    assert structure.is_periodic is True
    assert structure.is_molecular is False
    assert structure.to_dict()["cell"] == [
        [3.6, 0.0, 0.0],
        [0.0, 3.6, 0.0],
        [0.0, 0.0, 3.6],
    ]


def test_invalid_cell_shape_is_error():
    with pytest.raises(ValueError, match="3x3"):
        AtomisticStructure(
            atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
            cell=((3.6, 0.0), (0.0, 3.6)),
        )


def test_periodic_flags_require_cell():
    with pytest.raises(ValueError, match="periodic structures require"):
        AtomisticStructure(
            atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
            pbc=(True, True, True),
        )


def test_conversion_from_molecule_geometry():
    geometry = MoleculeGeometry(
        atoms=(Atom("H", 0.0, 0.0, 0.0),),
        comment="synthetic fixture hydrogen atom",
    )

    structure = AtomisticStructure.from_molecule_geometry(
        geometry,
        charge=0,
        multiplicity=2,
    )

    assert structure.atoms == geometry.atoms
    assert structure.charge == 0
    assert structure.multiplicity == 2
    assert structure.metadata["source_comment"] == "synthetic fixture hydrogen atom"
    assert structure.is_molecular is True
