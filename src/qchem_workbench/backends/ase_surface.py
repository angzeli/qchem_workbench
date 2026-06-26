"""Optional ASE-based surface and slab builders."""

from __future__ import annotations

from pathlib import Path

from qchem_workbench.backends.ase_adapter import (
    ASEUnavailableError,
    from_ase_atoms,
    to_ase_atoms,
)
from qchem_workbench.core.structure import AtomisticStructure


SUPPORTED_FCC_FACETS = ("100", "110", "111")
STARTING_STRUCTURE_WARNING = (
    "ASE-built starting slab; not relaxed and requires human inspection before use."
)


def build_fcc_surface(
    element: str,
    facet: str,
    size: tuple[int, int, int],
    vacuum: float,
) -> AtomisticStructure:
    if facet not in SUPPORTED_FCC_FACETS:
        raise ValueError(f"unsupported fcc facet {facet!r}")
    _validate_size(size)
    if vacuum < 0:
        raise ValueError("vacuum must be nonnegative")

    build = _load_ase_build()
    builders = {
        "100": build.fcc100,
        "110": build.fcc110,
        "111": build.fcc111,
    }
    atoms = builders[facet](element, size=size, vacuum=vacuum)
    structure = from_ase_atoms(atoms)
    return _with_starting_slab_metadata(
        structure,
        {
            "builder": "ase.build.fcc" + facet,
            "element": element,
            "facet": facet,
            "size": list(size),
            "vacuum_angstrom": float(vacuum),
        },
    )


def repeat_slab_from_bulk(
    structure: AtomisticStructure, repeats: tuple[int, int, int]
) -> AtomisticStructure:
    _validate_size(repeats)
    atoms = to_ase_atoms(structure).repeat(repeats)
    repeated = from_ase_atoms(atoms)
    return _with_starting_slab_metadata(
        repeated,
        {
            "builder": "ase.Atoms.repeat",
            "repeats": list(repeats),
        },
    )


def add_vacuum(
    structure: AtomisticStructure, vacuum: float, axis: int = 2
) -> AtomisticStructure:
    if vacuum < 0:
        raise ValueError("vacuum must be nonnegative")
    if axis not in {0, 1, 2}:
        raise ValueError("axis must be 0, 1, or 2")

    atoms = to_ase_atoms(structure)
    atoms.center(vacuum=vacuum, axis=axis)
    expanded = from_ase_atoms(atoms)
    return _with_starting_slab_metadata(
        expanded,
        {
            "builder": "ase.Atoms.center",
            "vacuum_angstrom": float(vacuum),
            "axis": axis,
        },
    )


def write_structure(structure: AtomisticStructure, path: Path) -> None:
    ase_io = _load_ase_io()
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ase_io.write(str(output_path), to_ase_atoms(structure))


def _load_ase_build():
    try:
        import ase.build
    except ImportError as exc:
        raise ASEUnavailableError(
            "ASE is required for slab building; install the optional dependency "
            "with qchem-workbench[ase]."
        ) from exc
    return ase.build


def _load_ase_io():
    try:
        import ase.io
    except ImportError as exc:
        raise ASEUnavailableError(
            "ASE is required to write this structure; install the optional "
            "dependency with qchem-workbench[ase]."
        ) from exc
    return ase.io


def _validate_size(size: tuple[int, int, int]) -> None:
    if len(size) != 3 or any(value <= 0 for value in size):
        raise ValueError("size must contain three positive integers")


def _with_starting_slab_metadata(
    structure: AtomisticStructure, metadata: dict[str, object]
) -> AtomisticStructure:
    return AtomisticStructure(
        atoms=structure.atoms,
        cell=structure.cell,
        pbc=structure.pbc,
        charge=structure.charge,
        multiplicity=structure.multiplicity,
        metadata={
            **structure.metadata,
            "generated_by": "ase",
            "structure_role": "starting_slab",
            "warning": STARTING_STRUCTURE_WARNING,
            **metadata,
        },
    )
