"""Active-learning campaign state tracking."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE_LEARNING_STATE_SCHEMA_VERSION = 1
VALID_STATES = {"unobserved", "proposed", "pending", "completed", "failed", "excluded"}
VALID_TRANSITIONS = {
    ("unobserved", "proposed"),
    ("proposed", "pending"),
    ("pending", "completed"),
    ("pending", "failed"),
    ("completed", "excluded"),
}


@dataclass(frozen=True)
class CandidateStateEntry:
    candidate_id: str
    state: str = "unobserved"
    result: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StateAuditEntry:
    timestamp_utc: str
    candidate_id: str
    from_state: str
    to_state: str
    reason: str | None = None
    result: str | None = None


@dataclass(frozen=True)
class CampaignState:
    candidates: dict[str, CandidateStateEntry]
    audit_log: tuple[StateAuditEntry, ...] = ()
    source_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ACTIVE_LEARNING_STATE_SCHEMA_VERSION,
            "candidates": {
                candidate_id: {
                    "state": entry.state,
                    "result": entry.result,
                    "reason": entry.reason,
                    "metadata": dict(entry.metadata),
                }
                for candidate_id, entry in sorted(self.candidates.items())
            },
            "audit_log": [
                {
                    "timestamp_utc": entry.timestamp_utc,
                    "candidate_id": entry.candidate_id,
                    "from_state": entry.from_state,
                    "to_state": entry.to_state,
                    "reason": entry.reason,
                    "result": entry.result,
                }
                for entry in self.audit_log
            ],
        }


def load_campaign_state(path: Path) -> CampaignState:
    state_path = Path(path)
    data = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{state_path}: campaign state must be a JSON object")
    schema_version = data.get("schema_version")
    if schema_version != ACTIVE_LEARNING_STATE_SCHEMA_VERSION:
        raise ValueError(
            f"{state_path}: unsupported schema_version {schema_version!r}; "
            f"expected {ACTIVE_LEARNING_STATE_SCHEMA_VERSION}"
        )
    raw_candidates = data.get("candidates")
    if not isinstance(raw_candidates, dict):
        raise ValueError(f"{state_path}: candidates must be a mapping")
    candidates = {
        candidate_id: _candidate_entry(state_path, candidate_id, raw)
        for candidate_id, raw in raw_candidates.items()
    }
    raw_audit = data.get("audit_log", [])
    if not isinstance(raw_audit, list):
        raise ValueError(f"{state_path}: audit_log must be a list")
    audit_log = tuple(_audit_entry(state_path, raw) for raw in raw_audit)
    return CampaignState(candidates=candidates, audit_log=audit_log, source_path=state_path)


def save_campaign_state(path: Path, state: CampaignState) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def mark_candidate_state(
    state: CampaignState,
    candidate_id: str,
    to_state: str,
    *,
    reason: str | None = None,
    result: str | None = None,
) -> CampaignState:
    if to_state not in VALID_STATES:
        raise ValueError(f"unsupported candidate state {to_state!r}")
    if candidate_id not in state.candidates:
        raise ValueError(f"unknown candidate {candidate_id!r} in campaign state")
    entry = state.candidates[candidate_id]
    if (entry.state, to_state) not in VALID_TRANSITIONS:
        raise ValueError(f"invalid state transition {entry.state!r} -> {to_state!r}")
    if to_state in {"failed", "excluded"} and not reason:
        raise ValueError(f"transition to {to_state!r} requires a reason")
    next_entry = CandidateStateEntry(
        candidate_id=candidate_id,
        state=to_state,
        result=result if result is not None else entry.result,
        reason=reason if reason is not None else entry.reason,
        metadata=dict(entry.metadata),
    )
    candidates = dict(state.candidates)
    candidates[candidate_id] = next_entry
    audit_entry = StateAuditEntry(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        candidate_id=candidate_id,
        from_state=entry.state,
        to_state=to_state,
        reason=reason,
        result=result,
    )
    return CampaignState(
        candidates=candidates,
        audit_log=(*state.audit_log, audit_entry),
        source_path=state.source_path,
    )


def state_summary(state: CampaignState) -> dict[str, int]:
    summary = {label: 0 for label in sorted(VALID_STATES)}
    for entry in state.candidates.values():
        summary[entry.state] = summary.get(entry.state, 0) + 1
    return summary


def _candidate_entry(path: Path, candidate_id: str, raw: Any) -> CandidateStateEntry:
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: candidates.{candidate_id} must be a mapping")
    current_state = raw.get("state", "unobserved")
    if current_state not in VALID_STATES:
        raise ValueError(f"{path}: candidates.{candidate_id} has invalid state")
    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}: candidates.{candidate_id}.metadata must be a mapping")
    return CandidateStateEntry(
        candidate_id=candidate_id,
        state=current_state,
        result=_optional_str(raw.get("result")),
        reason=_optional_str(raw.get("reason")),
        metadata=dict(metadata),
    )


def _audit_entry(path: Path, raw: Any) -> StateAuditEntry:
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: audit_log entries must be mappings")
    return StateAuditEntry(
        timestamp_utc=str(raw.get("timestamp_utc", "")),
        candidate_id=str(raw.get("candidate_id", "")),
        from_state=str(raw.get("from_state", "")),
        to_state=str(raw.get("to_state", "")),
        reason=_optional_str(raw.get("reason")),
        result=_optional_str(raw.get("result")),
    )


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
