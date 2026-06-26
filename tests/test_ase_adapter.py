from __future__ import annotations

import pytest

from qchem_workbench.backends.ase_adapter import from_ase_atoms, to_ase_atoms
from qchem_workbench.core.geometry import Atom
from qchem_workbench.core.structure import AtomisticStructure


def test_ase_adapter_import_does_not_require_ase():
    import qchem_workbench.backends.ase_adapter as ase_adapter

    assert callable(ase_adapter.to_ase_atoms)
    assert callable(ase_adapter.from_ase_atoms)


def test_molecule_conversion_with_ase():
    pytest.importorskip("ase")
    structure = AtomisticStructure(
        atoms=(Atom("O", 0.0, 0.0, 0.0), Atom("H", 0.0, 0.0, 1.0)),
        charge=0,
        multiplicity=1,
        metadata={"label": "synthetic fixture molecule"},
    )

    atoms = to_ase_atoms(structure)
    round_tripped = from_ase_atoms(atoms)

    assert atoms.get_chemical_symbols() == ["O", "H"]
    assert round_tripped.atoms == structure.atoms
    assert round_tripped.cell is None
    assert round_tripped.pbc == (False, False, False)
    assert round_tripped.charge == 0
    assert round_tripped.multiplicity == 1
    assert round_tripped.metadata["label"] == "synthetic fixture molecule"


def test_periodic_cell_conversion_with_ase():
    pytest.importorskip("ase")
    structure = AtomisticStructure(
        atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
        cell=((3.6, 0.0, 0.0), (0.0, 3.6, 0.0), (0.0, 0.0, 3.6)),
        pbc=(True, True, True),
        metadata={"label": "synthetic fixture cell"},
    )

    atoms = to_ase_atoms(structure)
    round_tripped = from_ase_atoms(atoms)

    assert tuple(bool(flag) for flag in atoms.get_pbc()) == (True, True, True)
    assert round_tripped.cell == structure.cell
    assert round_tripped.pbc == structure.pbc
    assert round_tripped.metadata["label"] == "synthetic fixture cell"
