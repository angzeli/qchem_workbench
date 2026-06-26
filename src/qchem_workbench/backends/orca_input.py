"""ORCA input file rendering."""

from __future__ import annotations

from dataclasses import dataclass, field

from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.geometry import MoleculeGeometry, read_xyz
from qchem_workbench.core.species import Species


ORCA_TASK_PRESETS = {
    "single_point": ("SP",),
    "opt": ("Opt",),
    "freq": ("Freq",),
    "opt_freq": ("Opt", "Freq"),
}


@dataclass(frozen=True)
class ORCAInputOptions:
    pal_nprocs: int | None = None
    maxcore_mb: int | None = None
    blocks: dict[str, str] = field(default_factory=dict)
    title: str | None = None


def render_orca_input(
    species: Species, calculation_spec: CalculationSpec, options: ORCAInputOptions
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
    if options.title:
        lines.append(f"# {options.title}")
    lines.append(orca_route_from_spec(calculation_spec))

    if options.pal_nprocs is not None:
        if options.pal_nprocs <= 0:
            raise ValueError("ORCA pal_nprocs must be positive")
        lines.extend(["%pal", f"  nprocs {options.pal_nprocs}", "end"])
    if options.maxcore_mb is not None:
        if options.maxcore_mb <= 0:
            raise ValueError("ORCA maxcore_mb must be positive")
        lines.append(f"%maxcore {options.maxcore_mb}")

    for block_name in sorted(options.blocks):
        lines.extend(_render_block(block_name, options.blocks[block_name]))

    lines.extend(
        [
            f"* xyz {charge} {multiplicity}",
            *_geometry_lines(geometry),
            "*",
        ]
    )
    return "\n".join(lines) + "\n"


def orca_route_from_spec(calculation_spec: CalculationSpec) -> str:
    if not calculation_spec.method.strip():
        raise ValueError("ORCA method cannot be empty")
    if calculation_spec.basis is None or not calculation_spec.basis.strip():
        raise ValueError("ORCA basis cannot be empty")
    if calculation_spec.solvent:
        raise ValueError(
            "ORCA solvent rendering is not implemented; provide explicit ORCA blocks"
        )

    try:
        task_keywords = ORCA_TASK_PRESETS[calculation_spec.task]
    except KeyError as exc:
        raise ValueError(f"unsupported ORCA task {calculation_spec.task!r}") from exc

    route_parts = [
        "!",
        calculation_spec.method.strip(),
        calculation_spec.basis.strip(),
        *task_keywords,
    ]
    return " ".join(route_parts)


def _render_block(name: str, content: str) -> list[str]:
    block_name = name.strip()
    if not block_name:
        raise ValueError("ORCA block name cannot be empty")
    header = block_name if block_name.startswith("%") else f"%{block_name}"
    body = [line.rstrip() for line in content.strip("\n").splitlines()]
    lines = [header, *body]
    if not any(line.strip().lower() == "end" for line in body):
        lines.append("end")
    return lines


def _geometry_lines(geometry: MoleculeGeometry) -> list[str]:
    return [
        f"{atom.symbol} {_format_coordinate(atom.x)} "
        f"{_format_coordinate(atom.y)} {_format_coordinate(atom.z)}"
        for atom in geometry.atoms
    ]


def _format_coordinate(value: float) -> str:
    return f"{value:.10g}"
