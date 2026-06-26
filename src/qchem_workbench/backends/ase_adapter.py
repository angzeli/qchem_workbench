"""Optional ASE adapter for atomistic structures."""

from __future__ import annotations

from typing import Any

import numpy as np

from qchem_workbench.core.geometry import Atom
from qchem_workbench.core.structure import AtomisticStructure, Cell


class ASEUnavailableError(RuntimeError):
    """Raised when ASE helpers are used without ASE installed."""


def to_ase_atoms(structure: AtomisticStructure):
    Atoms = _load_ase_atoms_class()
    atoms = Atoms(
        symbols=[atom.symbol for atom in structure.atoms],
        positions=[(atom.x, atom.y, atom.z) for atom in structure.atoms],
        cell=structure.cell,
        pbc=structure.pbc,
    )
    atoms.info["qchem_workbench_metadata"] = dict(structure.metadata)
    atoms.info["qchem_workbench_charge"] = structure.charge
    atoms.info["qchem_workbench_multiplicity"] = structure.multiplicity
    return atoms


def from_ase_atoms(atoms) -> AtomisticStructure:
    symbols = atoms.get_chemical_symbols()
    positions = atoms.get_positions()
    pbc = tuple(bool(flag) for flag in atoms.get_pbc())
    cell_array = np.asarray(atoms.get_cell().array, dtype=float)
    cell = _cell_or_none(cell_array, pbc)

    metadata: dict[str, Any] = dict(atoms.info.get("qchem_workbench_metadata", {}))
    other_info = {
        key: value
        for key, value in atoms.info.items()
        if key
        not in {
            "qchem_workbench_metadata",
            "qchem_workbench_charge",
            "qchem_workbench_multiplicity",
        }
    }
    if other_info:
        metadata["ase_info"] = other_info

    return AtomisticStructure(
        atoms=tuple(
            Atom(
                symbol=symbol,
                x=float(position[0]),
                y=float(position[1]),
                z=float(position[2]),
            )
            for symbol, position in zip(symbols, positions)
        ),
        cell=cell,
        pbc=pbc,
        charge=atoms.info.get("qchem_workbench_charge"),
        multiplicity=atoms.info.get("qchem_workbench_multiplicity"),
        metadata=metadata,
    )


def _load_ase_atoms_class():
    try:
        from ase import Atoms
    except ImportError as exc:
        raise ASEUnavailableError(
            "ASE is required for ASE structure conversion; install the optional "
            "dependency with qchem-workbench[ase]."
        ) from exc
    return Atoms


def _cell_or_none(cell_array: np.ndarray, pbc: tuple[bool, bool, bool]) -> Cell | None:
    if not any(pbc) and not np.any(np.abs(cell_array) > 1e-12):
        return None
    return tuple(tuple(float(component) for component in row) for row in cell_array)
