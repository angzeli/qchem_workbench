"""Surface and adsorption-site bookkeeping models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class SurfaceModel:
    structure_id: str
    miller_index: tuple[int, int, int] | None = None
    slab_layers: int | None = None
    vacuum_thickness_angstrom: float | None = None
    surface_area_angstrom2: float | None = None
    fixed_atom_indices: tuple[int, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.structure_id.strip():
            raise ValueError("surface structure_id cannot be empty")
        if self.miller_index is not None and len(self.miller_index) != 3:
            raise ValueError("miller_index must contain three integers")
        if self.slab_layers is not None and self.slab_layers <= 0:
            raise ValueError("slab_layers must be positive")
        if (
            self.vacuum_thickness_angstrom is not None
            and self.vacuum_thickness_angstrom < 0
        ):
            raise ValueError("vacuum_thickness_angstrom must be nonnegative")
        if self.surface_area_angstrom2 is not None and self.surface_area_angstrom2 <= 0:
            raise ValueError("surface_area_angstrom2 must be positive")
        object.__setattr__(
            self,
            "fixed_atom_indices",
            tuple(int(index) for index in self.fixed_atom_indices),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def vacuum_thickness_unit(self) -> str:
        return "angstrom"

    @property
    def surface_area_unit(self) -> str:
        return "angstrom^2"


@dataclass(frozen=True)
class AdsorptionSite:
    site_id: str
    site_type_label: str
    coordinates_angstrom: Vector3
    involved_atom_indices: tuple[int, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.site_id.strip():
            raise ValueError("adsorption site_id cannot be empty")
        if not self.site_type_label.strip():
            raise ValueError("adsorption site_type_label cannot be empty")
        object.__setattr__(
            self,
            "coordinates_angstrom",
            _vector3(self.coordinates_angstrom, "coordinates_angstrom"),
        )
        object.__setattr__(
            self,
            "involved_atom_indices",
            tuple(int(index) for index in self.involved_atom_indices),
        )

    @property
    def coordinate_unit(self) -> str:
        return "angstrom"


@dataclass(frozen=True)
class CoverageSpec:
    adsorbate_count: int
    surface_area_angstrom2: float | None = None
    coverage_label: str | None = None
    monolayer_definition_note: str | None = None

    def __post_init__(self) -> None:
        if self.adsorbate_count <= 0:
            raise ValueError("adsorbate_count must be positive")
        if self.surface_area_angstrom2 is not None and self.surface_area_angstrom2 <= 0:
            raise ValueError("surface_area_angstrom2 must be positive")

    @property
    def surface_area_unit(self) -> str:
        return "angstrom^2"

    @property
    def coverage_unit(self) -> str:
        return "adsorbates/angstrom^2"

    @property
    def coverage_adsorbates_per_angstrom2(self) -> float | None:
        if self.surface_area_angstrom2 is None:
            return None
        return self.adsorbate_count / self.surface_area_angstrom2

    def warnings(self) -> tuple[str, ...]:
        if self.surface_area_angstrom2 is None:
            return ("surface area is missing; numeric coverage was not computed",)
        return ()


def validate_adsorption_sites(sites: tuple[AdsorptionSite, ...]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for site in sites:
        if site.site_id in seen:
            duplicates.add(site.site_id)
        seen.add(site.site_id)
    if duplicates:
        raise ValueError(
            "duplicate adsorption site ID(s): " + ", ".join(sorted(duplicates))
        )


def _vector3(value: Any, label: str) -> Vector3:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must contain three numeric values")
    try:
        return tuple(float(component) for component in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain three numeric values") from exc
