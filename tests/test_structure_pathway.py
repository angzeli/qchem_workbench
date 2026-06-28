from __future__ import annotations

import pytest

from qchem_workbench.projects.structure_pathway import (
    export_structure_pathway_layout,
    load_structure_pathway,
)


def test_valid_structure_pathway(tmp_path):
    pathway_path = _write_pathway(tmp_path)

    pathway = load_structure_pathway(pathway_path)

    assert pathway.pathway_id == "synthetic_diffusion_path"
    assert [image.index for image in pathway.images] == [0, 1, 2]
    assert pathway.images[0].label == "initial"
    assert pathway.images[2].label == "final"


def test_missing_image_is_error(tmp_path):
    pathway_path = _write_pathway(tmp_path, create_images=False)

    with pytest.raises(ValueError, match="missing"):
        load_structure_pathway(pathway_path)


def test_duplicate_image_index_is_error(tmp_path):
    pathway_path = _write_pathway(tmp_path, duplicate=True)

    with pytest.raises(ValueError, match="duplicate image index"):
        load_structure_pathway(pathway_path)


def test_unordered_images_are_sorted(tmp_path):
    pathway_path = _write_pathway(tmp_path, unordered=True)

    pathway = load_structure_pathway(pathway_path)

    assert [image.index for image in pathway.images] == [0, 1, 2]


def test_export_structure_pathway_layout(tmp_path):
    pathway = load_structure_pathway(_write_pathway(tmp_path))
    output_dir = tmp_path / "exported"

    written = export_structure_pathway_layout(pathway, output_dir)

    assert [path.name for path in written] == [
        "00_initial.xyz",
        "01.xyz",
        "02_final.xyz",
    ]
    assert written[0].read_text(encoding="utf-8").startswith("1\n")


def _write_pathway(
    tmp_path,
    *,
    create_images: bool = True,
    duplicate: bool = False,
    unordered: bool = False,
):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    if create_images:
        for index in range(3):
            (images_dir / f"{index:02d}.xyz").write_text(
                "1\nsynthetic structure pathway image\nH 0 0 0\n",
                encoding="utf-8",
            )
    entries = [
        "    - index: 0\n      structure_path: images/00.xyz\n      label: initial\n",
        "    - index: 1\n      structure_path: images/01.xyz\n",
        "    - index: 2\n      structure_path: images/02.xyz\n      label: final\n",
    ]
    if duplicate:
        entries[1] = "    - index: 0\n      structure_path: images/01.xyz\n"
    if unordered:
        entries = [entries[2], entries[0], entries[1]]
    pathway_path = tmp_path / "structure_pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "structure_pathway:\n"
        "  id: synthetic_diffusion_path\n"
        "  images:\n"
        + "".join(entries),
        encoding="utf-8",
    )
    return pathway_path
