"""XYZ geometry parsing and formatting."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_ELEMENT_SYMBOLS = frozenset(
    {
        "H",
        "He",
        "Li",
        "Be",
        "B",
        "C",
        "N",
        "O",
        "F",
        "Ne",
        "Na",
        "Mg",
        "Al",
        "Si",
        "P",
        "S",
        "Cl",
        "Ar",
        "K",
        "Ca",
        "Sc",
        "Ti",
        "V",
        "Cr",
        "Mn",
        "Fe",
        "Co",
        "Ni",
        "Cu",
        "Zn",
        "Ga",
        "Ge",
        "As",
        "Se",
        "Br",
        "Kr",
        "Rb",
        "Sr",
        "Y",
        "Zr",
        "Nb",
        "Mo",
        "Tc",
        "Ru",
        "Rh",
        "Pd",
        "Ag",
        "Cd",
        "In",
        "Sn",
        "Sb",
        "Te",
        "I",
        "Xe",
        "Cs",
        "Ba",
        "La",
        "Ce",
        "Pr",
        "Nd",
        "Pm",
        "Sm",
        "Eu",
        "Gd",
        "Tb",
        "Dy",
        "Ho",
        "Er",
        "Tm",
        "Yb",
        "Lu",
        "Hf",
        "Ta",
        "W",
        "Re",
        "Os",
        "Ir",
        "Pt",
        "Au",
        "Hg",
        "Tl",
        "Pb",
        "Bi",
        "Po",
        "At",
        "Rn",
    }
)


@dataclass(frozen=True)
class Atom:
    symbol: str
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class MoleculeGeometry:
    atoms: tuple[Atom, ...]
    comment: str


def read_xyz(path: Path) -> MoleculeGeometry:
    frames = read_xyz_frames(path)
    if len(frames) != 1:
        raise ValueError(f"{Path(path)}: expected single XYZ frame, found {len(frames)}")
    return frames[0]


def read_xyz_frames(path: Path) -> list[MoleculeGeometry]:
    xyz_path = Path(path)
    lines = xyz_path.read_text(encoding="utf-8").splitlines()

    if not lines:
        _raise_xyz_error(xyz_path, 1, "missing atom count")

    frames: list[MoleculeGeometry] = []
    line_index = 0
    while line_index < len(lines):
        frames.append(_parse_xyz_frame(xyz_path, lines, line_index))
        line_index += len(frames[-1].atoms) + 2

    return frames


def write_xyz_frames(frames: Iterable[MoleculeGeometry], path: Path) -> None:
    frame_list = list(frames)
    if not frame_list:
        raise ValueError("at least one XYZ frame is required")
    Path(path).write_text(
        "".join(geometry_to_xyz_string(frame) for frame in frame_list),
        encoding="utf-8",
    )


def geometry_to_xyz_string(geometry: MoleculeGeometry) -> str:
    lines = [str(len(geometry.atoms)), geometry.comment]
    for atom in geometry.atoms:
        lines.append(
            f"{atom.symbol} {_format_coordinate(atom.x)} "
            f"{_format_coordinate(atom.y)} {_format_coordinate(atom.z)}"
        )
    return "\n".join(lines) + "\n"


def _parse_xyz_frame(
    xyz_path: Path, lines: list[str], line_index: int
) -> MoleculeGeometry:
    line_number = line_index + 1
    try:
        atom_count = int(lines[line_index].strip())
    except ValueError as exc:
        raise ValueError(
            f"{xyz_path}:{line_number}: atom count must be an integer"
        ) from exc

    if atom_count < 0:
        _raise_xyz_error(xyz_path, line_number, "atom count cannot be negative")
    if len(lines) <= line_index + 1:
        _raise_xyz_error(xyz_path, line_number + 1, "missing comment line")

    atom_start = line_index + 2
    atom_end = atom_start + atom_count
    atom_lines = lines[atom_start:atom_end]
    if len(atom_lines) != atom_count:
        raise ValueError(
            f"{xyz_path}:{atom_start + 1}: expected {atom_count} atom lines, "
            f"found {len(atom_lines)}"
        )

    atoms = tuple(
        _parse_atom_line(xyz_path, line_number, line)
        for line_number, line in enumerate(atom_lines, start=atom_start + 1)
    )
    return MoleculeGeometry(atoms=atoms, comment=lines[line_index + 1])


def _parse_atom_line(path: Path, line_number: int, line: str) -> Atom:
    parts = line.split()
    if len(parts) != 4:
        _raise_xyz_error(
            path,
            line_number,
            "atom line must contain an element symbol and three coordinates",
        )

    symbol = parts[0]
    if symbol not in SUPPORTED_ELEMENT_SYMBOLS:
        _raise_xyz_error(path, line_number, f"unsupported element symbol {symbol!r}")

    try:
        x, y, z = (float(value) for value in parts[1:])
    except ValueError as exc:
        raise ValueError(
            f"{path}:{line_number}: coordinates must be numeric"
        ) from exc

    return Atom(symbol=symbol, x=x, y=y, z=z)


def _format_coordinate(value: float) -> str:
    return f"{value:.10g}"


def _raise_xyz_error(path: Path, line_number: int, message: str) -> None:
    raise ValueError(f"{path}:{line_number}: {message}")
