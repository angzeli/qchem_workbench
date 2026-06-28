"""Optional ASE-based adsorbate placement helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.backends.ase_adapter import ASEUnavailableError, from_ase_atoms
from qchem_workbench.backends.ase_surface import write_structure
from qchem_workbench.core.structure import AtomisticStructure


PLACEMENT_SCHEMA_VERSION = 1
STARTING_ADSORBATE_PLACEMENT_WARNING = (
    "ASE-placed slab+adsorbate starting geometry; not relaxed and requires human "
    "inspection before use."
)


@dataclass(frozen=True)
class AdsorbatePlacementConfig:
    slab_structure_path: Path
    adsorbate_structure_path: Path
    anchor_atom: int
    target_position: tuple[float, float, float]
    height: float
    site_id: str | None = None
    site_type_label: str | None = None
    surface_normal: tuple[float, float, float] | None = None
    orient_vector: tuple[int, int] | None = None
    rotation_degrees_z: float | None = None
    notes: str | None = None


def load_adsorbate_placement_config(path: Path) -> AdsorbatePlacementConfig:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{config_path}: placement config must be a mapping")

    schema_version = data.get("schema_version")
    if schema_version != PLACEMENT_SCHEMA_VERSION:
        raise ValueError(
            f"{config_path}: unsupported schema_version {schema_version!r}; "
            f"expected {PLACEMENT_SCHEMA_VERSION}"
        )

    placement = data.get("placement", data)
    if not isinstance(placement, dict):
        raise ValueError(f"{config_path}: placement must be a mapping")

    slab_path = _required_path(config_path, placement, "slab_structure_path")
    adsorbate_path = _required_path(config_path, placement, "adsorbate_structure_path")
    anchor_atom = _required_int(config_path, placement, "anchor_atom")
    if anchor_atom < 0:
        raise ValueError(f"{config_path}: anchor_atom must be zero or positive")

    site = placement.get("site")
    if site is not None and not isinstance(site, dict):
        raise ValueError(f"{config_path}: site must be a mapping")
    target_position = (
        _site_coordinates(config_path, site)
        if isinstance(site, dict)
        else _required_vector3(config_path, placement, "target_position")
    )
    site_id = _optional_site_text(site, "site_id") if isinstance(site, dict) else None
    site_type = (
        _optional_site_text(site, "site_type_label")
        if isinstance(site, dict)
        else None
    )
    surface_normal = (
        _optional_vector3(config_path, site, "surface_normal")
        if isinstance(site, dict)
        else _optional_vector3(config_path, placement, "surface_normal")
    )
    orient_vector = _optional_orient_vector(config_path, placement)
    height = _required_float(config_path, placement, "height")
    if height <= 0:
        raise ValueError(f"{config_path}: height must be positive")
    rotation = placement.get("rotation_degrees_z")
    return AdsorbatePlacementConfig(
        slab_structure_path=slab_path,
        adsorbate_structure_path=adsorbate_path,
        anchor_atom=anchor_atom,
        target_position=target_position,
        height=height,
        site_id=site_id,
        site_type_label=site_type,
        surface_normal=surface_normal,
        orient_vector=orient_vector,
        rotation_degrees_z=None if rotation is None else float(rotation),
        notes=placement.get("notes"),
    )


def place_adsorbate(config: AdsorbatePlacementConfig) -> AtomisticStructure:
    ase_io = _load_ase_io()
    slab = ase_io.read(str(config.slab_structure_path))
    adsorbate = ase_io.read(str(config.adsorbate_structure_path))

    if config.anchor_atom >= len(adsorbate):
        raise ValueError(
            f"anchor_atom {config.anchor_atom} is out of range for adsorbate "
            f"with {len(adsorbate)} atoms"
        )

    anchor_position = adsorbate.positions[config.anchor_atom].copy()
    if config.rotation_degrees_z is not None:
        adsorbate.rotate(
            config.rotation_degrees_z,
            "z",
            center=anchor_position,
            rotate_cell=False,
        )
    if config.orient_vector is not None:
        if config.surface_normal is None:
            raise ValueError("orient_vector requires a site or placement surface_normal")
        from_atom, to_atom = config.orient_vector
        _validate_adsorbate_atom_index(from_atom, len(adsorbate), "orient_vector.from_atom")
        _validate_adsorbate_atom_index(to_atom, len(adsorbate), "orient_vector.to_atom")
        vector = adsorbate.positions[to_atom] - adsorbate.positions[from_atom]
        if float(vector.dot(vector)) == 0.0:
            raise ValueError("orient_vector atoms must not define a zero-length vector")
        adsorbate.rotate(
            vector,
            config.surface_normal,
            center=anchor_position,
            rotate_cell=False,
        )

    desired_anchor = (
        config.target_position[0],
        config.target_position[1],
        config.target_position[2] + config.height,
    )
    displacement = [desired_anchor[index] - anchor_position[index] for index in range(3)]
    adsorbate.translate(displacement)

    combined = slab + adsorbate
    combined.info["qchem_workbench_metadata"] = {
        "structure_role": "starting_slab_adsorbate",
        "warning": STARTING_ADSORBATE_PLACEMENT_WARNING,
        "slab_structure_path": str(config.slab_structure_path),
        "adsorbate_structure_path": str(config.adsorbate_structure_path),
        "anchor_atom": config.anchor_atom,
        "target_position": list(config.target_position),
        "height_angstrom": config.height,
        "site_id": config.site_id,
        "site_type_label": config.site_type_label,
        "surface_normal": (
            list(config.surface_normal) if config.surface_normal is not None else None
        ),
        "orient_vector": list(config.orient_vector) if config.orient_vector else None,
        "rotation_degrees_z": config.rotation_degrees_z,
        "notes": config.notes,
    }
    return from_ase_atoms(combined)


def place_adsorbate_from_yaml(config_path: Path, output_path: Path) -> AtomisticStructure:
    structure = place_adsorbate(load_adsorbate_placement_config(config_path))
    write_structure(structure, output_path)
    return structure


def _load_ase_io():
    try:
        import ase.io
    except ImportError as exc:
        raise ASEUnavailableError(
            "ASE is required for adsorbate placement; install the optional "
            "dependency with qchem-workbench[ase]."
        ) from exc
    return ase.io


def _required_path(config_path: Path, data: dict[str, Any], key: str) -> Path:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{config_path}: {key} must be a non-empty path")
    path = Path(value)
    return path if path.is_absolute() else config_path.parent / path


def _required_int(config_path: Path, data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{config_path}: {key} must be an integer")
    return value


def _required_float(config_path: Path, data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{config_path}: {key} must be numeric")
    return float(value)


def _required_vector3(
    config_path: Path, data: dict[str, Any], key: str
) -> tuple[float, float, float]:
    value = data.get(key)
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{config_path}: {key} must contain three numeric values")
    try:
        return tuple(float(component) for component in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{config_path}: {key} must contain three numeric values"
        ) from exc


def _optional_vector3(
    config_path: Path,
    data: dict[str, Any],
    key: str,
) -> tuple[float, float, float] | None:
    if key not in data or data.get(key) is None:
        return None
    return _required_vector3(config_path, data, key)


def _site_coordinates(
    config_path: Path,
    site: dict[str, Any],
) -> tuple[float, float, float]:
    if "coordinates" in site:
        return _required_vector3(config_path, site, "coordinates")
    return _required_vector3(config_path, site, "coordinates_angstrom")


def _optional_site_text(site: dict[str, Any], key: str) -> str | None:
    value = site.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"site {key} must be non-empty text")
    return value.strip()


def _optional_orient_vector(
    config_path: Path,
    placement: dict[str, Any],
) -> tuple[int, int] | None:
    value = placement.get("orient_vector")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{config_path}: orient_vector must be a mapping")
    from_atom = _required_int(config_path, value, "from_atom")
    to_atom = _required_int(config_path, value, "to_atom")
    return from_atom, to_atom


def _validate_adsorbate_atom_index(index: int, atom_count: int, label: str) -> None:
    if index < 0 or index >= atom_count:
        raise ValueError(
            f"{label} {index} is out of range for adsorbate with {atom_count} atoms"
        )
