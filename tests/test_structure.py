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
    assert structure.cell_unit == "angstrom"
    assert structure.coordinate_unit == "angstrom"


def test_fractional_to_cartesian_conversion():
    structure = AtomisticStructure.from_fractional_coordinates(
        ("Cu",),
        ((0.5, 0.25, 0.0),),
        cell=((4.0, 0.0, 0.0), (0.0, 8.0, 0.0), (0.0, 0.0, 10.0)),
    )

    assert structure.atoms[0].x == pytest.approx(2.0)
    assert structure.atoms[0].y == pytest.approx(2.0)
    assert structure.atoms[0].z == pytest.approx(0.0)
    assert structure.fractional_to_cartesian((0.25, 0.25, 0.25)) == pytest.approx(
        (1.0, 2.0, 2.5)
    )


def test_cartesian_to_fractional_conversion():
    structure = AtomisticStructure(
        atoms=(Atom("Cu", 1.0, 2.0, 2.5),),
        cell=((4.0, 0.0, 0.0), (0.0, 8.0, 0.0), (0.0, 0.0, 10.0)),
        pbc=(True, True, True),
    )

    assert structure.cartesian_to_fractional((1.0, 2.0, 2.5)) == pytest.approx(
        (0.25, 0.25, 0.25)
    )
    assert structure.atoms_as_fractional()[0] == pytest.approx((0.25, 0.25, 0.25))


def test_cell_volume():
    structure = AtomisticStructure(
        atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
        cell=((4.0, 0.0, 0.0), (0.0, 5.0, 0.0), (0.0, 0.0, 6.0)),
        pbc=(True, True, True),
    )

    assert structure.cell_volume_angstrom3 == pytest.approx(120.0)


def test_singular_cell_is_error():
    with pytest.raises(ValueError, match="cell volume"):
        AtomisticStructure(
            atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
            cell=((1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        )


def test_slab_like_structure_with_nonperiodic_z_and_constraints_round_trips():
    structure = AtomisticStructure(
        atoms=(Atom("Cu", 0.0, 0.0, 0.0), Atom("Cu", 0.0, 0.0, 2.0)),
        cell=((3.6, 0.0, 0.0), (0.0, 3.6, 0.0), (0.0, 0.0, 20.0)),
        pbc=(True, True, False),
        surface_normal=(0.0, 0.0, 1.0),
        fixed_atom_indices=(0,),
        metadata={"label": "synthetic fixture slab"},
    )

    payload = structure.to_dict()
    round_tripped = AtomisticStructure.from_dict(payload)

    assert structure.is_periodic is True
    assert structure.pbc == (True, True, False)
    assert payload["surface_normal"] == [0.0, 0.0, 1.0]
    assert payload["fixed_atom_indices"] == [0]
    assert round_tripped == structure


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
