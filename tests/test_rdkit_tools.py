from __future__ import annotations

import json

import pytest

from qchem_workbench.core.geometry import read_xyz
from qchem_workbench.geometry.rdkit_tools import generate_conformer_xyz_files


def test_rdkit_tools_import_without_requiring_rdkit():
    import qchem_workbench.geometry.rdkit_tools as rdkit_tools

    assert callable(rdkit_tools.generate_conformer_xyz_files)


def test_generate_conformer_rejects_nonpositive_count_without_rdkit():
    with pytest.raises(ValueError, match="number_of_conformers"):
        generate_conformer_xyz_files("O", "water", ".", 0)


def test_generate_conformer_xyz_files_with_rdkit(tmp_path):
    pytest.importorskip("rdkit")

    metadata = generate_conformer_xyz_files(
        smiles="O",
        molecule_name="water",
        output_dir=tmp_path,
        number_of_conformers=2,
    )

    metadata_path = tmp_path / "water_conformers.json"
    metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["number_generated"] == 2
    assert metadata_payload["generator"] == "rdkit"
    assert "not an optimized quantum-chemical minimum" in metadata_payload["warnings"][0]
    assert len(metadata_payload["conformers"]) == 2

    for conformer in metadata_payload["conformers"]:
        geometry_path = tmp_path / conformer["geometry_path"]
        geometry = read_xyz(geometry_path)
        assert geometry_path.exists()
        assert geometry.comment.startswith("RDKit-generated starting conformer")
        assert len(geometry.atoms) == 3
