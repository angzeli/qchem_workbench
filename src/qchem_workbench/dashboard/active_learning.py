"""Active-learning dashboard table helpers."""

from __future__ import annotations

from typing import Any

from qchem_workbench.active_learning.objectives import ObjectiveSpec
from qchem_workbench.active_learning.proposals import ProposedCandidate
from qchem_workbench.active_learning.state import CampaignState
from qchem_workbench.dashboard.data import DashboardData


def active_learning_dataset_rows(data: DashboardData) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in data.loaded_sections:
        if section.kind == "active_learning_dataset":
            rows.extend(section.rows)
    return rows


def active_learning_state_rows(data: DashboardData) -> list[dict[str, Any]]:
    section = data.section("active_learning_state")
    return list(section.rows) if section is not None else []


def active_learning_objective_rows(
    spec: ObjectiveSpec | None,
) -> dict[str, list[dict[str, Any]]]:
    if spec is None:
        return {
            "objectives": [],
            "constraints": [],
            "warnings": [
                {
                    "warning": (
                        "No objective specification was supplied; objective "
                        "directions and units cannot be inferred."
                    )
                }
            ],
        }
    return {
        "objectives": [
            {
                "id": objective.id,
                "source_column": objective.source_column,
                "direction": objective.direction,
                "weight": objective.weight,
                "target": objective.target,
                "transform": getattr(objective, "transform", None),
            }
            for objective in spec.objectives
        ],
        "constraints": [
            {
                "id": constraint.id,
                "source_column": constraint.source_column,
                "op": constraint.op,
                "value": constraint.value,
            }
            for constraint in spec.constraints
        ],
        "warnings": [],
    }


def active_learning_missing_descriptor_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing_rows = []
    for row in rows:
        reasons = {
            key: value
            for key, value in row.items()
            if key.startswith("missing_") and value not in ("", None)
        }
        al_reasons = row.get("al_reasons")
        if reasons or al_reasons:
            missing_rows.append(
                {
                    "candidate_id": row.get("candidate_id"),
                    "missing_reasons": "; ".join(
                        f"{key}={value}" for key, value in reasons.items()
                    ),
                    "al_reasons": al_reasons,
                }
            )
    return missing_rows


def active_learning_quality_flag_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flagged = []
    for row in rows:
        for key, value in row.items():
            if key.endswith("quality_flags") and value not in ("", None):
                flagged.append(
                    {
                        "candidate_id": row.get("candidate_id"),
                        "source": key.removesuffix("_quality_flags") or "dataset",
                        "quality_flags": value,
                    }
                )
    return flagged


def active_learning_ranking_rows(
    rows: list[dict[str, Any]],
    *,
    top: int | None = None,
) -> list[dict[str, Any]]:
    ranked = [row for row in rows if _optional_int(row.get("al_rank")) is not None]
    ranked.sort(key=lambda row: _optional_int(row.get("al_rank")) or 10**9)
    output = [
        {
            "candidate_id": row.get("candidate_id"),
            "rank": row.get("al_rank"),
            "score": row.get("al_score"),
            "status": row.get("al_status"),
            "score_components": "; ".join(
                f"{key}={value}"
                for key, value in row.items()
                if key.startswith("score_component_") and value not in ("", None)
            ),
            "reasons": row.get("al_reasons"),
        }
        for row in ranked
    ]
    return output[:top] if top is not None else output


def active_learning_proposal_rows(
    proposals: list[ProposedCandidate] | tuple[ProposedCandidate, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": proposal.candidate_id,
            "proposal_rank": proposal.proposal_rank,
            "acquisition_value": proposal.acquisition_value,
            "proposed_by": proposal.proposed_by,
            "notes": proposal.notes,
        }
        for proposal in sorted(
            proposals,
            key=lambda proposal: proposal.proposal_rank
            if proposal.proposal_rank is not None
            else 10**9,
        )
    ]


def active_learning_transition_rows(state: CampaignState) -> list[dict[str, Any]]:
    return [
        {
            "timestamp_utc": entry.timestamp_utc,
            "candidate_id": entry.candidate_id,
            "from_state": entry.from_state,
            "to_state": entry.to_state,
            "reason": entry.reason,
            "result": entry.result,
        }
        for entry in state.audit_log
    ]


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
