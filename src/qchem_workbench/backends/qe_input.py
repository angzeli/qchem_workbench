"""Quantum ESPRESSO pw.x input specifications and rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from qchem_workbench.core.structure import AtomisticStructure


QENamelistSettings = dict[str, dict[str, Any]]
QEKPointMode = Literal["automatic", "gamma", "crystal"]
QE_ATOMIC_POSITION_UNITS = {"angstrom", "crystal"}
QE_CALCULATION_TYPES = {"scf", "relax", "vc-relax"}
QE_CELL_CALCULATIONS = {"vc-relax"}
QE_IONS_CALCULATIONS = {"relax", "vc-relax"}


@dataclass(frozen=True)
class QEKPoints:
    mode: QEKPointMode = "automatic"
    grid: tuple[int, int, int] | None = (1, 1, 1)
    shift: tuple[int, int, int] = (0, 0, 0)
    points: tuple[tuple[float, float, float, float], ...] | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"automatic", "gamma", "crystal"}:
            raise ValueError(f"unsupported QE K_POINTS mode {self.mode!r}")
        if self.mode == "gamma":
            object.__setattr__(self, "grid", None)
            object.__setattr__(self, "shift", (0, 0, 0))
            object.__setattr__(self, "points", None)
            return
        if self.mode == "crystal":
            if not self.points:
                raise ValueError("crystal QE K_POINTS requires explicit points")
            object.__setattr__(self, "grid", None)
            object.__setattr__(self, "shift", (0, 0, 0))
            object.__setattr__(self, "points", _kpoint_rows(self.points))
            return
        if self.grid is None:
            raise ValueError("automatic QE K_POINTS requires a grid")
        object.__setattr__(self, "grid", _int3(self.grid, "k-point grid"))
        shift = _int3(self.shift, "k-point shift")
        if any(value not in {0, 1} for value in shift):
            raise ValueError("QE k-point shifts must be 0 or 1")
        object.__setattr__(self, "shift", shift)
        object.__setattr__(self, "points", None)

    def to_lines(self) -> list[str]:
        if self.mode == "gamma":
            return ["K_POINTS gamma"]
        if self.mode == "crystal":
            assert self.points is not None
            return [
                "K_POINTS crystal",
                str(len(self.points)),
                *[
                    " ".join(_format_number(value) for value in point)
                    for point in self.points
                ],
            ]
        assert self.grid is not None
        values = (*self.grid, *self.shift)
        return ["K_POINTS automatic", " ".join(str(value) for value in values)]


@dataclass(frozen=True)
class QEInputSpec:
    calculation: str
    prefix: str
    pseudo_dir: str
    outdir: str
    ecutwfc: float
    ecutrho: float | None = None
    occupations: str | None = None
    smearing: str | None = None
    degauss: float | None = None
    k_points: QEKPoints = field(default_factory=QEKPoints)
    pseudopotentials: dict[str, str] = field(default_factory=dict)
    atomic_masses: dict[str, float] = field(default_factory=dict)
    atomic_position_units: Literal["angstrom", "crystal"] = "angstrom"
    additional_settings: QENamelistSettings = field(default_factory=dict)

    def __post_init__(self) -> None:
        calculation = self.calculation.strip()
        if not calculation:
            raise ValueError("QE calculation type cannot be empty")
        if calculation not in QE_CALCULATION_TYPES:
            allowed = ", ".join(sorted(QE_CALCULATION_TYPES))
            raise ValueError(
                f"unsupported QE calculation type {calculation!r}; "
                f"expected one of: {allowed}"
            )
        if not self.prefix.strip():
            raise ValueError("QE prefix cannot be empty")
        if not self.pseudo_dir.strip():
            raise ValueError("QE pseudo_dir cannot be empty")
        if not self.outdir.strip():
            raise ValueError("QE outdir cannot be empty")
        if self.ecutwfc <= 0:
            raise ValueError("QE ecutwfc must be positive")
        if self.ecutrho is not None and self.ecutrho <= 0:
            raise ValueError("QE ecutrho must be positive")
        if self.degauss is not None and self.degauss < 0:
            raise ValueError("QE degauss must be nonnegative")
        if not self.pseudopotentials:
            raise ValueError("QE pseudopotential mapping is required")
        if self.atomic_position_units not in QE_ATOMIC_POSITION_UNITS:
            raise ValueError(
                "QE atomic_position_units must be 'angstrom' or 'crystal'"
            )

        object.__setattr__(self, "calculation", calculation)
        object.__setattr__(
            self,
            "pseudopotentials",
            _pseudopotentials(self.pseudopotentials),
        )
        object.__setattr__(self, "atomic_masses", _atomic_masses(self.atomic_masses))
        object.__setattr__(
            self,
            "additional_settings",
            _additional_settings(self.additional_settings),
        )


def render_qe_pw_input(structure: AtomisticStructure, spec: QEInputSpec) -> str:
    elements = {atom.symbol for atom in structure.atoms}
    validate_pseudopotentials_for_elements(elements, spec.pseudopotentials)
    _validate_atomic_masses_for_elements(elements, spec.atomic_masses)
    if structure.cell is None:
        raise ValueError("QE pw.x input rendering requires explicit cell vectors")

    namelists = _qe_namelists(structure, spec)
    lines: list[str] = []
    for name in ("control", "system", "electrons", "ions", "cell"):
        if name in namelists:
            settings = namelists[name]
            lines.extend(_render_namelist(name, settings))
            lines.append("")

    lines.extend(_atomic_species_lines(elements, spec))
    lines.append("")
    lines.extend(_atomic_positions_lines(structure, spec))
    lines.append("")
    lines.extend(_cell_parameter_lines(structure))
    lines.append("")
    lines.extend(spec.k_points.to_lines())
    return "\n".join(lines) + "\n"


def validate_pseudopotentials_for_elements(
    elements: set[str], pseudopotentials: dict[str, str]
) -> None:
    missing = sorted(elements - set(pseudopotentials))
    if missing:
        raise ValueError(
            "QE pseudopotential mapping is missing element(s): "
            + ", ".join(missing)
        )


def _validate_atomic_masses_for_elements(
    elements: set[str], atomic_masses: dict[str, float]
) -> None:
    missing = sorted(elements - set(atomic_masses))
    if missing:
        raise ValueError(
            "QE atomic mass mapping is missing element(s): " + ", ".join(missing)
        )


def _qe_namelists(
    structure: AtomisticStructure, spec: QEInputSpec
) -> dict[str, dict[str, Any]]:
    elements = sorted({atom.symbol for atom in structure.atoms})
    namelists: dict[str, dict[str, Any]] = {
        "control": {
            "calculation": spec.calculation,
            "prefix": spec.prefix,
            "pseudo_dir": spec.pseudo_dir,
            "outdir": spec.outdir,
        },
        "system": {
            "ibrav": 0,
            "nat": len(structure.atoms),
            "ntyp": len(elements),
            "ecutwfc": spec.ecutwfc,
        },
        "electrons": {},
    }
    if spec.ecutrho is not None:
        namelists["system"]["ecutrho"] = spec.ecutrho
    if spec.occupations is not None:
        namelists["system"]["occupations"] = spec.occupations
    if spec.smearing is not None:
        namelists["system"]["smearing"] = spec.smearing
    if spec.degauss is not None:
        namelists["system"]["degauss"] = spec.degauss
    if spec.calculation in QE_IONS_CALCULATIONS:
        namelists["ions"] = {}
    if spec.calculation in QE_CELL_CALCULATIONS:
        namelists["cell"] = {}

    for name, settings in spec.additional_settings.items():
        namelists.setdefault(name, {}).update(settings)
    return namelists


def _render_namelist(name: str, settings: dict[str, Any]) -> list[str]:
    lines = [f"&{name.upper()}"]
    for key, value in settings.items():
        lines.append(f"  {key} = {_format_qe_value(value)},")
    lines.append("/")
    return lines


def _atomic_species_lines(elements: set[str], spec: QEInputSpec) -> list[str]:
    lines = ["ATOMIC_SPECIES"]
    for element in sorted(elements):
        lines.append(
            f"{element} {_format_number(spec.atomic_masses[element])} "
            f"{spec.pseudopotentials[element]}"
        )
    return lines


def _atomic_positions_lines(
    structure: AtomisticStructure,
    spec: QEInputSpec,
) -> list[str]:
    lines = [f"ATOMIC_POSITIONS {spec.atomic_position_units}"]
    if spec.atomic_position_units == "crystal":
        positions = structure.atoms_as_fractional()
    else:
        positions = tuple((atom.x, atom.y, atom.z) for atom in structure.atoms)
    for index, (atom, position) in enumerate(zip(structure.atoms, positions)):
        constraints = _qe_constraint_flags(index, structure.fixed_atom_indices)
        lines.append(
            f"{atom.symbol} {_format_number(position[0])} "
            f"{_format_number(position[1])} {_format_number(position[2])}"
            f"{constraints}"
        )
    return lines


def _cell_parameter_lines(structure: AtomisticStructure) -> list[str]:
    if structure.cell is None:
        raise ValueError("QE CELL_PARAMETERS requires explicit cell vectors")
    lines = ["CELL_PARAMETERS angstrom"]
    for vector in structure.cell:
        lines.append(" ".join(_format_number(component) for component in vector))
    return lines


def _format_qe_value(value: Any) -> str:
    if isinstance(value, bool):
        return ".true." if value else ".false."
    if isinstance(value, str):
        return f"'{value}'"
    if isinstance(value, (int, float)):
        return _format_number(float(value))
    raise ValueError(f"unsupported QE namelist value {value!r}")


def _format_number(value: float) -> str:
    return f"{value:.12g}"


def _int3(value: tuple[int, int, int], label: str) -> tuple[int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"QE {label} must contain exactly three integers")
    parsed = tuple(int(item) for item in value)
    if any(item <= 0 for item in parsed[:3]) and label == "k-point grid":
        raise ValueError("QE k-point grid values must be positive")
    return parsed


def _kpoint_rows(
    value: tuple[tuple[float, float, float, float], ...],
) -> tuple[tuple[float, float, float, float], ...]:
    rows: list[tuple[float, float, float, float]] = []
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) != 4:
            raise ValueError("crystal QE K_POINTS rows must contain kx, ky, kz, weight")
        rows.append(tuple(float(component) for component in row))
    return tuple(rows)


def _qe_constraint_flags(index: int, fixed_atom_indices: tuple[int, ...]) -> str:
    if not fixed_atom_indices:
        return ""
    if index in fixed_atom_indices:
        return " 0 0 0"
    return " 1 1 1"


def _atomic_masses(value: dict[str, float]) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for element, mass in value.items():
        if not isinstance(element, str) or not element.strip():
            raise ValueError("QE atomic mass element keys must be nonempty strings")
        if not isinstance(mass, (int, float)) or mass <= 0:
            raise ValueError(
                f"QE atomic mass for {element!r} must be a positive number"
            )
        parsed[element.strip()] = float(mass)
    return parsed


def _pseudopotentials(value: dict[str, str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for element, filename in value.items():
        if not isinstance(element, str) or not element.strip():
            raise ValueError("QE pseudopotential element keys must be nonempty strings")
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError(
                f"QE pseudopotential filename for {element!r} must be explicit"
            )
        parsed[element.strip()] = filename.strip()
    return parsed


def _additional_settings(value: QENamelistSettings) -> QENamelistSettings:
    parsed: QENamelistSettings = {}
    for namelist, settings in value.items():
        if not isinstance(namelist, str) or not namelist.strip():
            raise ValueError("QE additional namelist names must be nonempty strings")
        if not isinstance(settings, dict):
            raise ValueError(
                f"QE additional settings for namelist {namelist!r} must be a mapping"
            )
        parsed[namelist.strip().lower()] = dict(settings)
    return parsed
