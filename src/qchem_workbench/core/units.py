"""Unit conversion helpers."""

from __future__ import annotations


HARTREE_TO_EV = 27.211386245988
BOHR_TO_ANGSTROM = 0.529177210903
RYDBERG_TO_EV = HARTREE_TO_EV * 0.5
RY_PER_BOHR_TO_EV_PER_ANGSTROM = RYDBERG_TO_EV / BOHR_TO_ANGSTROM


def hartree_to_ev(value: float | None) -> float | None:
    if value is None:
        return None
    return value * HARTREE_TO_EV


def ry_per_bohr_to_ev_per_angstrom(value: float | None) -> float | None:
    if value is None:
        return None
    return value * RY_PER_BOHR_TO_EV_PER_ANGSTROM
