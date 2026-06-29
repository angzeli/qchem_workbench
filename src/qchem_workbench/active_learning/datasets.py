"""Descriptor dataset builder for active-learning handoff workflows."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.active_learning.candidates import (
    ActiveLearningCandidate,
    CandidateRegistry,
    load_candidate_registry,
)
from qchem_workbench.analysis.quality_checks import run_quality_checks
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.results.store import load_result_collection


ACTIVE_LEARNING_DATASET_SCHEMA_VERSION = 1
DESCRIPTOR_SOURCE_TYPES = {
    "result_store",
    "adsorption_table",
    "che_table",
    "microkinetic_table",
    "property_export",
    "csv",
}


@dataclass(frozen=True)
class DescriptorSource:
    id: str
    type: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActiveLearningCampaign:
    name: str
    candidate_registry: CandidateRegistry
    descriptor_sources: tuple[DescriptorSource, ...]
    source_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DescriptorDataset:
    headers: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


def load_active_learning_campaign(path: Path) -> ActiveLearningCampaign:
    campaign_path = Path(path)
    data = yaml.safe_load(campaign_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{campaign_path}: active-learning campaign must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != ACTIVE_LEARNING_DATASET_SCHEMA_VERSION:
        raise ValueError(
            f"{campaign_path}: unsupported schema_version {schema_version!r}; "
            f"expected {ACTIVE_LEARNING_DATASET_SCHEMA_VERSION}"
        )
    raw_campaign = data.get("active_learning_campaign") or data.get("campaign")
    if not isinstance(raw_campaign, dict):
        raise ValueError(f"{campaign_path}: active_learning_campaign must be a mapping")
    candidates_path = _resolve_path(
        campaign_path,
        _required_string(raw_campaign, "candidates", "active_learning_campaign"),
        "active_learning_campaign.candidates",
    )
    sources = _descriptor_sources(campaign_path, raw_campaign.get("descriptor_sources", []))
    return ActiveLearningCampaign(
        name=_optional_string(raw_campaign, "name") or campaign_path.stem,
        candidate_registry=load_candidate_registry(candidates_path),
        descriptor_sources=sources,
        source_path=campaign_path,
        metadata=dict(raw_campaign.get("metadata", {}))
        if isinstance(raw_campaign.get("metadata", {}), dict)
        else {},
    )


def build_active_learning_dataset(campaign: ActiveLearningCampaign) -> DescriptorDataset:
    source_rows = [_load_source_rows(source) for source in campaign.descriptor_sources]
    rows = []
    for candidate in campaign.candidate_registry.candidates:
        row: dict[str, Any] = _base_candidate_row(candidate)
        row.update(_quality_defaults())
        for source, indexed in zip(campaign.descriptor_sources, source_rows):
            values, missing_reason = _candidate_source_values(candidate, source, indexed)
            row.update(values)
            row[f"missing_{source.id}_reason"] = missing_reason or ""
        rows.append(row)
    headers = _headers(rows)
    return DescriptorDataset(headers=headers, rows=tuple(rows))


def write_descriptor_dataset_csv(dataset: DescriptorDataset, path: Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dataset.headers))
        writer.writeheader()
        writer.writerows(dataset.rows)


def _descriptor_sources(path: Path, raw_sources: Any) -> tuple[DescriptorSource, ...]:
    if raw_sources in (None, ""):
        return ()
    if not isinstance(raw_sources, list):
        raise ValueError(f"{path}: descriptor_sources must be a list")
    seen: set[str] = set()
    sources = []
    for index, raw in enumerate(raw_sources):
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: descriptor_sources[{index}] must be a mapping")
        source_id = _required_string(raw, "id", f"descriptor_sources[{index}]")
        if source_id in seen:
            raise ValueError(f"{path}: duplicate descriptor source ID {source_id!r}")
        seen.add(source_id)
        source_type = _required_string(raw, "type", f"descriptor_sources[{index}]")
        if source_type not in DESCRIPTOR_SOURCE_TYPES:
            raise ValueError(f"{path}: unsupported descriptor source type {source_type!r}")
        source_path = _resolve_path(
            path,
            _required_string(raw, "path", f"descriptor_sources[{index}]"),
            f"descriptor_sources[{index}].path",
        )
        metadata = {
            key: value
            for key, value in raw.items()
            if key not in {"id", "type", "path"}
        }
        sources.append(
            DescriptorSource(
                id=source_id,
                type=source_type,
                path=source_path,
                metadata=metadata,
            )
        )
    return tuple(sources)


def _load_source_rows(source: DescriptorSource) -> dict[str, Any]:
    if source.type == "result_store":
        results = load_result_collection(source.path)
        checks = run_quality_checks(results)
        return {
            "type": source.type,
            "results_by_species": {result.species_name: result for result in results},
            "quality_by_species": _quality_by_species(checks),
        }
    rows = _read_csv_dicts(source.path)
    return {"type": source.type, "rows": rows}


def _candidate_source_values(
    candidate: ActiveLearningCandidate,
    source: DescriptorSource,
    indexed: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    if source.type == "result_store":
        return _result_values(candidate, source, indexed)
    match = _matching_csv_row(candidate, indexed["rows"], source.type)
    if match is None:
        return {}, f"missing_{source.type}_row"
    prefix = source.id
    values = {
        f"{prefix}_{key}": value
        for key, value in match.items()
        if key not in _identifier_columns(source.type)
    }
    values[f"{prefix}_source_path"] = str(source.path)
    return values, None


def _result_values(
    candidate: ActiveLearningCandidate,
    source: DescriptorSource,
    indexed: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    results_by_species: dict[str, CalculationResult] = indexed["results_by_species"]
    result = None
    for key in _candidate_match_keys(candidate):
        result = results_by_species.get(key)
        if result is not None:
            break
    if result is None:
        return {}, "missing_result"
    prefix = source.id
    values: dict[str, Any] = {
        f"{prefix}_species_name": result.species_name,
        f"{prefix}_backend": result.backend,
        f"{prefix}_method": result.method or "",
        f"{prefix}_basis": result.basis or "",
        f"{prefix}_task": result.task or "",
        f"{prefix}_success": result.success,
        f"{prefix}_electronic_energy_hartree": result.electronic_energy_hartree,
        f"{prefix}_gibbs_free_energy_hartree": result.gibbs_free_energy_hartree,
        f"{prefix}_homo_ev": result.homo_ev,
        f"{prefix}_lumo_ev": result.lumo_ev,
        f"{prefix}_gap_ev": result.gap_ev,
        f"{prefix}_source_path": str(result.source_path) if result.source_path else str(source.path),
    }
    quality = indexed["quality_by_species"].get(result.species_name, [])
    values.update(_quality_columns(quality, result))
    return values, None


def _base_candidate_row(candidate: ActiveLearningCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.id,
        "candidate_type": candidate.type,
        "species": candidate.species or "",
        "structure": candidate.structure or "",
        "system": candidate.system or "",
        "pathway": candidate.pathway or "",
    }


def _quality_defaults() -> dict[str, Any]:
    return {
        "quality_error_count": 0,
        "quality_warning_count": 0,
        "quality_info_count": 0,
        "quality_flags": "",
    }


def _quality_columns(checks, result: CalculationResult) -> dict[str, Any]:
    flags = [check.code for check in checks]
    if result.warnings:
        flags.append("parser_warning")
    return {
        "quality_error_count": sum(1 for check in checks if check.severity == "error"),
        "quality_warning_count": sum(1 for check in checks if check.severity == "warning")
        + (1 if result.warnings else 0),
        "quality_info_count": sum(1 for check in checks if check.severity == "info"),
        "quality_flags": ";".join(flags),
    }


def _quality_by_species(checks) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = {}
    for check in checks:
        species_name = str(check.result_identifier).split("|", 1)[0]
        grouped.setdefault(species_name, []).append(check)
    return grouped


def _matching_csv_row(
    candidate: ActiveLearningCandidate,
    rows: list[dict[str, str]],
    source_type: str,
) -> dict[str, str] | None:
    keys = _candidate_match_keys(candidate)
    columns = _identifier_columns(source_type)
    for row in rows:
        for column in columns:
            value = row.get(column, "")
            if value and value in keys:
                return row
    return None


def _candidate_match_keys(candidate: ActiveLearningCandidate) -> set[str]:
    return {
        key
        for key in (
            candidate.id,
            candidate.species,
            candidate.system,
            candidate.pathway,
            candidate.structure,
        )
        if key
    }


def _identifier_columns(source_type: str) -> tuple[str, ...]:
    if source_type == "adsorption_table":
        return ("candidate_id", "system_id", "id")
    if source_type == "che_table":
        return ("candidate_id", "reaction_id", "id")
    if source_type == "microkinetic_table":
        return ("candidate_id", "id", "species", "observable")
    return ("candidate_id", "species_name", "species", "system_id", "reaction_id", "id")


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _headers(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    preferred = [
        "candidate_id",
        "candidate_type",
        "species",
        "structure",
        "system",
        "pathway",
        "quality_error_count",
        "quality_warning_count",
        "quality_info_count",
        "quality_flags",
    ]
    headers = []
    for header in preferred:
        if any(header in row for row in rows):
            headers.append(header)
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)
    return tuple(headers)


def _resolve_path(path: Path, value: str, label: str) -> Path:
    if not value.strip():
        raise ValueError(f"{path}: {label} must be a non-empty path")
    resolved = Path(value)
    if not resolved.is_absolute():
        resolved = path.parent / resolved
    return resolved


def _required_string(data: dict[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return value.strip()


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string when provided")
    return value.strip()
