"""Structure-set schema for NEB-like or path-based workflows."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.core.geometry import read_xyz_frames


STRUCTURE_PATHWAY_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class StructurePathwayImage:
    index: int
    structure_path: Path
    label: str | None = None


@dataclass(frozen=True)
class StructurePathway:
    pathway_id: str
    images: tuple[StructurePathwayImage, ...]
    source_path: Path | None = None


def load_structure_pathway(path: Path) -> StructurePathway:
    pathway_path = Path(path)
    data = yaml.safe_load(pathway_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{pathway_path}: structure pathway must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != STRUCTURE_PATHWAY_SCHEMA_VERSION:
        raise ValueError(
            f"{pathway_path}: unsupported schema_version {schema_version!r}; "
            f"expected {STRUCTURE_PATHWAY_SCHEMA_VERSION}"
        )
    raw_pathway = data.get("structure_pathway")
    if not isinstance(raw_pathway, dict):
        raise ValueError(f"{pathway_path}: structure_pathway must be a mapping")
    pathway_id = _required_str(pathway_path, raw_pathway, "id")
    raw_images = raw_pathway.get("images")
    if not isinstance(raw_images, list) or not raw_images:
        raise ValueError(f"{pathway_path}: images must be a non-empty list")

    images: list[StructurePathwayImage] = []
    seen_indices: set[int] = set()
    duplicate_indices: set[int] = set()
    for entry in raw_images:
        image = _image_from_mapping(pathway_path, entry)
        if image.index in seen_indices:
            duplicate_indices.add(image.index)
        seen_indices.add(image.index)
        _validate_structure_file(image.structure_path)
        images.append(image)
    if duplicate_indices:
        raise ValueError(
            f"{pathway_path}: duplicate image index/indices "
            + ", ".join(str(index) for index in sorted(duplicate_indices))
        )
    return StructurePathway(
        pathway_id=pathway_id,
        images=tuple(sorted(images, key=lambda image: image.index)),
        source_path=pathway_path,
    )


def export_structure_pathway_layout(
    pathway: StructurePathway,
    output_dir: Path,
) -> list[Path]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for image in pathway.images:
        label = f"_{_safe_label(image.label)}" if image.label else ""
        target = target_dir / f"{image.index:02d}{label}{image.structure_path.suffix}"
        shutil.copyfile(image.structure_path, target)
        written.append(target)
    return written


def _image_from_mapping(
    pathway_path: Path,
    data: Any,
) -> StructurePathwayImage:
    if not isinstance(data, dict):
        raise ValueError(f"{pathway_path}: image entries must be mappings")
    index = data.get("index")
    if not isinstance(index, int) or index < 0:
        raise ValueError(f"{pathway_path}: image index must be a nonnegative integer")
    raw_structure_path = _required_str(pathway_path, data, "structure_path")
    structure_path = Path(raw_structure_path)
    if not structure_path.is_absolute():
        structure_path = pathway_path.parent / structure_path
    label = data.get("label")
    if label is not None and (not isinstance(label, str) or not label.strip()):
        raise ValueError(f"{pathway_path}: image label must be non-empty text")
    return StructurePathwayImage(
        index=index,
        structure_path=structure_path,
        label=label.strip() if isinstance(label, str) else None,
    )


def _validate_structure_file(path: Path) -> None:
    if not path.exists():
        raise ValueError(f"structure pathway image is missing: {path}")
    try:
        read_xyz_frames(path)
    except ValueError as exc:
        raise ValueError(f"{path}: invalid XYZ structure for pathway image") from exc


def _required_str(path: Path, data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {key} must be a non-empty string")
    return value.strip()


def _safe_label(value: str | None) -> str:
    if value is None:
        return ""
    return "".join(character if character.isalnum() else "_" for character in value)
