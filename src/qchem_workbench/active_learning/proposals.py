"""Import proposed candidates from external optimisation tools."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.active_learning.candidates import ActiveLearningCandidate
from qchem_workbench.active_learning.datasets import ActiveLearningCampaign


@dataclass(frozen=True)
class ProposedCandidate:
    candidate_id: str
    proposal_rank: int | None = None
    acquisition_value: float | None = None
    proposed_by: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProposalImportSummary:
    proposals: tuple[ProposedCandidate, ...]
    todo_manifest: dict[str, Any]


def import_proposed_candidates_csv(
    campaign: ActiveLearningCampaign,
    path: Path,
) -> ProposalImportSummary:
    proposals = _read_proposals(path)
    _validate_proposals(campaign, proposals)
    manifest = proposal_todo_manifest(campaign, proposals)
    return ProposalImportSummary(proposals=tuple(proposals), todo_manifest=manifest)


def proposal_todo_manifest(
    campaign: ActiveLearningCampaign,
    proposals: list[ProposedCandidate] | tuple[ProposedCandidate, ...],
) -> dict[str, Any]:
    candidates_by_id = campaign.candidate_registry.by_id()
    calculations = []
    for proposal in proposals:
        candidate = candidates_by_id[proposal.candidate_id]
        calculations.append(
            {
                "candidate_id": proposal.candidate_id,
                "candidate_type": candidate.type,
                "species": candidate.species,
                "structure": candidate.structure,
                "system": candidate.system,
                "pathway": candidate.pathway,
                "proposal_rank": proposal.proposal_rank,
                "acquisition_value": proposal.acquisition_value,
                "proposed_by": proposal.proposed_by,
                "notes": proposal.notes,
                "status": "todo",
            }
        )
    return {
        "schema_version": 1,
        "calculation_todos": calculations,
        "metadata": {
            "campaign_name": campaign.name,
            "source": "active_learning_proposals",
            "note": "Planning manifest only; qchem-workbench does not run calculations automatically.",
        },
    }


def write_proposal_todo_manifest(path: Path, manifest: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )


def _read_proposals(path: Path) -> list[ProposedCandidate]:
    input_path = Path(path)
    with input_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "candidate_id" not in reader.fieldnames:
            raise ValueError(f"{input_path}: proposed_candidates.csv requires candidate_id")
        proposals = []
        for line_number, row in enumerate(reader, start=2):
            candidate_id = row.get("candidate_id", "").strip()
            if not candidate_id:
                raise ValueError(f"{input_path}:{line_number}: candidate_id is required")
            proposals.append(
                ProposedCandidate(
                    candidate_id=candidate_id,
                    proposal_rank=_optional_int(row.get("proposal_rank")),
                    acquisition_value=_optional_float(row.get("acquisition_value")),
                    proposed_by=_optional_str(row.get("proposed_by")),
                    notes=_optional_str(row.get("notes")),
                    metadata={
                        key: value
                        for key, value in row.items()
                        if key
                        not in {
                            "candidate_id",
                            "proposal_rank",
                            "acquisition_value",
                            "proposed_by",
                            "notes",
                        }
                    },
                )
            )
    return proposals


def _validate_proposals(
    campaign: ActiveLearningCampaign,
    proposals: list[ProposedCandidate],
) -> None:
    known_ids = {candidate.id for candidate in campaign.candidate_registry.candidates}
    seen: set[str] = set()
    duplicates: set[str] = set()
    unknown = []
    for proposal in proposals:
        if proposal.candidate_id in seen:
            duplicates.add(proposal.candidate_id)
        seen.add(proposal.candidate_id)
        if proposal.candidate_id not in known_ids:
            unknown.append(proposal.candidate_id)
    if duplicates:
        raise ValueError("duplicate proposed candidate(s): " + ", ".join(sorted(duplicates)))
    if unknown:
        raise ValueError("unknown proposed candidate(s): " + ", ".join(sorted(unknown)))


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
