"""Reaction, adsorption, and CHE dashboard table helpers."""

from __future__ import annotations

from typing import Any

from qchem_workbench.dashboard.data import DashboardData


def reaction_energy_rows(data: DashboardData) -> list[dict[str, Any]]:
    return _rows_for_kind(data, "pathway_table")


def adsorption_energy_rows(data: DashboardData) -> list[dict[str, Any]]:
    return _rows_for_kind(data, "adsorption_table")


def che_energy_rows(data: DashboardData) -> list[dict[str, Any]]:
    return _rows_for_kind(data, "che_table")


def incomplete_analysis_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("complete", "")).lower() != "true"]


def che_correction_display_rows(data: DashboardData) -> list[dict[str, Any]]:
    rows = []
    for row in che_energy_rows(data):
        rows.append(
            {
                "reaction_id": row.get("reaction_id"),
                "correction_total_eV": row.get("correction_total_eV"),
                "correction_terms": row.get("correction_terms"),
                "warnings": row.get("warnings"),
            }
        )
    return rows


def method_consistency_warnings(
    rows: list[dict[str, Any]],
    *,
    label: str,
) -> list[dict[str, str]]:
    settings = {
        (
            row.get("backend", ""),
            row.get("method", ""),
            row.get("basis", ""),
        )
        for row in rows
        if row.get("backend") or row.get("method") or row.get("basis")
    }
    if len(settings) <= 1:
        return []
    return [
        {
            "scope": label,
            "warning": "Table contains mixed backend/method/basis values.",
            "settings": "; ".join(
                "/".join(value or "N/A" for value in setting)
                for setting in sorted(settings)
            ),
        }
    ]


def _rows_for_kind(data: DashboardData, kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in data.loaded_sections:
        if section.kind == kind:
            rows.extend(section.rows)
    return rows
