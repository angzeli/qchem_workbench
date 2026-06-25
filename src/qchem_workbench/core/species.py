"""Generic molecular species model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Species:
    """Backend-independent description of a molecular species."""

    name: str
    formula: str | None
    charge: int
    multiplicity: int
    geometry_path: Path
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("species name cannot be empty")
        if self.multiplicity <= 0:
            raise ValueError("species multiplicity must be positive")
        if isinstance(self.geometry_path, str) and not self.geometry_path.strip():
            raise ValueError("species geometry_path cannot be empty")
        if self.geometry_path is None:
            raise ValueError("species geometry_path cannot be empty")

        object.__setattr__(self, "geometry_path", Path(self.geometry_path))
        object.__setattr__(self, "tags", tuple(self.tags))

    @property
    def pyscf_spin(self) -> int:
        """Return the PySCF spin value, multiplicity - 1 for ordinary cases."""

        return self.multiplicity - 1
