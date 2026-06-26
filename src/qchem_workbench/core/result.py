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
    method: str | None
    basis: str | None
    task: str | None
    success: bool
    electronic_energy_hartree: float | None = None
    gibbs_free_energy_hartree: float | None = None
    zero_point_correction_hartree: float | None = None
    thermal_correction_energy_hartree: float | None = None
    thermal_correction_enthalpy_hartree: float | None = None
    thermal_correction_gibbs_hartree: float | None = None
    sum_electronic_zero_point_energy_hartree: float | None = None
    sum_electronic_thermal_free_energy_hartree: float | None = None
    homo_ev: float | None = None
    lumo_ev: float | None = None
    gap_ev: float | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None
    conformer_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_name": self.species_name,
            "conformer_id": self.conformer_id,
            "backend": self.backend,
            "method": self.method,
            "basis": self.basis,
            "task": self.task,
            "success": self.success,
            "electronic_energy_hartree": self.electronic_energy_hartree,
            "gibbs_free_energy_hartree": self.gibbs_free_energy_hartree,
            "zero_point_correction_hartree": self.zero_point_correction_hartree,
            "thermal_correction_energy_hartree": self.thermal_correction_energy_hartree,
            "thermal_correction_enthalpy_hartree": (
                self.thermal_correction_enthalpy_hartree
            ),
            "thermal_correction_gibbs_hartree": self.thermal_correction_gibbs_hartree,
            "sum_electronic_zero_point_energy_hartree": (
                self.sum_electronic_zero_point_energy_hartree
            ),
            "sum_electronic_thermal_free_energy_hartree": (
                self.sum_electronic_thermal_free_energy_hartree
            ),
            "homo_ev": self.homo_ev,
            "lumo_ev": self.lumo_ev,
            "gap_ev": self.gap_ev,
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
            "source_path": str(self.source_path) if self.source_path else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalculationResult":
        source_path = data.get("source_path")
        return cls(
            species_name=data["species_name"],
            conformer_id=data.get("conformer_id"),
            backend=data["backend"],
            method=data.get("method"),
            basis=data.get("basis"),
            task=data.get("task"),
            success=bool(data["success"]),
            electronic_energy_hartree=data.get("electronic_energy_hartree"),
            gibbs_free_energy_hartree=data.get("gibbs_free_energy_hartree"),
            zero_point_correction_hartree=data.get("zero_point_correction_hartree"),
            thermal_correction_energy_hartree=data.get(
                "thermal_correction_energy_hartree"
            ),
            thermal_correction_enthalpy_hartree=data.get(
                "thermal_correction_enthalpy_hartree"
            ),
            thermal_correction_gibbs_hartree=data.get(
                "thermal_correction_gibbs_hartree"
            ),
            sum_electronic_zero_point_energy_hartree=data.get(
                "sum_electronic_zero_point_energy_hartree"
            ),
            sum_electronic_thermal_free_energy_hartree=data.get(
                "sum_electronic_thermal_free_energy_hartree"
            ),
            homo_ev=data.get("homo_ev"),
            lumo_ev=data.get("lumo_ev"),
            gap_ev=data.get("gap_ev"),
            warnings=list(data.get("warnings", [])),
            metadata=dict(data.get("metadata", {})),
            source_path=Path(source_path) if source_path else None,
        )
