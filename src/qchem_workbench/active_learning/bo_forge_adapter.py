"""Optional Python adapter for BO Forge.

The file-based CSV/JSON interchange remains the stable integration path. This
module only provides a thin conversion layer when BO Forge is installed.
"""

from __future__ import annotations

import importlib
from typing import Any, Iterable

from qchem_workbench.active_learning.proposals import ProposedCandidate


class BOForgeUnavailableError(RuntimeError):
    """Raised when the optional BO Forge package is not installed."""


def to_bo_forge_dataset(
    rows: Iterable[dict[str, Any]],
    headers: Iterable[str],
) -> dict[str, Any]:
    """Convert qchem-workbench dataset rows into a BO Forge-ready dictionary."""

    bo_forge = _import_bo_forge()
    return {
        "format": "qchem_workbench_bo_forge_adapter",
        "bo_forge_module": bo_forge.__name__,
        "candidate_id_column": "candidate_id",
        "headers": tuple(headers),
        "rows": [dict(row) for row in rows],
    }


def from_bo_forge_proposals(proposals: Iterable[Any]) -> list[ProposedCandidate]:
    """Convert public proposal-like mappings/objects into qchem-workbench proposals."""

    _import_bo_forge()
    converted = []
    for proposal in proposals:
        data = _proposal_mapping(proposal)
        candidate_id = data.get("candidate_id") or data.get("id")
        if not candidate_id:
            raise ValueError("BO Forge proposal is missing candidate_id")
        converted.append(
            ProposedCandidate(
                candidate_id=str(candidate_id),
                proposal_rank=_optional_int(data.get("proposal_rank") or data.get("rank")),
                acquisition_value=_optional_float(data.get("acquisition_value")),
                proposed_by=_optional_str(data.get("proposed_by") or "bo_forge"),
                notes=_optional_str(data.get("notes")),
                metadata={
                    key: value
                    for key, value in data.items()
                    if key
                    not in {
                        "candidate_id",
                        "id",
                        "proposal_rank",
                        "rank",
                        "acquisition_value",
                        "proposed_by",
                        "notes",
                    }
                },
            )
        )
    return converted


def _import_bo_forge():
    try:
        return importlib.import_module("bo_forge")
    except ImportError as exc:
        raise BOForgeUnavailableError(
            "BO Forge is required for the optional Python adapter. "
            "Use qchemwb active-learning export-bo-forge for the stable "
            "file-based interchange path."
        ) from exc


def _proposal_mapping(proposal: Any) -> dict[str, Any]:
    if isinstance(proposal, dict):
        return dict(proposal)
    if hasattr(proposal, "to_dict"):
        value = proposal.to_dict()
        if isinstance(value, dict):
            return dict(value)
    return {
        key: getattr(proposal, key)
        for key in dir(proposal)
        if not key.startswith("_") and not callable(getattr(proposal, key))
    }


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
