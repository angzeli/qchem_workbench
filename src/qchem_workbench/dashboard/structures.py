"""Structure summary helpers for the dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from qchem_workbench.core.geometry import read_xyz_frames
from qchem_workbench.core.structure import AtomisticStructure
from qchem_workbench.dashboard.data import DashboardData


def structure_summary_rows(
    structures: Iterable[AtomisticStructure],
    *,
    source_path: Path | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for index, structure in enumerate(structures, start=1):
        rows.append(
            {
                "frame": index,
                "source_path": str(source_path) if source_path else "",
                "atom_count": len(structure.atoms),
                "formula": formula_from_atoms(structure.atoms),
                "periodic": structure.is_periodic,
                "pbc": " ".join(str(flag) for flag in structure.pbc),
                "cell_vectors_angstrom": json.dumps(structure.cell) if structure.cell else "",
                "cell_volume_angstrom3": structure.cell_volume_angstrom3,
                "surface_normal": (
                    json.dumps(structure.surface_normal)
                    if structure.surface_normal is not None
                    else ""
                ),
                "fixed_atom_indices": ";".join(
                    str(index) for index in structure.fixed_atom_indices
                ),
            }
        )
    return rows


def structure_summary_from_xyz(path: Path) -> list[dict[str, Any]]:
    structure_path = Path(path)
    frames = [
        AtomisticStructure.from_molecule_geometry(frame)
        for frame in read_xyz_frames(structure_path)
    ]
    return structure_summary_rows(frames, source_path=structure_path)


def dashboard_structure_rows(data: DashboardData) -> list[dict[str, Any]]:
    species_section = data.section("species")
    if species_section is None:
        return []
    rows: list[dict[str, Any]] = []
    for species in species_section.rows:
        geometry_path = species.get("geometry_path")
        if not geometry_path:
            rows.append(
                {
                    "species": species.get("name"),
                    "source_path": "",
                    "status": "missing geometry path",
                }
            )
            continue
        path = Path(str(geometry_path))
        try:
            structure_rows = structure_summary_from_xyz(path)
        except (OSError, ValueError) as exc:
            rows.append(
                {
                    "species": species.get("name"),
                    "source_path": str(path),
                    "status": f"could not load structure: {exc}",
                }
            )
            continue
        for row in structure_rows:
            rows.append({"species": species.get("name"), "status": "loaded", **row})
    return rows


def formula_from_atoms(atoms) -> str:
    counts: dict[str, int] = {}
    for atom in atoms:
        counts[atom.symbol] = counts.get(atom.symbol, 0) + 1
    if "C" in counts:
        symbols = ["C"]
        if "H" in counts:
            symbols.append("H")
        symbols.extend(symbol for symbol in sorted(counts) if symbol not in {"C", "H"})
    else:
        symbols = sorted(counts)
    return "".join(
        symbol if counts[symbol] == 1 else f"{symbol}{counts[symbol]}"
        for symbol in symbols
    )
