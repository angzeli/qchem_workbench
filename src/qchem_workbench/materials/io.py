"""Structure loading and summaries for materials workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qchem_workbench.backends.ase_adapter import ASEUnavailableError, from_ase_atoms
from qchem_workbench.core.geometry import read_xyz_frames
from qchem_workbench.core.structure import AtomisticStructure, Cell


class MaterialsStructureIOError(ValueError):
    """Raised when a structure file cannot be read by available I/O backends."""


@dataclass(frozen=True)
class StructureSummary:
    """Human-readable summary of an atomistic structure file."""

    path: Path
    detected_format: str
    frame_count: int
    atom_count: int
    formula: str
    periodic: bool
    pbc: tuple[bool, bool, bool]
    coordinate_unit: str
    cell: Cell | None = None
    cell_unit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "detected_format": self.detected_format,
            "frame_count": self.frame_count,
            "atom_count": self.atom_count,
            "formula": self.formula,
            "periodic": self.periodic,
            "pbc": list(self.pbc),
            "coordinate_unit": self.coordinate_unit,
            "cell": [list(vector) for vector in self.cell] if self.cell else None,
            "cell_unit": self.cell_unit,
        }


def inspect_structure(path: Path) -> StructureSummary:
    """Load a structure file and return a compact summary of the first frame."""

    structure_path = Path(path)
    structures = load_structures(structure_path)
    first = structures[0]
    return StructureSummary(
        path=structure_path,
        detected_format=detect_structure_format(structure_path),
        frame_count=len(structures),
        atom_count=len(first.atoms),
        formula=formula_from_atoms(first.atoms),
        periodic=first.is_periodic,
        pbc=first.pbc,
        coordinate_unit=first.coordinate_unit,
        cell=first.cell,
        cell_unit=first.cell_unit if first.cell is not None else None,
    )


def load_structures(path: Path) -> list[AtomisticStructure]:
    """Load one or more structures from a file.

    XYZ is supported directly. Other formats are read through optional ASE when
    available; this function never performs optimisation or coordinate changes.
    """

    structure_path = Path(path)
    if not structure_path.exists():
        raise FileNotFoundError(f"structure file does not exist: {structure_path}")
    detected_format = detect_structure_format(structure_path)
    if detected_format == "xyz":
        return [
            AtomisticStructure.from_molecule_geometry(frame)
            for frame in read_xyz_frames(structure_path)
        ]
    return _load_structures_with_ase(structure_path, detected_format)


def detect_structure_format(path: Path) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    if not suffix:
        raise MaterialsStructureIOError(
            f"{path}: unsupported structure format; file extension is required"
        )
    return suffix


def formula_from_atoms(atoms) -> str:
    counts: dict[str, int] = {}
    for atom in atoms:
        counts[atom.symbol] = counts.get(atom.symbol, 0) + 1

    if "C" in counts:
        symbols = ["C"]
        if "H" in counts:
            symbols.append("H")
        symbols.extend(
            symbol for symbol in sorted(counts) if symbol not in {"C", "H"}
        )
    else:
        symbols = sorted(counts)

    return "".join(
        symbol if counts[symbol] == 1 else f"{symbol}{counts[symbol]}"
        for symbol in symbols
    )


def _load_structures_with_ase(
    path: Path,
    detected_format: str,
) -> list[AtomisticStructure]:
    try:
        import ase.io
    except ImportError as exc:
        raise MaterialsStructureIOError(
            f"{path}: {detected_format} reading requires an optional structure "
            "I/O dependency. Install qchem-workbench[ase] for CIF and other "
            "ASE-readable materials formats."
        ) from exc

    try:
        frames = ase.io.read(str(path), index=":")
    except Exception as exc:
        raise MaterialsStructureIOError(
            f"{path}: could not read {detected_format} structure with ASE: {exc}"
        ) from exc

    if not isinstance(frames, list):
        frames = [frames]
    if not frames:
        raise MaterialsStructureIOError(f"{path}: no structures were read")

    try:
        return [from_ase_atoms(frame) for frame in frames]
    except ASEUnavailableError as exc:
        raise MaterialsStructureIOError(str(exc)) from exc
