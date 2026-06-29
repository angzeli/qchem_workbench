"""Markdown reporting for active-learning campaign loops."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from qchem_workbench.active_learning.datasets import ActiveLearningCampaign
from qchem_workbench.active_learning.objectives import ObjectiveSpec
from qchem_workbench.active_learning.proposals import ProposedCandidate
from qchem_workbench.active_learning.state import CampaignState, state_summary


MISSING = "N/A"


def generate_active_learning_report(
    campaign: ActiveLearningCampaign,
    state: CampaignState,
    dataset_rows: list[dict[str, str]],
    dataset_headers: list[str],
    *,
    objective_spec: ObjectiveSpec | None = None,
    proposals: list[ProposedCandidate] | tuple[ProposedCandidate, ...] | None = None,
    title: str | None = None,
) -> str:
    """Return a Markdown active-learning campaign report.

    The report is bookkeeping only. It summarizes explicit candidate states,
    descriptors, objective columns, and proposals without claiming optimisation
    success or scientific performance.
    """

    proposal_list = list(proposals or [])
    sections = [
        f"# {_markdown_text(title or f'Active-learning report: {campaign.name}')}",
        _campaign_overview(campaign, state, dataset_rows),
        _state_counts(state),
        _objective_definitions(objective_spec, dataset_headers),
        _observed_objective_summary(dataset_rows, dataset_headers),
        _current_best_candidates(dataset_rows),
        _proposed_candidates(proposal_list),
        _pending_failed_candidates(state),
        _quality_warnings(dataset_rows),
        _bo_forge_provenance(dataset_headers, proposal_list),
    ]
    return "\n\n".join(sections).rstrip() + "\n"


def write_active_learning_report(
    path: Path,
    campaign: ActiveLearningCampaign,
    state: CampaignState,
    dataset_rows: list[dict[str, str]],
    dataset_headers: list[str],
    *,
    objective_spec: ObjectiveSpec | None = None,
    proposals: list[ProposedCandidate] | tuple[ProposedCandidate, ...] | None = None,
    title: str | None = None,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        generate_active_learning_report(
            campaign,
            state,
            dataset_rows,
            dataset_headers,
            objective_spec=objective_spec,
            proposals=proposals,
            title=title,
        ),
        encoding="utf-8",
    )


def _campaign_overview(
    campaign: ActiveLearningCampaign,
    state: CampaignState,
    dataset_rows: list[dict[str, str]],
) -> str:
    rows = [
        ("Campaign", campaign.name),
        ("Candidates in registry", len(campaign.candidate_registry.candidates)),
        ("Candidates in state file", len(state.candidates)),
        ("Rows in dataset", len(dataset_rows)),
        (
            "Descriptor sources",
            ", ".join(f"{source.id}:{source.type}" for source in campaign.descriptor_sources)
            or MISSING,
        ),
    ]
    return "## Campaign overview\n\n" + _markdown_table(["Item", "Value"], rows)


def _state_counts(state: CampaignState) -> str:
    counts = state_summary(state)
    rows = [(label, counts[label]) for label in sorted(counts)]
    return "## Candidate counts by state\n\n" + _markdown_table(["State", "Count"], rows)


def _objective_definitions(
    objective_spec: ObjectiveSpec | None,
    dataset_headers: list[str],
) -> str:
    if objective_spec is None:
        objective_columns = _objective_value_columns(dataset_headers)
        column_text = ", ".join(objective_columns) if objective_columns else MISSING
        return (
            "## Objective definitions\n\n"
            "Objective YAML was not supplied; this report does not infer campaign "
            "success from descriptors alone.\n\n"
            + _markdown_table(
                ["Visible objective columns", "Units from column names"],
                [(column_text, ", ".join(_unit_for_column(column) for column in objective_columns) or MISSING)],
            )
        )

    objective_rows = [
        (
            objective.id,
            objective.source_column,
            objective.direction,
            objective.weight,
            _unit_for_column(objective.source_column),
        )
        for objective in objective_spec.objectives
    ]
    constraint_rows = [
        (
            constraint.id,
            constraint.source_column,
            constraint.op,
            constraint.value,
        )
        for constraint in objective_spec.constraints
    ]
    text = "## Objective definitions\n\n" + _markdown_table(
        ["ID", "Source column", "Direction", "Weight", "Units from column name"],
        objective_rows,
    )
    if constraint_rows:
        text += "\n\n" + _markdown_table(
            ["Constraint ID", "Source column", "Operator", "Value"],
            constraint_rows,
        )
    return text


def _observed_objective_summary(
    rows: list[dict[str, str]],
    headers: list[str],
) -> str:
    objective_columns = [column for column in _objective_value_columns(headers) if column != "al_score"]
    if "al_score" in headers:
        objective_columns.append("al_score")
    if not objective_columns:
        return "## Observed objective summary\n\nNo objective columns were found."

    table_rows = []
    for column in objective_columns:
        values = [_optional_float(row.get(column)) for row in rows]
        numeric = [value for value in values if value is not None]
        table_rows.append(
            (
                column,
                _unit_for_column(column),
                len(numeric),
                _format_number(min(numeric) if numeric else None),
                _format_number(max(numeric) if numeric else None),
                _format_number(mean(numeric) if numeric else None),
            )
        )
    return "## Observed objective summary\n\n" + _markdown_table(
        ["Column", "Units", "Observed rows", "Minimum", "Maximum", "Mean"],
        table_rows,
    )


def _current_best_candidates(rows: list[dict[str, str]]) -> str:
    ranked_rows = [row for row in rows if _optional_int(row.get("al_rank")) is not None]
    if not ranked_rows:
        return (
            "## Current best candidates\n\n"
            "No ranked candidates were found; use an explicit objective table to "
            "score the dataset before interpreting candidate order."
        )

    ranked_rows.sort(key=lambda row: _optional_int(row.get("al_rank")) or 10**9)
    table_rows = [
        (
            row.get("al_rank"),
            row.get("candidate_id"),
            row.get("al_score"),
            row.get("al_status"),
            row.get("al_reasons"),
        )
        for row in ranked_rows[:10]
    ]
    return "## Current best candidates\n\n" + _markdown_table(
        ["Rank", "Candidate ID", "Score", "Status", "Reasons"],
        table_rows,
    )


def _proposed_candidates(proposals: list[ProposedCandidate]) -> str:
    if not proposals:
        return "## Proposed next candidates\n\nNo proposal file was supplied."
    rows = [
        (
            proposal.proposal_rank,
            proposal.candidate_id,
            proposal.acquisition_value,
            proposal.proposed_by,
            proposal.notes,
        )
        for proposal in sorted(
            proposals,
            key=lambda item: item.proposal_rank if item.proposal_rank is not None else 10**9,
        )
    ]
    return "## Proposed next candidates\n\n" + _markdown_table(
        ["Proposal rank", "Candidate ID", "Acquisition value", "Proposed by", "Notes"],
        rows,
    )


def _pending_failed_candidates(state: CampaignState) -> str:
    rows = [
        (
            candidate_id,
            entry.state,
            entry.result,
            entry.reason,
        )
        for candidate_id, entry in sorted(state.candidates.items())
        if entry.state in {"pending", "failed"}
    ]
    if not rows:
        return "## Failed and pending calculations\n\nNo pending or failed candidates were recorded."
    return "## Failed and pending calculations\n\n" + _markdown_table(
        ["Candidate ID", "State", "Result", "Reason"],
        rows,
    )


def _quality_warnings(rows: list[dict[str, str]]) -> str:
    flagged = []
    for row in rows:
        warning_count = _optional_int(row.get("quality_warning_count")) or 0
        error_count = _optional_int(row.get("quality_error_count")) or 0
        flags = row.get("quality_flags", "")
        if warning_count or error_count or flags:
            flagged.append(
                (
                    row.get("candidate_id"),
                    error_count,
                    warning_count,
                    flags,
                    row.get("missing_data_reasons"),
                )
            )
    if not flagged:
        return "## Quality warnings\n\nNo quality flags were present in the dataset."
    return "## Quality warnings\n\n" + _markdown_table(
        ["Candidate ID", "Quality errors", "Quality warnings", "Flags", "Missing data"],
        flagged,
    )


def _bo_forge_provenance(
    headers: list[str],
    proposals: list[ProposedCandidate],
) -> str:
    rows = [
        ("Dataset contains BO-style score columns", "yes" if "al_score" in headers else "no"),
        ("Proposal import included", "yes" if proposals else "no"),
        (
            "Stable interchange path",
            "file-based CSV/JSON; no BO Forge Python dependency is required",
        ),
    ]
    return "## BO Forge export/import provenance\n\n" + _markdown_table(["Item", "Value"], rows)


def _objective_value_columns(headers: list[str]) -> list[str]:
    return [
        column
        for column in headers
        if (column.startswith("objective_") and column.endswith("_value")) or column == "al_score"
    ]


def _unit_for_column(column: str) -> str:
    lowered = column.lower()
    if lowered.endswith("_ev") or "_ev_" in lowered:
        return "eV"
    if lowered.endswith("_hartree") or "_hartree_" in lowered:
        return "Hartree"
    if lowered.endswith("_kj_mol") or "_kj_mol_" in lowered:
        return "kJ/mol"
    if lowered.endswith("_cm1") or "_cm1_" in lowered:
        return "cm^-1"
    if lowered.endswith("_k") or "_k_" in lowered:
        return "K"
    return "not specified"


def _markdown_table(headers: list[str], rows: list[tuple[Any, ...]]) -> str:
    header_line = "| " + " | ".join(_markdown_text(header) for header in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_markdown_text(_format_value(value)) for value in row) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator, *body])


def _format_value(value: Any) -> str:
    if value is None or value == "":
        return MISSING
    if isinstance(value, float):
        return _format_number(value)
    return str(value)


def _format_number(value: float | None) -> str:
    if value is None:
        return MISSING
    return f"{value:.6g}"


def _markdown_text(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
