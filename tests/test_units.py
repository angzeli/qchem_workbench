from __future__ import annotations

import pytest

from qchem_workbench.core.units import HARTREE_TO_EV, hartree_to_ev


def test_hartree_to_ev_conversion():
    assert hartree_to_ev(1.0) == pytest.approx(HARTREE_TO_EV)


def test_hartree_to_ev_preserves_missing_value():
    assert hartree_to_ev(None) is None
