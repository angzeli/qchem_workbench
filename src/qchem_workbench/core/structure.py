"""Generic atomistic structure model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from qchem_workbench.core.geometry import Atom, MoleculeGeometry


Cell = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class AtomisticStructure:
    """Backend-independent atomistic structure for molecules and periodic cells."""

    atoms: tuple[Atom, ...]
    cell: Cell | None = None
    pbc: tuple[bool, bool, bool] = (False, False, False)
    fractional_coordinates: tuple[Vector3, ...] | None = None
    surface_normal: Vector3 | None = None
    fixed_atom_indices: tuple[int, ...] = ()
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
        object.__setattr__(
            self,
            "fractional_coordinates",
            _fractional_coordinates(
                self.fractional_coordinates,
                expected_count=len(atoms),
            ),
        )
        object.__setattr__(
            self,
            "surface_normal",
            _vector3(self.surface_normal, "surface normal"),
        )
        object.__setattr__(
            self,
            "fixed_atom_indices",
            _fixed_atom_indices(self.fixed_atom_indices, len(atoms)),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

        if any(self.pbc) and self.cell is None:
            raise ValueError("periodic structures require a 3x3 cell")
        if self.fractional_coordinates is not None and self.cell is None:
            raise ValueError("fractional coordinates require a 3x3 cell")
        if self.cell is not None and abs(_cell_volume(self.cell)) <= 1e-12:
            raise ValueError("structure cell volume must be nonzero")
        if self.multiplicity is not None and self.multiplicity <= 0:
            raise ValueError("structure multiplicity must be positive")

    @property
    def is_periodic(self) -> bool:
        return any(self.pbc)

    @property
    def is_molecular(self) -> bool:
        return not self.is_periodic

    @property
    def coordinate_unit(self) -> str:
        return "angstrom"

    @property
    def cell_unit(self) -> str:
        return "angstrom"

    @property
    def cell_volume_angstrom3(self) -> float | None:
        if self.cell is None:
            return None
        return abs(_cell_volume(self.cell))

    def fractional_to_cartesian(self, fractional: Vector3) -> Vector3:
        """Convert fractional crystal coordinates to Cartesian Angstrom."""

        if self.cell is None:
            raise ValueError("fractional coordinate conversion requires a 3x3 cell")
        return _fractional_to_cartesian(_vector3(fractional, "fractional"), self.cell)

    def cartesian_to_fractional(self, cartesian: Vector3) -> Vector3:
        """Convert Cartesian Angstrom coordinates to fractional crystal coordinates."""

        if self.cell is None:
            raise ValueError("Cartesian coordinate conversion requires a 3x3 cell")
        return _cartesian_to_fractional(_vector3(cartesian, "Cartesian"), self.cell)

    def atoms_as_fractional(self) -> tuple[Vector3, ...]:
        """Return atom positions as fractional coordinates."""

        if self.fractional_coordinates is not None:
            return self.fractional_coordinates
        return tuple(
            self.cartesian_to_fractional((atom.x, atom.y, atom.z))
            for atom in self.atoms
        )

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

    @classmethod
    def from_fractional_coordinates(
        cls,
        symbols: tuple[str, ...],
        fractional_coordinates: tuple[Vector3, ...],
        *,
        cell: Cell,
        pbc: tuple[bool, bool, bool] = (True, True, True),
        charge: int | None = None,
        multiplicity: int | None = None,
        surface_normal: Vector3 | None = None,
        fixed_atom_indices: tuple[int, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "AtomisticStructure":
        parsed_cell = _cell3x3(cell)
        if parsed_cell is None:
            raise ValueError("fractional coordinate structures require a 3x3 cell")
        fractional = _fractional_coordinates(
            fractional_coordinates,
            expected_count=len(symbols),
        )
        assert fractional is not None
        atoms = tuple(
            Atom(symbol, *(_fractional_to_cartesian(position, parsed_cell)))
            for symbol, position in zip(symbols, fractional)
        )
        return cls(
            atoms=atoms,
            cell=parsed_cell,
            pbc=pbc,
            fractional_coordinates=fractional,
            charge=charge,
            multiplicity=multiplicity,
            surface_normal=surface_normal,
            fixed_atom_indices=fixed_atom_indices,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "atoms": [
                {"symbol": atom.symbol, "x": atom.x, "y": atom.y, "z": atom.z}
                for atom in self.atoms
            ],
            "cell": [list(vector) for vector in self.cell] if self.cell else None,
            "cell_unit": self.cell_unit,
            "coordinate_unit": self.coordinate_unit,
            "pbc": list(self.pbc),
            "fractional_coordinates": (
                [list(position) for position in self.fractional_coordinates]
                if self.fractional_coordinates is not None
                else None
            ),
            "surface_normal": (
                list(self.surface_normal) if self.surface_normal is not None else None
            ),
            "fixed_atom_indices": list(self.fixed_atom_indices),
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
            fractional_coordinates=data.get("fractional_coordinates"),
            surface_normal=data.get("surface_normal"),
            fixed_atom_indices=tuple(data.get("fixed_atom_indices", ())),
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


def _cell_volume(cell: Cell) -> float:
    return float(np.linalg.det(np.array(cell, dtype=float)))


def _fractional_to_cartesian(fractional: Vector3, cell: Cell) -> Vector3:
    vector = np.array(fractional, dtype=float) @ np.array(cell, dtype=float)
    return tuple(float(component) for component in vector)


def _cartesian_to_fractional(cartesian: Vector3, cell: Cell) -> Vector3:
    vector = np.array(cartesian, dtype=float) @ np.linalg.inv(np.array(cell, dtype=float))
    return tuple(float(component) for component in vector)


def _fractional_coordinates(
    value: Any,
    *,
    expected_count: int,
) -> tuple[Vector3, ...] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != expected_count:
        raise ValueError(
            "fractional_coordinates must contain one coordinate triplet per atom"
        )
    return tuple(_vector3(position, "fractional coordinate") for position in value)


def _vector3(value: Any, label: str) -> Vector3 | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"structure {label} must contain three numeric values")
    try:
        return tuple(float(component) for component in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"structure {label} must contain three numeric values"
        ) from exc


def _fixed_atom_indices(value: Any, atom_count: int) -> tuple[int, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("fixed_atom_indices must be a list of atom indices")
    indices = tuple(int(index) for index in value)
    for index in indices:
        if index < 0 or index >= atom_count:
            raise ValueError(f"fixed atom index {index} is out of range")
    return indices


def _pbc3(value: Any) -> tuple[bool, bool, bool]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("structure pbc must contain exactly three flags")
    if not all(isinstance(flag, bool) for flag in value):
        raise ValueError("structure pbc flags must be booleans")
    return (value[0], value[1], value[2])
