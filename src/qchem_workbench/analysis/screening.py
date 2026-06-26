"""Screening campaign descriptor table utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qchem_workbench.analysis.adsorption import AdsorptionEnergyRow
from qchem_workbench.analysis.quality_checks import QualityCheck
from qchem_workbench.analysis.reactions import ReactionEnergyRow
from qchem_workbench.campaigns import CampaignCandidate, CampaignManifest, RankingRule
from qchem_workbench.core.result import CalculationResult


BASE_DESCRIPTOR_HEADERS = [
    "candidate_id",
    "species_name",
    "structure_path",
]
QUALITY_DESCRIPTOR_HEADERS = [
    "quality_error_count",
    "quality_warning_count",
    "quality_info_count",
    "quality_flags",
]


@dataclass(frozen=True)
class DescriptorTable:
    """CSV-ready descriptor table for a screening campaign."""

    headers: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class RankedCandidateTable:
    """CSV-ready ranked candidate table with visible score components."""

    headers: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


def build_descriptor_table(
    campaign: CampaignManifest,
    results: list[CalculationResult],
    *,
    quality_checks: list[QualityCheck] | None = None,
    reaction_rows: list[ReactionEnergyRow] | None = None,
    adsorption_rows: list[AdsorptionEnergyRow] | None = None,
) -> DescriptorTable:
    """Build a descriptor table from explicit campaign descriptor definitions."""

    descriptor_names = tuple(descriptor.name for descriptor in campaign.descriptors)
    headers = (
        *BASE_DESCRIPTOR_HEADERS,
        *descriptor_names,
        *QUALITY_DESCRIPTOR_HEADERS,
    )
    result_by_species = _result_by_species(results)
    quality_by_candidate = _quality_by_candidate(
        campaign.candidates,
        results,
        quality_checks or [],
    )
    rows = []
    for candidate in campaign.candidates:
        result = _candidate_result(candidate, result_by_species)
        row: dict[str, Any] = {
            "candidate_id": candidate.id,
            "species_name": candidate.species_name or "",
            "structure_path": str(candidate.structure_path)
            if candidate.structure_path is not None
            else "",
        }
        for descriptor in campaign.descriptors:
            row[descriptor.name] = _descriptor_value(
                descriptor_source=descriptor.source,
                descriptor_field=descriptor.field or descriptor.name,
                descriptor_reference=descriptor.reference,
                candidate=candidate,
                result=result,
                reaction_rows=reaction_rows or [],
                adsorption_rows=adsorption_rows or [],
            )
        row.update(_quality_columns(quality_by_candidate.get(candidate.id, []), result))
        rows.append(row)
    return DescriptorTable(headers=tuple(headers), rows=tuple(rows))


def write_descriptor_table_csv(path: Path, table: DescriptorTable) -> None:
    """Write a descriptor table CSV."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table.headers))
        writer.writeheader()
        writer.writerows(table.rows)


def rank_descriptor_table(
    campaign: CampaignManifest,
    table: DescriptorTable,
) -> RankedCandidateTable:
    """Apply explicit ranking rules to a descriptor table."""

    return rank_descriptor_rows(campaign, table.rows, table.headers)


def rank_descriptor_rows(
    campaign: CampaignManifest,
    rows: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    headers: tuple[str, ...] | list[str] | None = None,
) -> RankedCandidateTable:
    """Rank descriptor rows using transparent campaign ranking rules."""

    original_headers = tuple(headers or _headers_from_rows(rows))
    score_rules = tuple(rule for rule in campaign.ranking_rules if rule.direction)
    component_headers = tuple(
        f"score_component_{rule.descriptor}" for rule in score_rules
    )
    ranked_headers = (
        "rank",
        "rank_status",
        "rank_score",
        "ranking_reasons",
        *component_headers,
        *original_headers,
    )

    evaluated = [_evaluate_ranking_row(row, campaign.ranking_rules) for row in rows]
    complete = [item for item in evaluated if item["status"] == "ranked"]
    complete.sort(
        key=lambda item: (
            -float(item["score"]),
            str(item["row"].get("candidate_id", "")),
        )
    )
    _assign_ranks(complete)

    excluded = [item for item in evaluated if item["status"] != "ranked"]
    output_rows = [
        _ranked_output_row(item, original_headers, component_headers)
        for item in [*complete, *excluded]
    ]
    return RankedCandidateTable(headers=ranked_headers, rows=tuple(output_rows))


def write_ranked_candidates_csv(path: Path, table: RankedCandidateTable) -> None:
    """Write ranked candidate rows to CSV."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table.headers))
        writer.writeheader()
        writer.writerows(table.rows)


def _result_by_species(
    results: list[CalculationResult],
) -> dict[str, CalculationResult]:
    return {result.species_name: result for result in results}


def _candidate_result(
    candidate: CampaignCandidate,
    result_by_species: dict[str, CalculationResult],
) -> CalculationResult | None:
    if candidate.species_name is not None:
        result = result_by_species.get(candidate.species_name)
        if result is not None:
            return result
    return result_by_species.get(candidate.id)


def _descriptor_value(
    *,
    descriptor_source: str,
    descriptor_field: str,
    descriptor_reference: str | None,
    candidate: CampaignCandidate,
    result: CalculationResult | None,
    reaction_rows: list[ReactionEnergyRow],
    adsorption_rows: list[AdsorptionEnergyRow],
) -> object | None:
    if descriptor_source in {"result", "result_field"}:
        if result is None:
            return None
        return _result_field(result, descriptor_field)
    if descriptor_source == "reaction":
        row = _reaction_row(reaction_rows, descriptor_reference or candidate.id)
        return getattr(row, descriptor_field, None) if row is not None else None
    if descriptor_source == "adsorption":
        row = _adsorption_row(adsorption_rows, descriptor_reference or candidate.id)
        return getattr(row, descriptor_field, None) if row is not None else None
    if descriptor_source == "quality":
        return None
    raise ValueError(f"unsupported descriptor source {descriptor_source!r}")


def _result_field(result: CalculationResult, field_name: str) -> object | None:
    aliases = {
        "electronic_energy": "electronic_energy_hartree",
        "gibbs_free_energy": "gibbs_free_energy_hartree",
        "homo": "homo_ev",
        "lumo": "lumo_ev",
        "gap": "gap_ev",
    }
    attr = aliases.get(field_name, field_name)
    if not hasattr(result, attr):
        raise ValueError(f"unsupported result descriptor field {field_name!r}")
    return getattr(result, attr)


def _reaction_row(
    rows: list[ReactionEnergyRow],
    reaction_id: str,
) -> ReactionEnergyRow | None:
    return next((row for row in rows if row.reaction_id == reaction_id), None)


def _adsorption_row(
    rows: list[AdsorptionEnergyRow],
    system_id: str,
) -> AdsorptionEnergyRow | None:
    return next((row for row in rows if row.system_id == system_id), None)


def _quality_by_candidate(
    candidates: tuple[CampaignCandidate, ...],
    results: list[CalculationResult],
    checks: list[QualityCheck],
) -> dict[str, list[QualityCheck]]:
    result_by_species = _result_by_species(results)
    quality_by_id: dict[str, list[QualityCheck]] = {candidate.id: [] for candidate in candidates}
    for candidate in candidates:
        names = {candidate.id}
        if candidate.species_name is not None:
            names.add(candidate.species_name)
        result = _candidate_result(candidate, result_by_species)
        if result is not None:
            names.add(result.species_name)
        for check in checks:
            if any(
                check.result_identifier == name
                or check.result_identifier.startswith(f"{name}|")
                for name in names
            ):
                quality_by_id[candidate.id].append(check)
    return quality_by_id


def _quality_columns(
    checks: list[QualityCheck],
    result: CalculationResult | None,
) -> dict[str, object]:
    flags = [check.code for check in checks]
    if result is not None and result.warnings:
        flags.append("parser_warning")
    return {
        "quality_error_count": sum(1 for check in checks if check.severity == "error"),
        "quality_warning_count": sum(
            1 for check in checks if check.severity == "warning"
        )
        + (1 if result is not None and result.warnings else 0),
        "quality_info_count": sum(1 for check in checks if check.severity == "info"),
        "quality_flags": ";".join(flags),
    }


def _headers_from_rows(rows: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> tuple[str, ...]:
    headers: list[str] = []
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)
    return tuple(headers)


def _evaluate_ranking_row(
    row: dict[str, Any],
    rules: tuple[RankingRule, ...],
) -> dict[str, Any]:
    reasons: list[str] = []
    components: dict[str, float | None] = {}
    score = 0.0
    for rule in rules:
        if rule.filter:
            _apply_filter_rule(row, rule, reasons)

        if rule.minimum is not None or rule.maximum is not None:
            value = _numeric_descriptor(row, rule.descriptor)
            if value is None:
                reasons.append(f"missing_descriptor:{rule.descriptor}")
            else:
                if rule.minimum is not None and value < rule.minimum:
                    reasons.append(f"below_minimum:{rule.descriptor}")
                if rule.maximum is not None and value > rule.maximum:
                    reasons.append(f"above_maximum:{rule.descriptor}")

        if rule.direction:
            value = _numeric_descriptor(row, rule.descriptor)
            component_key = f"score_component_{rule.descriptor}"
            if value is None:
                components[component_key] = None
                if not rule.allow_missing:
                    reasons.append(f"missing_descriptor:{rule.descriptor}")
                continue
            direction = _ranking_direction(rule.direction)
            weight = 1.0 if rule.weight is None else rule.weight
            component = value * weight if direction == "maximize" else -value * weight
            components[component_key] = component
            score += component

    unique_reasons = tuple(dict.fromkeys(reasons))
    return {
        "row": row,
        "rank": None,
        "status": "excluded" if unique_reasons else "ranked",
        "score": None if unique_reasons else score,
        "reasons": unique_reasons,
        "components": components,
    }


def _apply_filter_rule(
    row: dict[str, Any],
    rule: RankingRule,
    reasons: list[str],
) -> None:
    if rule.filter in {"exclude_quality_errors", "no_quality_errors"}:
        errors = _numeric_descriptor(row, "quality_error_count")
        if errors is not None and errors > 0:
            reasons.append("quality_errors_present")
        return
    if rule.filter in {"exclude_quality_warnings", "no_quality_warnings"}:
        warnings = _numeric_descriptor(row, "quality_warning_count")
        if warnings is not None and warnings > 0:
            reasons.append("quality_warnings_present")
        return
    raise ValueError(f"unsupported ranking filter {rule.filter!r}")


def _ranking_direction(direction: str) -> str:
    normalized = direction.strip().lower()
    aliases = {
        "max": "maximize",
        "maximize": "maximize",
        "maximise": "maximize",
        "min": "minimize",
        "minimize": "minimize",
        "minimise": "minimize",
    }
    if normalized not in aliases:
        raise ValueError(f"unsupported ranking direction {direction!r}")
    return aliases[normalized]


def _numeric_descriptor(row: dict[str, Any], descriptor: str) -> float | None:
    value = row.get(descriptor)
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None


def _assign_ranks(evaluated_rows: list[dict[str, Any]]) -> None:
    previous_score: float | None = None
    previous_rank = 0
    for index, item in enumerate(evaluated_rows, start=1):
        score = float(item["score"])
        if previous_score is not None and score == previous_score:
            item["rank"] = previous_rank
        else:
            item["rank"] = index
            previous_rank = index
            previous_score = score


def _ranked_output_row(
    item: dict[str, Any],
    original_headers: tuple[str, ...],
    component_headers: tuple[str, ...],
) -> dict[str, Any]:
    source_row = item["row"]
    output = {
        "rank": item["rank"] if item["rank"] is not None else "",
        "rank_status": item["status"],
        "rank_score": item["score"] if item["score"] is not None else "",
        "ranking_reasons": ";".join(item["reasons"]),
    }
    for header in component_headers:
        component = item["components"].get(header)
        output[header] = "" if component is None else component
    for header in original_headers:
        output[header] = source_row.get(header, "")
    return output
