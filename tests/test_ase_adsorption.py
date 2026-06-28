from __future__ import annotations

import pytest

from qchem_workbench.backends.ase_adsorption import (
    STARTING_ADSORBATE_PLACEMENT_WARNING,
    load_adsorbate_placement_config,
    place_adsorbate_from_yaml,
)


def test_ase_adsorption_import_does_not_require_ase():
    import qchem_workbench.backends.ase_adsorption as ase_adsorption

    assert callable(ase_adsorption.place_adsorbate)


def test_place_adsorbate_with_ase(tmp_path):
    pytest.importorskip("ase")
    config_path = _write_placement_fixture(tmp_path)
    output_path = tmp_path / "combined.xyz"

    structure = place_adsorbate_from_yaml(config_path, output_path)

    assert output_path.exists()
    assert len(structure.atoms) == 3
    assert structure.metadata["structure_role"] == "starting_slab_adsorbate"
    assert structure.metadata["warning"] == STARTING_ADSORBATE_PLACEMENT_WARNING
    assert structure.atoms[1].symbol == "C"
    assert structure.atoms[1].z == pytest.approx(2.0)


def test_invalid_anchor_atom_is_error(tmp_path):
    pytest.importorskip("ase")
    config_path = _write_placement_fixture(tmp_path, anchor_atom=5)

    with pytest.raises(ValueError, match="anchor_atom 5 is out of range"):
        place_adsorbate_from_yaml(config_path, tmp_path / "combined.xyz")


def test_place_adsorbate_with_explicit_site(tmp_path):
    pytest.importorskip("ase")
    config_path = _write_site_placement_fixture(tmp_path)
    output_path = tmp_path / "combined.xyz"

    structure = place_adsorbate_from_yaml(config_path, output_path)

    assert output_path.exists()
    assert len(structure.atoms) == 3
    assert structure.metadata["site_id"] == "site_top_1"
    assert structure.metadata["site_type_label"] == "top"
    assert structure.atoms[1].x == pytest.approx(1.0)
    assert structure.atoms[1].y == pytest.approx(1.0)
    assert structure.atoms[1].z == pytest.approx(2.5)


def test_invalid_height_is_error(tmp_path):
    config_path = _write_site_placement_fixture(tmp_path, height=0.0)

    with pytest.raises(ValueError, match="height must be positive"):
        load_adsorbate_placement_config(config_path)


def test_invalid_orient_vector_atom_is_error(tmp_path):
    pytest.importorskip("ase")
    config_path = _write_site_placement_fixture(tmp_path, orient_to_atom=9)

    with pytest.raises(ValueError, match="orient_vector.to_atom 9 is out of range"):
        place_adsorbate_from_yaml(config_path, tmp_path / "combined.xyz")


def test_load_placement_config_resolves_relative_paths(tmp_path):
    config_path = _write_placement_fixture(tmp_path)

    config = load_adsorbate_placement_config(config_path)

    assert config.slab_structure_path == tmp_path / "slab.xyz"
    assert config.adsorbate_structure_path == tmp_path / "co.xyz"
    assert config.target_position == (0.0, 0.0, 0.0)


def test_load_placement_config_reads_site_metadata(tmp_path):
    config_path = _write_site_placement_fixture(tmp_path)

    config = load_adsorbate_placement_config(config_path)

    assert config.site_id == "site_top_1"
    assert config.site_type_label == "top"
    assert config.target_position == (1.0, 1.0, 0.0)
    assert config.surface_normal == (0.0, 0.0, 1.0)
    assert config.orient_vector == (0, 1)


def _write_placement_fixture(tmp_path, anchor_atom: int = 0):
    (tmp_path / "slab.xyz").write_text(
        "1\nsynthetic fixture slab atom\nCu 0 0 0\n",
        encoding="utf-8",
    )
    (tmp_path / "co.xyz").write_text(
        "2\nsynthetic fixture adsorbate\nC 0 0 0\nO 0 0 1.1\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "placement.yaml"
    config_path.write_text(
        "schema_version: 1\n"
        "placement:\n"
        "  slab_structure_path: slab.xyz\n"
        "  adsorbate_structure_path: co.xyz\n"
        f"  anchor_atom: {anchor_atom}\n"
        "  target_position: [0.0, 0.0, 0.0]\n"
        "  height: 2.0\n"
        "  notes: synthetic fixture starting geometry\n",
        encoding="utf-8",
    )
    return config_path


def _write_site_placement_fixture(
    tmp_path,
    *,
    height: float = 2.5,
    orient_to_atom: int = 1,
):
    (tmp_path / "slab.xyz").write_text(
        "1\nsynthetic fixture slab atom\nCu 0 0 0\n",
        encoding="utf-8",
    )
    (tmp_path / "co.xyz").write_text(
        "2\nsynthetic fixture adsorbate\nC 0 0 0\nO 0 0 1.1\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "placement_site.yaml"
    config_path.write_text(
        "schema_version: 1\n"
        "placement:\n"
        "  slab_structure_path: slab.xyz\n"
        "  adsorbate_structure_path: co.xyz\n"
        "  anchor_atom: 0\n"
        f"  height: {height}\n"
        "  site:\n"
        "    site_id: site_top_1\n"
        "    site_type_label: top\n"
        "    coordinates: [1.0, 1.0, 0.0]\n"
        "    surface_normal: [0.0, 0.0, 1.0]\n"
        "  orient_vector:\n"
        "    from_atom: 0\n"
        f"    to_atom: {orient_to_atom}\n"
        "  notes: synthetic fixture starting geometry with explicit site\n",
        encoding="utf-8",
    )
    return config_path
