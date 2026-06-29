"""File-based BO Forge interchange helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qchem_workbench.active_learning.datasets import ActiveLearningCampaign


BO_FORGE_INTERCHANGE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BOForgeExportSummary:
    output_dir: Path
    candidate_count: int
    observation_count: int
    objective_columns: tuple[str, ...]
    constraint_columns: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def export_bo_forge_interchange(
    campaign: ActiveLearningCampaign,
    dataset_rows: list[dict[str, str]],
    dataset_headers: list[str] | tuple[str, ...],
    output_dir: Path,
) -> BOForgeExportSummary:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    objective_columns = _objective_columns(dataset_headers)
    constraint_columns = _constraint_columns(dataset_headers)
    warnings = []
    if not objective_columns:
        warnings.append("no objective columns found; exported observations are pending-only")
    _write_candidates(campaign, out_dir / "bo_forge_candidates.csv")
    _write_observations(
        dataset_rows,
        dataset_headers,
        objective_columns,
        constraint_columns,
        out_dir / "bo_forge_observations.csv",
    )
    _write_metadata(
        campaign,
        objective_columns,
        constraint_columns,
        warnings,
        out_dir / "bo_forge_metadata.json",
    )
    return BOForgeExportSummary(
        output_dir=out_dir,
        candidate_count=len(campaign.candidate_registry.candidates),
        observation_count=len(dataset_rows),
        objective_columns=tuple(objective_columns),
        constraint_columns=tuple(constraint_columns),
        warnings=tuple(warnings),
    )


def _write_candidates(campaign: ActiveLearningCampaign, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "candidate_id",
                "candidate_type",
                "species",
                "structure",
                "system",
                "pathway",
                "status",
                "provenance",
            ],
        )
        writer.writeheader()
        for candidate in campaign.candidate_registry.candidates:
            writer.writerow(
                {
                    "candidate_id": candidate.id,
                    "candidate_type": candidate.type,
                    "species": candidate.species or "",
                    "structure": candidate.structure or "",
                    "system": candidate.system or "",
                    "pathway": candidate.pathway or "",
                    "status": candidate.metadata.get("status", "pending"),
                    "provenance": candidate.metadata.get("provenance", "qchem_workbench"),
                }
            )


def _write_observations(
    rows: list[dict[str, str]],
    headers: list[str] | tuple[str, ...],
    objective_columns: list[str],
    constraint_columns: list[str],
    path: Path,
) -> None:
    descriptor_columns = [
        column
        for column in headers
        if column
        not in {
            "candidate_id",
            "observed_status",
            "al_rank",
            "al_status",
            "al_score",
            "al_reasons",
            "provenance",
        }
        and not column.startswith("objective_")
        and not column.startswith("constraint_")
    ]
    fieldnames = [
        "candidate_id",
        "observed_status",
        *descriptor_columns,
        *objective_columns,
        *constraint_columns,
        "provenance",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            observed = any(row.get(column, "") not in ("", None) for column in objective_columns)
            writer.writerow(
                {
                    "candidate_id": row.get("candidate_id", ""),
                    "observed_status": "observed" if observed else "pending",
                    **{column: row.get(column, "") for column in descriptor_columns},
                    **{column: row.get(column, "") for column in objective_columns},
                    **{column: row.get(column, "") for column in constraint_columns},
                    "provenance": "qchem_workbench",
                }
            )


def _write_metadata(
    campaign: ActiveLearningCampaign,
    objective_columns: list[str],
    constraint_columns: list[str],
    warnings: list[str],
    path: Path,
) -> None:
    payload: dict[str, Any] = {
        "schema_version": BO_FORGE_INTERCHANGE_SCHEMA_VERSION,
        "format": "qchem_workbench_bo_forge_interchange",
        "campaign_name": campaign.name,
        "candidate_count": len(campaign.candidate_registry.candidates),
        "objective_columns": objective_columns,
        "constraint_columns": constraint_columns,
        "stable_path": "file_based_csv_json",
        "warnings": warnings,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _objective_columns(headers: list[str] | tuple[str, ...]) -> list[str]:
    columns = [
        column
        for column in headers
        if column == "al_score" or (column.startswith("objective_") and column.endswith("_value"))
    ]
    return columns


def _constraint_columns(headers: list[str] | tuple[str, ...]) -> list[str]:
    return [
        column
        for column in headers
        if column.startswith("constraint_") and column.endswith("_pass")
    ]
