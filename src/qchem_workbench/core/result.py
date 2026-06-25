"""Backend-independent calculation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CalculationResult:
    """Generic calculation result with distinct energy fields."""

    species_name: str
    backend: str
    method: str
    basis: str | None
    task: str
    success: bool
    electronic_energy_hartree: float | None = None
    gibbs_free_energy_hartree: float | None = None
    zero_point_correction_hartree: float | None = None
    thermal_correction_gibbs_hartree: float | None = None
    homo_ev: float | None = None
    lumo_ev: float | None = None
    gap_ev: float | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_name": self.species_name,
            "backend": self.backend,
            "method": self.method,
            "basis": self.basis,
            "task": self.task,
            "success": self.success,
            "electronic_energy_hartree": self.electronic_energy_hartree,
            "gibbs_free_energy_hartree": self.gibbs_free_energy_hartree,
            "zero_point_correction_hartree": self.zero_point_correction_hartree,
            "thermal_correction_gibbs_hartree": self.thermal_correction_gibbs_hartree,
            "homo_ev": self.homo_ev,
            "lumo_ev": self.lumo_ev,
            "gap_ev": self.gap_ev,
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
            "source_path": str(self.source_path) if self.source_path else None,
        }
