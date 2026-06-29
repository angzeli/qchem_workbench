from __future__ import annotations

import pytest
import yaml

from qchem_workbench.active_learning.datasets import load_active_learning_campaign
from qchem_workbench.active_learning.proposals import (
    import_proposed_candidates_csv,
    write_proposal_todo_manifest,
)
from qchem_workbench.cli import main


def test_valid_proposal_import(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    proposals_path = _write_proposals(tmp_path)

    summary = import_proposed_candidates_csv(campaign, proposals_path)

    assert len(summary.proposals) == 1
    assert summary.proposals[0].candidate_id == "cand_001"
    assert summary.todo_manifest["calculation_todos"][0]["status"] == "todo"


def test_unknown_candidate_is_error(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    proposals_path = _write_proposals(tmp_path, candidate_id="missing")

    with pytest.raises(ValueError, match="unknown proposed candidate"):
        import_proposed_candidates_csv(campaign, proposals_path)


def test_duplicate_candidate_is_error(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    proposals_path = tmp_path / "proposed_candidates.csv"
    proposals_path.write_text(
        "candidate_id,proposal_rank\ncand_001,1\ncand_001,2\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate proposed candidate"):
        import_proposed_candidates_csv(campaign, proposals_path)


def test_todo_manifest_output(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    summary = import_proposed_candidates_csv(campaign, _write_proposals(tmp_path))
    out_path = tmp_path / "next_calculations.yaml"

    write_proposal_todo_manifest(out_path, summary.todo_manifest)

    data = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["calculation_todos"][0]["candidate_id"] == "cand_001"
    assert "does not run calculations automatically" in data["metadata"]["note"]


def test_import_proposals_cli(tmp_path, capsys):
    campaign_path = _write_campaign_and_candidates(tmp_path)
    proposals_path = _write_proposals(tmp_path)
    out_path = tmp_path / "next_calculations.yaml"

    exit_code = main(
        [
            "active-learning",
            "import-proposals",
            str(campaign_path),
            str(proposals_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "proposed candidate" in captured.out
    assert out_path.exists()


def _write_proposals(tmp_path, *, candidate_id="cand_001"):
    path = tmp_path / "proposed_candidates.csv"
    path.write_text(
        "candidate_id,proposal_rank,acquisition_value,proposed_by,notes\n"
        f"{candidate_id},1,0.7,synthetic_optimizer,Synthetic proposal\n",
        encoding="utf-8",
    )
    return path


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
        "  name: synthetic proposal campaign\n"
        "  candidates: candidates.yaml\n"
        "  descriptor_sources: []\n",
        encoding="utf-8",
    )
    return campaign_path
