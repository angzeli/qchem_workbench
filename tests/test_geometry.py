from __future__ import annotations

import pytest

from qchem_workbench.core.geometry import (
    Atom,
    MoleculeGeometry,
    geometry_to_xyz_string,
    read_xyz,
    read_xyz_frames,
    write_xyz_frames,
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


def test_read_xyz_frames_single_frame(tmp_path):
    xyz_path = tmp_path / "water.xyz"
    xyz_path.write_text(
        "1\nsynthetic fixture hydrogen geometry\nH 0 0 0\n",
        encoding="utf-8",
    )

    frames = read_xyz_frames(xyz_path)

    assert frames == [
        MoleculeGeometry(
            atoms=(Atom("H", 0.0, 0.0, 0.0),),
            comment="synthetic fixture hydrogen geometry",
        )
    ]


def test_read_xyz_frames_multi_frame_and_read_xyz_rejects_it(tmp_path):
    xyz_path = tmp_path / "trajectory.xyz"
    xyz_path.write_text(
        "1\n"
        "synthetic fixture frame 1\n"
        "H 0 0 0\n"
        "1\n"
        "synthetic fixture frame 2\n"
        "H 0 0 1\n",
        encoding="utf-8",
    )

    frames = read_xyz_frames(xyz_path)

    assert [frame.comment for frame in frames] == [
        "synthetic fixture frame 1",
        "synthetic fixture frame 2",
    ]
    assert frames[1].atoms[0].z == 1.0
    with pytest.raises(ValueError, match="expected single XYZ frame"):
        read_xyz(xyz_path)


def test_read_xyz_frames_malformed_second_frame(tmp_path):
    xyz_path = tmp_path / "bad-trajectory.xyz"
    xyz_path.write_text(
        "1\n"
        "synthetic fixture frame 1\n"
        "H 0 0 0\n"
        "not-a-count\n"
        "synthetic fixture frame 2\n"
        "H 0 0 1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"bad-trajectory\.xyz:4"):
        read_xyz_frames(xyz_path)


def test_write_xyz_frames_round_trip(tmp_path):
    frames = [
        MoleculeGeometry(
            atoms=(Atom("H", 0.0, 0.0, 0.0),),
            comment="synthetic fixture frame 1",
        ),
        MoleculeGeometry(
            atoms=(Atom("H", 0.0, 0.0, 1.0),),
            comment="synthetic fixture frame 2",
        ),
    ]
    xyz_path = tmp_path / "frames.xyz"

    write_xyz_frames(frames, xyz_path)

    assert xyz_path.read_text(encoding="utf-8") == (
        "1\n"
        "synthetic fixture frame 1\n"
        "H 0 0 0\n"
        "1\n"
        "synthetic fixture frame 2\n"
        "H 0 0 1\n"
    )
    assert read_xyz_frames(xyz_path) == frames
