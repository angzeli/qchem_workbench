"""Overview table helpers for the dashboard."""

from __future__ import annotations

from collections import Counter
from typing import Any

from qchem_workbench.dashboard.data import DashboardData


def overview_summary_rows(data: DashboardData) -> list[dict[str, Any]]:
    """Return high-level project summary rows."""

    return [
        {"item": "Project name", "value": data.project_name or "N/A"},
        {"item": "Loaded files", "value": len(data.file_provenance)},
        {"item": "Species count", "value": _species_count(data)},
        {"item": "Result count", "value": _result_count(data)},
        {"item": "Missing sections", "value": len(data.missing_sections)},
        {"item": "Dashboard warnings", "value": len(data.warnings)},
    ]


def loaded_file_rows(data: DashboardData) -> list[dict[str, Any]]:
    return [item.to_dict() for item in data.file_provenance]


def backend_method_basis_rows(data: DashboardData) -> list[dict[str, Any]]:
    counts = Counter()
    for result in _result_rows(data):
        key = (
            result.get("backend") or "N/A",
            result.get("method") or "N/A",
            result.get("basis") or "N/A",
            result.get("task") or "N/A",
        )
        counts[key] += 1
    return [
        {
            "backend": backend,
            "method": method,
            "basis": basis,
            "task": task,
            "count": count,
        }
        for (backend, method, basis, task), count in sorted(counts.items())
    ]


def missing_data_rows(data: DashboardData) -> list[dict[str, Any]]:
    rows = [{"section": section, "message": "Optional section was not loaded"} for section in data.missing_sections]
    rows.extend({"section": "warning", "message": warning} for warning in data.warnings)
    return rows


def _species_count(data: DashboardData) -> int:
    section = data.section("species")
    return len(section.rows) if section is not None else 0


def _result_count(data: DashboardData) -> int:
    return len(_result_rows(data))


def _result_rows(data: DashboardData) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in data.loaded_sections:
        if section.kind == "result_store":
            rows.extend(section.rows)
    return rows
