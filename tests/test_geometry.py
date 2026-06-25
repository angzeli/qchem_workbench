from __future__ import annotations

import pytest

from qchem_workbench.core.geometry import (
    Atom,
    MoleculeGeometry,
    geometry_to_xyz_string,
    read_xyz,
)


def test_read_valid_water_xyz(tmp_path):
    xyz_path = tmp_path / "water.xyz"
    xyz_path.write_text(
        "3\n"
        "synthetic fixture water geometry\n"
        "O 0.0 0.0 0.0\n"
        "H 0.0 0.757 0.586\n"
        "H 0.0 -0.757 0.586\n",
        encoding="utf-8",
    )

    geometry = read_xyz(xyz_path)

    assert geometry.comment == "synthetic fixture water geometry"
    assert geometry.atoms[0] == Atom("O", 0.0, 0.0, 0.0)
    assert len(geometry.atoms) == 3


def test_malformed_atom_count(tmp_path):
    xyz_path = tmp_path / "bad-count.xyz"
    xyz_path.write_text("three\ncomment\nO 0 0 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"bad-count\.xyz:1"):
        read_xyz(xyz_path)


def test_bad_coordinate(tmp_path):
    xyz_path = tmp_path / "bad-coordinate.xyz"
    xyz_path.write_text("1\ncomment\nO 0 nope 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"bad-coordinate\.xyz:3"):
        read_xyz(xyz_path)


def test_unsupported_symbol(tmp_path):
    xyz_path = tmp_path / "unsupported.xyz"
    xyz_path.write_text("1\ncomment\nXx 0 0 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported element symbol"):
        read_xyz(xyz_path)


def test_round_trip_to_xyz_string(tmp_path):
    geometry = MoleculeGeometry(
        atoms=(
            Atom("C", 0.0, 0.0, 0.0),
            Atom("O", 0.0, 0.0, 1.16),
            Atom("O", 0.0, 0.0, -1.16),
        ),
        comment="synthetic fixture co2 geometry",
    )
    xyz_path = tmp_path / "co2.xyz"
    xyz_path.write_text(geometry_to_xyz_string(geometry), encoding="utf-8")

    parsed = read_xyz(xyz_path)

    assert parsed == geometry
