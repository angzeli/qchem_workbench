"""Generic atomistic structure model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from qchem_workbench.core.geometry import Atom, MoleculeGeometry


Cell = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]


@dataclass(frozen=True)
class AtomisticStructure:
    """Backend-independent atomistic structure for molecules and periodic cells."""

    atoms: tuple[Atom, ...]
    cell: Cell | None = None
    pbc: tuple[bool, bool, bool] = (False, False, False)
    charge: int | None = None
    multiplicity: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        atoms = tuple(self.atoms)
        if not atoms:
            raise ValueError("atomistic structure must contain at least one atom")
        object.__setattr__(self, "atoms", atoms)
        object.__setattr__(self, "pbc", _pbc3(self.pbc))
        object.__setattr__(self, "cell", _cell3x3(self.cell))
        object.__setattr__(self, "metadata", dict(self.metadata))

        if any(self.pbc) and self.cell is None:
            raise ValueError("periodic structures require a 3x3 cell")
        if self.multiplicity is not None and self.multiplicity <= 0:
            raise ValueError("structure multiplicity must be positive")

    @property
    def is_periodic(self) -> bool:
        return any(self.pbc)

    @property
    def is_molecular(self) -> bool:
        return not self.is_periodic

    @classmethod
    def from_molecule_geometry(
        cls,
        geometry: MoleculeGeometry,
        *,
        charge: int | None = None,
        multiplicity: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "AtomisticStructure":
        return cls(
            atoms=geometry.atoms,
            charge=charge,
            multiplicity=multiplicity,
            metadata={
                "source_comment": geometry.comment,
                **(metadata or {}),
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "atoms": [
                {"symbol": atom.symbol, "x": atom.x, "y": atom.y, "z": atom.z}
                for atom in self.atoms
            ],
            "cell": [list(vector) for vector in self.cell] if self.cell else None,
            "pbc": list(self.pbc),
            "charge": self.charge,
            "multiplicity": self.multiplicity,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AtomisticStructure":
        atoms = tuple(
            Atom(
                symbol=str(atom["symbol"]),
                x=float(atom["x"]),
                y=float(atom["y"]),
                z=float(atom["z"]),
            )
            for atom in data["atoms"]
        )
        return cls(
            atoms=atoms,
            cell=data.get("cell"),
            pbc=data.get("pbc", (False, False, False)),
            charge=data.get("charge"),
            multiplicity=data.get("multiplicity"),
            metadata=data.get("metadata", {}),
        )


def _cell3x3(value: Any) -> Cell | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("structure cell must be a 3x3 matrix")

    rows: list[tuple[float, float, float]] = []
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            raise ValueError("structure cell must be a 3x3 matrix")
        rows.append(tuple(float(component) for component in row))
    return (rows[0], rows[1], rows[2])


def _pbc3(value: Any) -> tuple[bool, bool, bool]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("structure pbc must contain exactly three flags")
    if not all(isinstance(flag, bool) for flag in value):
        raise ValueError("structure pbc flags must be booleans")
    return (value[0], value[1], value[2])
