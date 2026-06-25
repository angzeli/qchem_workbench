"""Failed-job triage report generation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from qchem_workbench.core.result import CalculationResult


MISSING = "N/A"


@dataclass(frozen=True)
class TriageCategory:
    code: str
    title: str
    suggestion: str


TRIAGE_CATEGORIES = (
    TriageCategory(
        code="complete",
        title="Complete",
        suggestion="No triage action is suggested from stored result fields.",
    ),
    TriageCategory(
        code="incomplete_no_normal_termination",
        title="Incomplete/no normal termination",
        suggestion=(
            "Inspect the source output and job logs. Do not treat the calculation "
            "as complete until the termination state is understood."
        ),
    ),
    TriageCategory(
        code="missing_energy",
        title="Missing energy",
        suggestion=(
            "Inspect the source output and parser warnings. Do not substitute or "
            "estimate missing energy values."
        ),
    ),
    TriageCategory(
        code="imaginary_frequencies",
        title="Imaginary frequencies",
        suggestion=(
            "Review the parsed frequency information and structure. No transition-"
            "state identity is inferred by this report."
        ),
    ),
    TriageCategory(
        code="spin_warning",
        title="Spin warning",
        suggestion=(
            "Review spin metadata and expected multiplicity when available. This "
            "report does not decide whether the result is usable."
        ),
    ),
    TriageCategory(
        code="parser_warning",
        title="Parser warning",
        suggestion=(
            "Inspect parser warnings and the source file. Missing parsed values "
            "remain missing."
        ),
    ),
)


def classify_triage_results(
    results: Iterable[CalculationResult],
) -> dict[str, list[CalculationResult]]:
    """Classify results into conservative triage categories."""

    classified = {category.code: [] for category in TRIAGE_CATEGORIES}
    for result in results:
        issue_codes = _result_issue_codes(result)
        if not issue_codes:
            classified["complete"].append(result)
            continue
        for code in issue_codes:
            classified[code].append(result)
    return classified


def generate_failed_jobs_markdown(results: Iterable[CalculationResult]) -> str:
    """Return a Markdown failed-job triage report."""

    result_list = list(results)
    classified = classify_triage_results(result_list)
    sections = [
        "# Failed job triage",
        (
            "This report summarizes stored calculation results and parser metadata. "
            "It does not infer missing scientific quantities or prescribe fixes."
        ),
        _summary_table(classified),
    ]
    for category in TRIAGE_CATEGORIES:
        sections.append(_category_section(category, classified[category.code]))
    return "\n\n".join(sections).rstrip() + "\n"


def write_failed_jobs_report(
    path: Path, results: Iterable[CalculationResult]
) -> None:
    """Write a failed-job triage report to *path*."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_failed_jobs_markdown(results), encoding="utf-8")


def _result_issue_codes(result: CalculationResult) -> tuple[str, ...]:
    codes = []
    if _is_incomplete(result):
        codes.append("incomplete_no_normal_termination")
    if result.electronic_energy_hartree is None:
        codes.append("missing_energy")
    if _negative_frequency_count(result) > 0:
        codes.append("imaginary_frequencies")
    if _has_spin_warning(result):
        codes.append("spin_warning")
    if result.warnings:
        codes.append("parser_warning")
    return tuple(codes)


def _is_incomplete(result: CalculationResult) -> bool:
    if not result.success:
        return True
    if result.metadata.get("normal_termination") is False:
        return True
    return result.metadata.get("error_termination") is True


def _negative_frequency_count(result: CalculationResult) -> int:
    value = result.metadata.get("negative_frequency_count")
    if isinstance(value, int):
        return value
    return 0


def _has_spin_warning(result: CalculationResult) -> bool:
    if result.metadata.get("possible_spin_contamination") is True:
        return True
    return any(
        "spin" in warning.lower() or "s**2" in warning.lower()
        for warning in result.warnings
    )


def _summary_table(classified: dict[str, list[CalculationResult]]) -> str:
    rows = [
        (category.title, len(classified[category.code]))
        for category in TRIAGE_CATEGORIES
    ]
    return "## Summary\n\n" + _markdown_table(["Category", "Count"], rows)


def _category_section(
    category: TriageCategory, results: list[CalculationResult]
) -> str:
    lines = [f"## {category.title}", category.suggestion]
    if not results:
        lines.append("No results in this category.")
        return "\n\n".join(lines)

    rows = [
        (
            result.species_name,
            result.backend,
            result.method,
            result.basis,
            result.task,
            result.success,
            _format_number(result.electronic_energy_hartree),
            _source_path(result),
            len(result.warnings),
        )
        for result in results
    ]
    lines.append(
        _markdown_table(
            [
                "Species",
                "Backend",
                "Method",
                "Basis",
                "Task",
                "Success",
                "Electronic energy (Hartree)",
                "Source path",
                "Warnings",
            ],
            rows,
        )
    )
    return "\n\n".join(lines)


def _markdown_table(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    header_line = "| " + " | ".join(_markdown_text(header) for header in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = [
        "| " + " | ".join(_markdown_text(_format_value(value)) for value in row) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator, *row_lines])


def _format_value(value: object) -> str:
    if value is None:
        return MISSING
    if isinstance(value, str) and value == "":
        return MISSING
    return str(value)


def _format_number(value: float | None) -> str:
    if value is None:
        return MISSING
    return f"{value:.12g}"


def _source_path(result: CalculationResult) -> str:
    if result.source_path is None:
        return MISSING
    return str(result.source_path)


def _markdown_text(value: object) -> str:
    text = _format_value(value)
    return text.replace("|", "\\|").replace("\n", "<br>")
