from __future__ import annotations

import pytest

from qchem_workbench.core.units import (
    RY_PER_BOHR_TO_EV_PER_ANGSTROM,
    HARTREE_TO_EV,
    hartree_to_ev,
    ry_per_bohr_to_ev_per_angstrom,
)


def test_hartree_to_ev_conversion():
    assert hartree_to_ev(1.0) == pytest.approx(HARTREE_TO_EV)


def test_hartree_to_ev_preserves_missing_value():
    assert hartree_to_ev(None) is None


def test_ry_per_bohr_to_ev_per_angstrom_conversion():
    assert ry_per_bohr_to_ev_per_angstrom(1.0) == pytest.approx(
        RY_PER_BOHR_TO_EV_PER_ANGSTROM
    )
