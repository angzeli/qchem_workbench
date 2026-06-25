"""Gaussian input file rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.geometry import MoleculeGeometry, read_xyz
from qchem_workbench.core.species import Species


@dataclass(frozen=True)
class GaussianInputOptions:
    nprocshared: int | None = None
    mem: str | None = None
    checkpoint: str | Path | None = None
    route: str = ""
    title: str = "qchem-workbench Gaussian job"


def render_gaussian_input(
    species: Species, calculation_spec: CalculationSpec, options: GaussianInputOptions
) -> str:
    geometry = read_xyz(species.geometry_path)
    charge = (
        species.charge if calculation_spec.charge is None else calculation_spec.charge
    )
    multiplicity = (
        species.multiplicity
        if calculation_spec.multiplicity is None
        else calculation_spec.multiplicity
    )

    lines: list[str] = []
    if options.nprocshared is not None:
        lines.append(f"%nprocshared={options.nprocshared}")
    if options.mem is not None:
        lines.append(f"%mem={options.mem}")
    if options.checkpoint is not None:
        lines.append(f"%chk={options.checkpoint}")

    lines.extend(
        [
            _normalize_route(options.route),
            "",
            options.title,
            "",
            f"{charge} {multiplicity}",
            *_geometry_lines(geometry),
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _normalize_route(route: str) -> str:
    route = route.strip()
    if not route:
        raise ValueError("Gaussian route cannot be empty")
    if route.startswith("#"):
        return route
    return f"# {route}"


def _geometry_lines(geometry: MoleculeGeometry) -> list[str]:
    return [
        f"{atom.symbol} {_format_coordinate(atom.x)} "
        f"{_format_coordinate(atom.y)} {_format_coordinate(atom.z)}"
        for atom in geometry.atoms
    ]


def _format_coordinate(value: float) -> str:
    return f"{value:.10g}"
