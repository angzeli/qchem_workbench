"""File-based active-learning handoff utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from qchem_workbench.campaigns import CampaignManifest


@dataclass(frozen=True)
class HandoffTable:
    """CSV-ready handoff table."""

    headers: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ProposedCandidate:
    """Candidate proposed by an external active-learning or BO tool."""

    candidate_id: str
    metadata: dict[str, Any]


def candidate_handoff_table(campaign: CampaignManifest) -> HandoffTable:
    """Export campaign candidates for external tools."""

    rows = tuple(
        {
            "candidate_id": candidate.id,
            "species_name": candidate.species_name or "",
            "structure_path": str(candidate.structure_path)
            if candidate.structure_path is not None
            else "",
            "tags": ";".join(candidate.tags),
        }
        for candidate in campaign.candidates
    )
    return HandoffTable(
        headers=("candidate_id", "species_name", "structure_path", "tags"),
        rows=rows,
    )


def objective_handoff_table(
    descriptor_rows: Iterable[dict[str, Any]],
    objective_columns: Iterable[str],
) -> HandoffTable:
    """Export selected descriptor columns as objective values."""

    objectives = tuple(objective_columns)
    headers = ("candidate_id", *objectives)
    rows = []
    for row in descriptor_rows:
        rows.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                **{column: row.get(column, "") for column in objectives},
            }
        )
    return HandoffTable(headers=headers, rows=tuple(rows))


def write_handoff_table_csv(path: Path, table: HandoffTable) -> None:
    """Write a handoff table to CSV."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table.headers))
        writer.writeheader()
        writer.writerows(table.rows)


def read_proposed_candidates_csv(path: Path) -> list[ProposedCandidate]:
    """Read candidate IDs proposed by an external optimizer."""

    input_path = Path(path)
    with input_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{input_path}: proposed candidate CSV is missing headers")
        id_field = "candidate_id" if "candidate_id" in reader.fieldnames else "id"
        if id_field not in reader.fieldnames:
            raise ValueError(
                f"{input_path}: proposed candidate CSV requires candidate_id or id"
            )
        proposed = []
        for index, row in enumerate(reader, start=2):
            candidate_id = row.get(id_field, "")
            if not candidate_id:
                raise ValueError(f"{input_path}:{index}: candidate ID is required")
            proposed.append(
                ProposedCandidate(
                    candidate_id=candidate_id,
                    metadata={key: value for key, value in row.items() if key != id_field},
                )
            )
    return proposed


def write_proposed_candidates_csv(
    path: Path,
    proposed: Iterable[ProposedCandidate],
) -> None:
    """Write proposed candidates to CSV."""

    proposed_list = list(proposed)
    metadata_headers = sorted(
        {
            key
            for candidate in proposed_list
            for key in candidate.metadata
        }
    )
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["candidate_id", *metadata_headers],
        )
        writer.writeheader()
        for candidate in proposed_list:
            writer.writerow(
                {
                    "candidate_id": candidate.candidate_id,
                    **candidate.metadata,
                }
            )


def validate_proposed_candidates(
    campaign: CampaignManifest,
    proposed: Iterable[ProposedCandidate],
    *,
    registry_species_names: Iterable[str] | None = None,
) -> None:
    """Validate proposed candidate IDs against a campaign or optional registry names."""

    known_ids = {candidate.id for candidate in campaign.candidates}
    known_species = {
        candidate.species_name
        for candidate in campaign.candidates
        if candidate.species_name is not None
    }
    if registry_species_names is not None:
        known_species.update(registry_species_names)
    known = known_ids | known_species
    missing = [
        candidate.candidate_id
        for candidate in proposed
        if candidate.candidate_id not in known
    ]
    if missing:
        raise ValueError(
            "proposed candidate ID(s) are not present in campaign or registry: "
            + ", ".join(sorted(missing))
        )
