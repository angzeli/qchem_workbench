from __future__ import annotations

import numpy as np
import pytest

from qchem_workbench.core.geometry import (
    Atom,
    MoleculeGeometry,
    atom_distance,
    center_geometry_at_centroid,
    geometry_centroid,
    kabsch_align_geometry,
    pairwise_distance_matrix,
    rmsd,
    translate_geometry,
)


def _water() -> MoleculeGeometry:
    return MoleculeGeometry(
        atoms=(
            Atom("O", 0.0, 0.0, 0.0),
            Atom("H", 0.0, 0.0, 1.0),
            Atom("H", 1.0, 0.0, 0.0),
        ),
        comment="synthetic fixture water geometry",
    )


def test_atom_distance_and_pairwise_distance_matrix():
    geometry = _water()

    matrix = pairwise_distance_matrix(geometry)

    assert atom_distance(geometry, 0, 1) == 1.0
    assert matrix.shape == (3, 3)
    assert np.allclose(np.diag(matrix), 0.0)
    assert matrix[1, 2] == pytest.approx(2**0.5)


def test_center_geometry_at_centroid():
    geometry = translate_geometry(_water(), (3.0, -2.0, 1.0))

    centered = center_geometry_at_centroid(geometry)

    assert geometry_centroid(centered) == pytest.approx((0.0, 0.0, 0.0))


def test_rmsd_identical_geometries():
    geometry = _water()

    assert rmsd(geometry, geometry) == 0.0


def test_rmsd_after_translation_with_alignment():
    reference = _water()
    translated = translate_geometry(reference, (5.0, -2.0, 0.5))

    assert rmsd(translated, reference) > 0.0
    assert rmsd(translated, reference, align=True) == pytest.approx(0.0)


def test_kabsch_alignment_returns_reference_frame_coordinates():
    reference = _water()
    translated = translate_geometry(reference, (5.0, -2.0, 0.5))

    aligned = kabsch_align_geometry(translated, reference)

    assert rmsd(aligned, reference) == pytest.approx(0.0)


def test_rmsd_mismatched_atoms_error():
    geometry_a = _water()
    geometry_b = MoleculeGeometry(
        atoms=(
            Atom("O", 0.0, 0.0, 0.0),
            Atom("H", 0.0, 0.0, 1.0),
            Atom("C", 1.0, 0.0, 0.0),
        ),
        comment="synthetic fixture mismatched geometry",
    )

    with pytest.raises(ValueError, match="same atom ordering"):
        rmsd(geometry_a, geometry_b)
