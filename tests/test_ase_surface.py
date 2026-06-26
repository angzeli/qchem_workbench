from __future__ import annotations

import pytest

from qchem_workbench.backends.ase_surface import (
    STARTING_STRUCTURE_WARNING,
    add_vacuum,
    build_fcc_surface,
    repeat_slab_from_bulk,
)
from qchem_workbench.core.geometry import Atom
from qchem_workbench.core.structure import AtomisticStructure


def test_ase_surface_import_does_not_require_ase():
    import qchem_workbench.backends.ase_surface as ase_surface

    assert callable(ase_surface.build_fcc_surface)


def test_build_fcc_surface_with_ase():
    pytest.importorskip("ase")

    structure = build_fcc_surface(
        element="Cu",
        facet="111",
        size=(2, 2, 4),
        vacuum=15.0,
    )

    assert len(structure.atoms) == 16
    assert structure.cell is not None
    assert structure.metadata["structure_role"] == "starting_slab"
    assert structure.metadata["warning"] == STARTING_STRUCTURE_WARNING
    assert structure.metadata["facet"] == "111"


def test_repeat_slab_and_add_vacuum_with_ase():
    pytest.importorskip("ase")
    bulk = AtomisticStructure(
        atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
        cell=((3.6, 0.0, 0.0), (0.0, 3.6, 0.0), (0.0, 0.0, 3.6)),
        pbc=(True, True, True),
        metadata={"label": "synthetic fixture bulk"},
    )

    repeated = repeat_slab_from_bulk(bulk, (2, 2, 1))
    with_vacuum = add_vacuum(repeated, 10.0, axis=2)

    assert len(repeated.atoms) == 4
    assert with_vacuum.cell is not None
    assert with_vacuum.metadata["structure_role"] == "starting_slab"
