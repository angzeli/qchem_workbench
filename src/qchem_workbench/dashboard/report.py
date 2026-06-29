"""Dashboard-assisted Markdown report export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qchem_workbench.core.result import CalculationResult
from qchem_workbench.dashboard.data import DashboardData
from qchem_workbench.dashboard.overview import (
    loaded_file_rows,
    missing_data_rows,
    overview_summary_rows,
)
from qchem_workbench.reports.markdown import generate_markdown_report


def generate_dashboard_markdown_report(
    data: DashboardData,
    *,
    title: str = "qchem-workbench dashboard report",
) -> str:
    """Generate a Markdown report from currently loaded dashboard data."""

    results = _calculation_results(data)
    if results:
        sections = [generate_markdown_report(results, title=title).rstrip()]
    else:
        sections = [
            f"# {_markdown_text(title)}",
            "No calculation result store was loaded.",
        ]
    sections.append(_dashboard_table("Dashboard overview", ["Item", "Value"], overview_summary_rows(data)))
    sections.append(
        _dashboard_table(
            "Loaded files",
            ["Label", "Path", "Status", "Message"],
            loaded_file_rows(data),
        )
    )
    missing_rows = missing_data_rows(data)
    if missing_rows:
        sections.append(
            _dashboard_table(
                "Missing data and warnings",
                ["Section", "Message"],
                missing_rows,
            )
        )
    sections.append(
        "## Dashboard caveats\n\n"
        "- This report summarizes loaded files only.\n"
        "- Missing values remain missing; no scientific quantities are inferred.\n"
        "- Dashboard views are for workflow review and do not validate calculations."
    )
    return "\n\n".join(sections).rstrip() + "\n"


def write_dashboard_markdown_report(
    path: Path,
    data: DashboardData,
    *,
    title: str = "qchem-workbench dashboard report",
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        generate_dashboard_markdown_report(data, title=title),
        encoding="utf-8",
    )


def _calculation_results(data: DashboardData) -> list[CalculationResult]:
    results = []
    for section in data.loaded_sections:
        if section.kind == "result_store":
            results.extend(CalculationResult.from_dict(row) for row in section.rows)
    return results


def _dashboard_table(title: str, headers: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"## {_markdown_text(title)}\n\nNo rows."
    table_rows = []
    for row in rows:
        table_rows.append([_format_value(row.get(_row_key(header))) for header in headers])
    header_line = "| " + " | ".join(_markdown_text(header) for header in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_markdown_text(value) for value in row) + " |"
        for row in table_rows
    ]
    return "\n".join([f"## {_markdown_text(title)}", "", header_line, separator, *body])


def _row_key(header: str) -> str:
    return header.lower().replace(" ", "_")


def _format_value(value: Any) -> str:
    if value in (None, ""):
        return "N/A"
    return str(value)


def _markdown_text(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
