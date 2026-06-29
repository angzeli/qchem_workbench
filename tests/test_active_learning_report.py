from __future__ import annotations

import csv
import json

from qchem_workbench.active_learning.datasets import load_active_learning_campaign
from qchem_workbench.active_learning.objectives import load_objective_spec
from qchem_workbench.active_learning.proposals import import_proposed_candidates_csv
from qchem_workbench.active_learning.report import generate_active_learning_report
from qchem_workbench.active_learning.state import load_campaign_state
from qchem_workbench.cli import main


def test_report_with_completed_candidates(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    state = load_campaign_state(_write_state(tmp_path))
    objective_spec = load_objective_spec(_write_objectives(tmp_path))

    report = generate_active_learning_report(
        campaign,
        state,
        _dataset_rows(),
        list(_dataset_rows()[0]),
        objective_spec=objective_spec,
    )

    assert "## Campaign overview" in report
    assert "completed" in report
    assert "cand_001" in report
    assert "adsorption_energy_eV" in report


def test_report_with_pending_and_failed_candidates(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    state = load_campaign_state(_write_state(tmp_path, include_pending_failed=True))

    report = generate_active_learning_report(
        campaign,
        state,
        _dataset_rows(),
        list(_dataset_rows()[0]),
    )

    assert "## Failed and pending calculations" in report
    assert "cand_002" in report
    assert "synthetic parser failure" in report


def test_report_with_proposals(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    state = load_campaign_state(_write_state(tmp_path))
    proposals = import_proposed_candidates_csv(campaign, _write_proposals(tmp_path)).proposals

    report = generate_active_learning_report(
        campaign,
        state,
        _dataset_rows(),
        list(_dataset_rows()[0]),
        proposals=proposals,
    )

    assert "## Proposed next candidates" in report
    assert "synthetic_optimizer" in report


def test_missing_objective_warning_is_visible(tmp_path):
    campaign = load_active_learning_campaign(_write_campaign_and_candidates(tmp_path))
    state = load_campaign_state(_write_state(tmp_path))

    report = generate_active_learning_report(
        campaign,
        state,
        _dataset_rows(),
        list(_dataset_rows()[0]),
    )

    assert "Objective YAML was not supplied" in report
    assert "does not infer campaign success" in report


def test_active_learning_report_cli(tmp_path, capsys):
    campaign_path = _write_campaign_and_candidates(tmp_path)
    state_path = _write_state(tmp_path)
    dataset_path = _write_dataset(tmp_path)
    objectives_path = _write_objectives(tmp_path)
    proposals_path = _write_proposals(tmp_path)
    out_path = tmp_path / "al_report.md"

    exit_code = main(
        [
            "active-learning",
            "report",
            str(campaign_path),
            str(state_path),
            str(dataset_path),
            "--objectives",
            str(objectives_path),
            "--proposals",
            str(proposals_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "active-learning report" in captured.out
    report = out_path.read_text(encoding="utf-8")
    assert "# Active-learning report" in report
    assert "BO Forge export/import provenance" in report


def _dataset_rows():
    return [
        {
            "candidate_id": "cand_001",
            "adsorption_energy_eV": "-0.4",
            "objective_minimise_adsorption_energy_value": "0.4",
            "constraint_require_no_quality_errors_pass": "True",
            "quality_error_count": "0",
            "quality_warning_count": "0",
            "quality_flags": "",
            "al_score": "0.4",
            "al_rank": "1",
            "al_status": "ranked",
            "al_reasons": "",
        },
        {
            "candidate_id": "cand_002",
            "adsorption_energy_eV": "",
            "objective_minimise_adsorption_energy_value": "",
            "constraint_require_no_quality_errors_pass": "False",
            "quality_error_count": "1",
            "quality_warning_count": "1",
            "quality_flags": "missing_descriptor",
            "al_score": "",
            "al_rank": "",
            "al_status": "excluded",
            "al_reasons": "missing descriptor",
        },
    ]


def _write_dataset(tmp_path):
    path = tmp_path / "al_dataset.csv"
    rows = _dataset_rows()
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_proposals(tmp_path):
    path = tmp_path / "proposed_candidates.csv"
    path.write_text(
        "candidate_id,proposal_rank,acquisition_value,proposed_by,notes\n"
        "cand_001,1,0.8,synthetic_optimizer,Synthetic proposal\n",
        encoding="utf-8",
    )
    return path


def _write_objectives(tmp_path):
    path = tmp_path / "objectives.yaml"
    path.write_text(
        "schema_version: 1\n"
        "objectives:\n"
        "  - id: minimise_adsorption_energy\n"
        "    source_column: adsorption_energy_eV\n"
        "    direction: minimise\n"
        "    weight: 1.0\n"
        "constraints:\n"
        "  - id: require_no_quality_errors\n"
        "    source_column: quality_error_count\n"
        "    op: equals\n"
        "    value: 0\n",
        encoding="utf-8",
    )
    return path


def _write_state(tmp_path, *, include_pending_failed: bool = False):
    candidates = {
        "cand_001": {
            "state": "completed",
            "result": "results/synthetic_results.json",
            "metadata": {},
        }
    }
    if include_pending_failed:
        candidates["cand_002"] = {
            "state": "failed",
            "reason": "synthetic parser failure",
            "metadata": {},
        }
        candidates["cand_003"] = {
            "state": "pending",
            "reason": "input rendered",
            "metadata": {},
        }
    path = tmp_path / "campaign_state.json"
    path.write_text(
        json.dumps({"schema_version": 1, "candidates": candidates, "audit_log": []}),
        encoding="utf-8",
    )
    return path


def _write_campaign_and_candidates(tmp_path):
    (tmp_path / "candidates.yaml").write_text(
        "schema_version: 1\n"
        "candidates:\n"
        "  - id: cand_001\n"
        "    type: adsorbate_system\n"
        "    system: co_on_surface\n"
        "    metadata:\n"
        "      notes: Synthetic adsorption-screening candidate\n"
        "  - id: cand_002\n"
        "    type: adsorbate_system\n"
        "    system: h_on_surface\n"
        "  - id: cand_003\n"
        "    type: adsorbate_system\n"
        "    system: o_on_surface\n",
        encoding="utf-8",
    )
    campaign_path = tmp_path / "campaign.yaml"
    campaign_path.write_text(
        "schema_version: 1\n"
        "active_learning_campaign:\n"
        "  name: synthetic adsorption screening\n"
        "  candidates: candidates.yaml\n"
        "  descriptor_sources: []\n",
        encoding="utf-8",
    )
    return campaign_path
