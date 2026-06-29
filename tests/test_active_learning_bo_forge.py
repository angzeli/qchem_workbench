from __future__ import annotations

import csv
import json

from qchem_workbench.active_learning.bo_forge import export_bo_forge_interchange
from qchem_workbench.active_learning.datasets import load_active_learning_campaign
from qchem_workbench.cli import main


def test_bo_forge_export_files_created(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    out_dir = tmp_path / "bo_forge_export"

    summary = export_bo_forge_interchange(
        campaign,
        [_scored_row("cand_001")],
        list(_scored_row("cand_001")),
        out_dir,
    )

    assert summary.candidate_count == 1
    assert (out_dir / "bo_forge_candidates.csv").exists()
    assert (out_dir / "bo_forge_observations.csv").exists()
    assert (out_dir / "bo_forge_metadata.json").exists()


def test_metadata_includes_schema_version(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    out_dir = tmp_path / "bo_forge_export"

    export_bo_forge_interchange(campaign, [_scored_row("cand_001")], list(_scored_row("cand_001")), out_dir)

    metadata = json.loads((out_dir / "bo_forge_metadata.json").read_text(encoding="utf-8"))
    assert metadata["schema_version"] == 1
    assert metadata["stable_path"] == "file_based_csv_json"


def test_missing_objectives_are_handled(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    out_dir = tmp_path / "bo_forge_export"

    summary = export_bo_forge_interchange(
        campaign,
        [{"candidate_id": "cand_001", "descriptor": "1.0"}],
        ["candidate_id", "descriptor"],
        out_dir,
    )

    assert summary.warnings
    metadata = json.loads((out_dir / "bo_forge_metadata.json").read_text(encoding="utf-8"))
    assert "no objective columns found" in metadata["warnings"][0]


def test_pending_candidates_preserved(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    out_dir = tmp_path / "bo_forge_export"

    export_bo_forge_interchange(
        campaign,
        [{"candidate_id": "cand_001", "descriptor": "1.0"}],
        ["candidate_id", "descriptor"],
        out_dir,
    )

    with (out_dir / "bo_forge_observations.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["observed_status"] == "pending"


def test_export_bo_forge_cli(tmp_path, capsys):
    campaign_path = _write_campaign_and_candidates(tmp_path)
    dataset_path = tmp_path / "scored.csv"
    _write_dataset(dataset_path)
    out_dir = tmp_path / "bo_forge_export"

    exit_code = main(
        [
            "active-learning",
            "export-bo-forge",
            str(campaign_path),
            str(dataset_path),
            "--out",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "BO Forge interchange" in captured.out
    assert (out_dir / "bo_forge_metadata.json").exists()


def _scored_row(candidate_id):
    return {
        "candidate_id": candidate_id,
        "descriptor": "1.0",
        "objective_ads_value": "0.4",
        "constraint_quality_pass": "True",
        "al_score": "0.4",
    }


def _write_dataset(path):
    row = _scored_row("cand_001")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


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
        "  name: synthetic bo forge handoff\n"
        "  candidates: candidates.yaml\n"
        "  descriptor_sources: []\n",
        encoding="utf-8",
    )
    return campaign_path
