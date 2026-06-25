"""Backend-independent calculation specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CalculationSpec:
    """Generic calculation request independent of a specific backend."""

    backend: str
    method: str
    basis: str | None
    task: str
    solvent: str | None = None
    charge: int | None = None
    multiplicity: int | None = None
    keywords: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "method": self.method,
            "basis": self.basis,
            "task": self.task,
            "solvent": self.solvent,
            "charge": self.charge,
            "multiplicity": self.multiplicity,
            "keywords": dict(self.keywords),
        }
