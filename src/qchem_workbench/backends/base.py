"""Backend interface for calculation runners."""

from __future__ import annotations

from typing import Protocol

from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species


class Backend(Protocol):
    """Protocol implemented by quantum-chemistry workflow backends."""

    def run(self, species: Species, spec: CalculationSpec) -> CalculationResult:
        """Run a calculation for one species and return a generic result."""
