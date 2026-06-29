from __future__ import annotations

import importlib.util

import pytest

from qchem_workbench.active_learning.bo_forge import export_bo_forge_interchange
from qchem_workbench.active_learning.bo_forge_adapter import (
    BOForgeUnavailableError,
    from_bo_forge_proposals,
    to_bo_forge_dataset,
)
from qchem_workbench.active_learning.datasets import load_active_learning_campaign


def test_adapter_import_error_when_unavailable():
    if importlib.util.find_spec("bo_forge") is not None:
        pytest.skip("BO Forge is installed; unavailable path is not applicable")

    with pytest.raises(BOForgeUnavailableError):
        to_bo_forge_dataset([], [])


def test_adapter_smoke_when_available():
    pytest.importorskip("bo_forge")

    dataset = to_bo_forge_dataset(
        [{"candidate_id": "cand_001", "objective": "1.0"}],
        ["candidate_id", "objective"],
    )
    proposals = from_bo_forge_proposals(
        [{"candidate_id": "cand_001", "proposal_rank": "1"}]
    )

    assert dataset["candidate_id_column"] == "candidate_id"
    assert proposals[0].candidate_id == "cand_001"


def test_file_based_path_unaffected(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    out_dir = tmp_path / "export"

    export_bo_forge_interchange(
        campaign,
        [{"candidate_id": "cand_001"}],
        ["candidate_id"],
        out_dir,
    )

    assert (out_dir / "bo_forge_metadata.json").exists()


def _write_campaign_and_candidates(tmp_path):
    (tmp_path / "candidates.yaml").write_text(
        "schema_version: 1\n"
        "candidates:\n"
        "  - id: cand_001\n"
        "    type: molecule\n"
        "    species: CO\n",
        encoding="utf-8",
    )
    campaign_path = tmp_path / "campaign.yaml"
    campaign_path.write_text(
        "schema_version: 1\n"
        "active_learning_campaign:\n"
        "  name: synthetic adapter campaign\n"
        "  candidates: candidates.yaml\n"
        "  descriptor_sources: []\n",
        encoding="utf-8",
    )
    return campaign_path
