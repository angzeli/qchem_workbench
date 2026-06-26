"""Quantum ESPRESSO pw.x input specifications and rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


QENamelistSettings = dict[str, dict[str, Any]]
QEKPointMode = Literal["automatic", "gamma"]


@dataclass(frozen=True)
class QEKPoints:
    mode: QEKPointMode = "automatic"
    grid: tuple[int, int, int] | None = (1, 1, 1)
    shift: tuple[int, int, int] = (0, 0, 0)

    def __post_init__(self) -> None:
        if self.mode not in {"automatic", "gamma"}:
            raise ValueError(f"unsupported QE K_POINTS mode {self.mode!r}")
        if self.mode == "gamma":
            object.__setattr__(self, "grid", None)
            object.__setattr__(self, "shift", (0, 0, 0))
            return
        if self.grid is None:
            raise ValueError("automatic QE K_POINTS requires a grid")
        object.__setattr__(self, "grid", _int3(self.grid, "k-point grid"))
        shift = _int3(self.shift, "k-point shift")
        if any(value not in {0, 1} for value in shift):
            raise ValueError("QE k-point shifts must be 0 or 1")
        object.__setattr__(self, "shift", shift)

    def to_lines(self) -> list[str]:
        if self.mode == "gamma":
            return ["K_POINTS gamma"]
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
    additional_settings: QENamelistSettings = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.calculation.strip():
            raise ValueError("QE calculation type cannot be empty")
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

        object.__setattr__(
            self,
            "pseudopotentials",
            _pseudopotentials(self.pseudopotentials),
        )
        object.__setattr__(
            self,
            "additional_settings",
            _additional_settings(self.additional_settings),
        )


def validate_pseudopotentials_for_elements(
    elements: set[str], pseudopotentials: dict[str, str]
) -> None:
    missing = sorted(elements - set(pseudopotentials))
    if missing:
        raise ValueError(
            "QE pseudopotential mapping is missing element(s): "
            + ", ".join(missing)
        )


def _int3(value: tuple[int, int, int], label: str) -> tuple[int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"QE {label} must contain exactly three integers")
    parsed = tuple(int(item) for item in value)
    if any(item <= 0 for item in parsed[:3]) and label == "k-point grid":
        raise ValueError("QE k-point grid values must be positive")
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
