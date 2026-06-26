from __future__ import annotations

import pytest

from qchem_workbench.core.registry import load_species_registry


def test_load_valid_registry(tmp_path):
    xyz_dir = tmp_path / "xyz"
    xyz_dir.mkdir()
    (xyz_dir / "water.xyz").write_text(
        "3\n"
        "synthetic fixture water geometry\n"
        "O 0 0 0\n"
        "H 0 0.757 0.586\n"
        "H 0 -0.757 0.586\n",
        encoding="utf-8",
    )
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text(
        "schema_version: 1\n"
        "species:\n"
        "  - name: water\n"
        "    formula: H2O\n"
        "    charge: 0\n"
        "    multiplicity: 1\n"
        "    geometry_path: xyz/water.xyz\n"
        "    tags: [demo]\n"
        "    notes: Example molecule\n",
        encoding="utf-8",
    )

    species = load_species_registry(registry_path)

    assert len(species) == 1
    assert species[0].name == "water"
    assert species[0].geometry_path == xyz_dir / "water.xyz"
    assert species[0].conformers == ()


def test_duplicate_species_name_is_error(tmp_path):
    xyz_path = tmp_path / "water.xyz"
    xyz_path.write_text(
        "1\nsynthetic fixture atom geometry\nO 0 0 0\n",
        encoding="utf-8",
    )
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text(
        "schema_version: 1\n"
        "species:\n"
        "  - name: water\n"
        "    charge: 0\n"
        "    multiplicity: 1\n"
        "    geometry_path: water.xyz\n"
        "  - name: water\n"
        "    charge: 0\n"
        "    multiplicity: 1\n"
        "    geometry_path: water.xyz\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate species name"):
        load_species_registry(registry_path)


def test_missing_geometry_is_error(tmp_path):
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text(
        "schema_version: 1\n"
        "species:\n"
        "  - name: missing\n"
        "    charge: 0\n"
        "    multiplicity: 1\n"
        "    geometry_path: xyz/missing.xyz\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing geometry file"):
        load_species_registry(registry_path)


def test_invalid_xyz_is_error(tmp_path):
    xyz_path = tmp_path / "bad.xyz"
    xyz_path.write_text("1\nsynthetic fixture bad geometry\nXx 0 0 0\n", encoding="utf-8")
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text(
        "schema_version: 1\n"
        "species:\n"
        "  - name: bad\n"
        "    charge: 0\n"
        "    multiplicity: 1\n"
        "    geometry_path: bad.xyz\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported element symbol"):
        load_species_registry(registry_path)


def test_unsupported_schema_version_is_error(tmp_path):
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text("schema_version: 99\nspecies: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported schema_version"):
        load_species_registry(registry_path)


def test_missing_schema_version_is_error(tmp_path):
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text("species: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing schema_version"):
        load_species_registry(registry_path)


def test_load_conformer_species_registry(tmp_path):
    xyz_dir = tmp_path / "xyz"
    xyz_dir.mkdir()
    (xyz_dir / "ethanol_conf_001.xyz").write_text(
        "1\nsynthetic fixture ethanol conformer 1\nC 0 0 0\n",
        encoding="utf-8",
    )
    (xyz_dir / "ethanol_conf_002.xyz").write_text(
        "1\nsynthetic fixture ethanol conformer 2\nC 0 0 1\n",
        encoding="utf-8",
    )
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text(
        "schema_version: 1\n"
        "species:\n"
        "  - name: ethanol\n"
        "    formula: C2H6O\n"
        "    charge: 0\n"
        "    multiplicity: 1\n"
        "    conformers:\n"
        "      - id: conf_001\n"
        "        geometry_path: xyz/ethanol_conf_001.xyz\n"
        "      - id: conf_002\n"
        "        geometry_path: xyz/ethanol_conf_002.xyz\n",
        encoding="utf-8",
    )

    species = load_species_registry(registry_path)

    assert species[0].geometry_path == xyz_dir / "ethanol_conf_001.xyz"
    assert [conformer.id for conformer in species[0].conformers] == [
        "conf_001",
        "conf_002",
    ]


def test_missing_conformer_geometry_is_error(tmp_path):
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text(
        "schema_version: 1\n"
        "species:\n"
        "  - name: ethanol\n"
        "    charge: 0\n"
        "    multiplicity: 1\n"
        "    conformers:\n"
        "      - id: conf_001\n"
        "        geometry_path: xyz/missing.xyz\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing geometry file"):
        load_species_registry(registry_path)


def test_duplicate_conformer_id_is_error(tmp_path):
    xyz_path = tmp_path / "conf.xyz"
    xyz_path.write_text(
        "1\nsynthetic fixture conformer geometry\nC 0 0 0\n",
        encoding="utf-8",
    )
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text(
        "schema_version: 1\n"
        "species:\n"
        "  - name: ethanol\n"
        "    charge: 0\n"
        "    multiplicity: 1\n"
        "    conformers:\n"
        "      - id: conf_001\n"
        "        geometry_path: conf.xyz\n"
        "      - id: conf_001\n"
        "        geometry_path: conf.xyz\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate conformer id"):
        load_species_registry(registry_path)
