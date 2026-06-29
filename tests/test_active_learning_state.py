from __future__ import annotations

import json

import pytest

from qchem_workbench.active_learning.state import (
    load_campaign_state,
    mark_candidate_state,
    save_campaign_state,
    state_summary,
)
from qchem_workbench.cli import main


def test_valid_state_transitions(tmp_path):
    state = load_campaign_state(_write_state(tmp_path))

    state = mark_candidate_state(state, "cand_001", "proposed", reason="selected")
    state = mark_candidate_state(state, "cand_001", "pending", reason="input rendered")
    state = mark_candidate_state(
        state,
        "cand_001",
        "completed",
        result="results/qe_results.json",
    )

    assert state.candidates["cand_001"].state == "completed"
    assert state.candidates["cand_001"].result == "results/qe_results.json"


def test_invalid_transition_is_error(tmp_path):
    state = load_campaign_state(_write_state(tmp_path))

    with pytest.raises(ValueError, match="invalid state transition"):
        mark_candidate_state(state, "cand_001", "pending")


def test_failed_and_excluded_require_reason(tmp_path):
    state = load_campaign_state(_write_state(tmp_path))
    state = mark_candidate_state(state, "cand_001", "proposed")
    state = mark_candidate_state(state, "cand_001", "pending")

    with pytest.raises(ValueError, match="requires a reason"):
        mark_candidate_state(state, "cand_001", "failed")


def test_audit_log_entry_is_written(tmp_path):
    state = load_campaign_state(_write_state(tmp_path))

    updated = mark_candidate_state(state, "cand_001", "proposed", reason="BO proposal")

    assert len(updated.audit_log) == 1
    assert updated.audit_log[0].from_state == "unobserved"
    assert updated.audit_log[0].to_state == "proposed"
    assert updated.audit_log[0].reason == "BO proposal"


def test_state_summary_counts(tmp_path):
    state = load_campaign_state(_write_state(tmp_path))

    summary = state_summary(state)

    assert summary["unobserved"] == 1
    assert summary["pending"] == 0


def test_save_campaign_state_round_trip(tmp_path):
    state_path = _write_state(tmp_path)
    state = load_campaign_state(state_path)
    updated = mark_candidate_state(state, "cand_001", "proposed")

    save_campaign_state(state_path, updated)
    reloaded = load_campaign_state(state_path)

    assert reloaded.candidates["cand_001"].state == "proposed"
    assert reloaded.audit_log[0].candidate_id == "cand_001"


def test_active_learning_state_summary_cli(tmp_path, capsys):
    state_path = _write_state(tmp_path)

    exit_code = main(["active-learning", "state", str(state_path), "summary"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "unobserved\t1" in captured.out


def test_active_learning_state_mark_cli(tmp_path, capsys):
    state_path = _write_state(tmp_path)

    exit_code = main(
        [
            "active-learning",
            "state",
            str(state_path),
            "mark-proposed",
            "cand_001",
            "--reason",
            "synthetic BO proposal",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Marked cand_001 as proposed" in captured.out
    state = load_campaign_state(state_path)
    assert state.candidates["cand_001"].state == "proposed"


def _write_state(tmp_path):
    state_path = tmp_path / "campaign_state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "candidates": {
                    "cand_001": {
                        "state": "unobserved",
                        "metadata": {"notes": "Synthetic candidate state"},
                    }
                },
                "audit_log": [],
            }
        ),
        encoding="utf-8",
    )
    return state_path
