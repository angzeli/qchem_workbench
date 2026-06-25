"""Unit conversion helpers."""

from __future__ import annotations


HARTREE_TO_EV = 27.211386245988


def hartree_to_ev(value: float | None) -> float | None:
    if value is None:
        return None
    return value * HARTREE_TO_EV
