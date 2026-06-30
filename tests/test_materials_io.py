from __future__ import annotations

import json

import pytest

from qchem_workbench.cli import main
from qchem_workbench.materials import (
    MaterialsStructureIOError,
    inspect_structure,
    load_structures,
)


def test_inspect_xyz_molecule(tmp_path):
    xyz_path = tmp_path / "water.xyz"
    xyz_path.write_text(
        "3\n"
        "synthetic fixture water geometry\n"
        "O 0 0 0\n"
        "H 0 0 1\n"
        "H 0 1 0\n",
        encoding="utf-8",
    )

    summary = inspect_structure(xyz_path)
    payload = summary.to_dict()
    json.dumps(payload)

    assert summary.detected_format == "xyz"
    assert summary.frame_count == 1
    assert summary.atom_count == 3
    assert summary.formula == "H2O"
    assert summary.periodic is False
    assert summary.pbc == (False, False, False)
    assert summary.coordinate_unit == "angstrom"
    assert summary.cell is None


def test_materials_inspect_cli_xyz(tmp_path, capsys):
    xyz_path = tmp_path / "co.xyz"
    xyz_path.write_text(
        "2\n"
        "synthetic fixture carbon monoxide geometry\n"
        "C 0 0 0\n"
        "O 0 0 1.1\n",
        encoding="utf-8",
    )

    exit_code = main(["materials", "inspect", str(xyz_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "detected_format\txyz" in captured.out
    assert "atoms\t2" in captured.out
    assert "formula\tCO" in captured.out
    assert "coordinate_unit\tangstrom" in captured.out
    assert "cell_vectors\t" in captured.out


def test_unsupported_structure_without_extension_errors(tmp_path):
    structure_path = tmp_path / "structure"
    structure_path.write_text("not a supported structure fixture\n", encoding="utf-8")

    with pytest.raises(MaterialsStructureIOError, match="file extension is required"):
        load_structures(structure_path)


def test_materials_inspect_cli_unsupported_format(tmp_path, capsys):
    structure_path = tmp_path / "structure"
    structure_path.write_text("not a supported structure fixture\n", encoding="utf-8")

    exit_code = main(["materials", "inspect", str(structure_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "unsupported structure format" in captured.err


def test_inspect_cif_with_optional_ase(tmp_path):
    pytest.importorskip("ase")
    from ase import Atoms
    from ase.io import write

    cif_path = tmp_path / "cu.cif"
    atoms = Atoms(
        symbols=["Cu"],
        positions=[(0.0, 0.0, 0.0)],
        cell=[3.6, 3.6, 3.6],
        pbc=True,
    )
    write(cif_path, atoms, format="cif")

    summary = inspect_structure(cif_path)

    assert summary.detected_format == "cif"
    assert summary.atom_count == 1
    assert summary.formula == "Cu"
    assert summary.periodic is True
    assert summary.pbc == (True, True, True)
    assert summary.cell is not None
    assert summary.cell_unit == "angstrom"
