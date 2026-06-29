"""Quality-check table helpers for the dashboard."""

from __future__ import annotations

from collections import Counter
from typing import Any

from qchem_workbench.analysis.quality_checks import run_quality_checks
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.dashboard.data import DashboardData


def quality_summary_rows(data: DashboardData) -> list[dict[str, Any]]:
    checks = _quality_rows(data)
    counts = Counter(row["severity"] for row in checks)
    return [
        {"severity": severity, "count": counts.get(severity, 0)}
        for severity in ("error", "warning", "info")
    ]


def quality_check_rows(
    data: DashboardData,
    *,
    species: str | None = None,
    backend: str | None = None,
    code: str | None = None,
) -> list[dict[str, Any]]:
    rows = _quality_rows(data)
    if species:
        rows = [row for row in rows if row["species"] == species]
    if backend:
        rows = [row for row in rows if row["backend"] == backend]
    if code:
        rows = [row for row in rows if row["code"] == code]
    return rows


def failed_calculation_rows(data: DashboardData) -> list[dict[str, Any]]:
    rows = []
    for result in _result_rows(data):
        if result.get("success") is False:
            rows.append(
                {
                    "species": result.get("species_name"),
                    "backend": result.get("backend"),
                    "method": result.get("method"),
                    "basis": result.get("basis"),
                    "task": result.get("task"),
                    "source_path": result.get("source_path"),
                    "warnings": "; ".join(result.get("warnings", [])),
                }
            )
    return rows


def _quality_rows(data: DashboardData) -> list[dict[str, Any]]:
    results = [CalculationResult.from_dict(row) for row in _result_rows(data)]
    checks = run_quality_checks(results)
    return [
        {
            "severity": check.severity,
            "code": check.code,
            "species": _identifier_part(check.result_identifier, 0),
            "backend": _identifier_part(check.result_identifier, 2),
            "identifier": check.result_identifier,
            "message": check.message,
        }
        for check in checks
    ]


def _result_rows(data: DashboardData) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in data.loaded_sections:
        if section.kind == "result_store":
            rows.extend(section.rows)
    return rows


def _identifier_part(identifier: str, index: int) -> str:
    parts = identifier.split("|")
    if len(parts) <= index:
        return ""
    return parts[index]
