"""Markdown report generation for qchem-workbench result collections."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

from qchem_workbench.analysis.quality_checks import QualityCheck
from qchem_workbench.analysis.reactions import ReactionEnergyRow
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species


MISSING = "N/A"


def generate_markdown_report(
    results: Iterable[CalculationResult],
    *,
    species: Iterable[Species] | None = None,
    quality_checks: Iterable[QualityCheck] | None = None,
    reaction_rows: Iterable[ReactionEnergyRow] | None = None,
    title: str = "qchem-workbench report",
) -> str:
    """Return a GitHub-readable Markdown report.

    The report summarizes stored workflow data only. It does not infer missing
    scientific quantities or apply thermochemical/reaction corrections.
    """

    result_list = list(results)
    species_list = list(species) if species is not None else None
    check_list = list(quality_checks or [])
    reaction_row_list = list(reaction_rows or [])

    sections = [
        f"# {_markdown_text(title)}",
        _project_summary(result_list, species_list, check_list, reaction_row_list),
    ]
    if species_list is not None:
        sections.append(_species_table(species_list))
    sections.append(_result_table(result_list))
    sections.append(_quality_check_summary(check_list))
    if reaction_row_list:
        sections.append(_reaction_energy_table(reaction_row_list))
    sections.append(_method_provenance_summary(result_list, reaction_row_list))
    return "\n\n".join(sections).rstrip() + "\n"


def write_markdown_report(
    path: Path,
    results: Iterable[CalculationResult],
    *,
    species: Iterable[Species] | None = None,
    quality_checks: Iterable[QualityCheck] | None = None,
    reaction_rows: Iterable[ReactionEnergyRow] | None = None,
    title: str = "qchem-workbench report",
) -> None:
    """Write a Markdown report to *path*."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        generate_markdown_report(
            results,
            species=species,
            quality_checks=quality_checks,
            reaction_rows=reaction_rows,
            title=title,
        ),
        encoding="utf-8",
    )


def _project_summary(
    results: list[CalculationResult],
    species: list[Species] | None,
    checks: list[QualityCheck],
    reaction_rows: list[ReactionEnergyRow],
) -> str:
    counts = Counter(check.severity for check in checks)
    rows = [
        ("Species in registry", _format_value(len(species)) if species is not None else MISSING),
        ("Calculation results", _format_value(len(results))),
        ("Reaction rows", _format_value(len(reaction_rows))),
        ("Quality errors", _format_value(counts.get("error", 0))),
        ("Quality warnings", _format_value(counts.get("warning", 0))),
        ("Quality info", _format_value(counts.get("info", 0))),
    ]
    return "## Project summary\n\n" + _markdown_table(["Item", "Value"], rows)


def _species_table(species: list[Species]) -> str:
    rows = [
        (
            item.name,
            item.formula,
            item.charge,
            item.multiplicity,
            str(item.geometry_path),
            ", ".join(item.tags),
            item.notes,
        )
        for item in species
    ]
    return "## Species table\n\n" + _markdown_table(
        ["Name", "Formula", "Charge", "Multiplicity", "Geometry path", "Tags", "Notes"],
        rows,
    )


def _result_table(results: list[CalculationResult]) -> str:
    rows = [
        (
            result.species_name,
            result.backend,
            result.method,
            result.basis,
            result.task,
            result.success,
            _format_number(result.electronic_energy_hartree),
            _format_number(result.gibbs_free_energy_hartree),
            _format_number(result.zero_point_correction_hartree),
            _format_number(result.thermal_correction_gibbs_hartree),
            _format_number(result.homo_ev),
            _format_number(result.lumo_ev),
            _format_number(result.gap_ev),
            len(result.warnings),
        )
        for result in results
    ]
    return "## Calculation result table\n\n" + _markdown_table(
        [
            "Species",
            "Backend",
            "Method",
            "Basis",
            "Task",
            "Success",
            "Electronic energy (Hartree)",
            "Gibbs free energy (Hartree)",
            "Zero-point correction (Hartree)",
            "Thermal correction to Gibbs (Hartree)",
            "HOMO (eV)",
            "LUMO (eV)",
            "Gap (eV)",
            "Warnings",
        ],
        rows,
    )


def _quality_check_summary(checks: list[QualityCheck]) -> str:
    if not checks:
        return "## Quality-check summary\n\nNo quality checks reported."

    counts = Counter(check.severity for check in checks)
    summary = _markdown_table(
        ["Severity", "Count"],
        [(severity, counts.get(severity, 0)) for severity in ("error", "warning", "info")],
    )
    rows = [
        (check.severity, check.code, check.result_identifier, check.message)
        for check in checks
    ]
    details = _markdown_table(["Severity", "Code", "Identifier", "Message"], rows)
    return f"## Quality-check summary\n\n{summary}\n\n{details}"


def _reaction_energy_table(rows: list[ReactionEnergyRow]) -> str:
    table_rows = [
        (
            row.reaction_id,
            row.label,
            row.quantity,
            row.complete,
            _format_number(row.delta_hartree),
            _format_number(row.delta_ev),
            _format_number(row.delta_kj_mol),
            ", ".join(row.missing_species),
            row.notes,
        )
        for row in rows
    ]
    return "## Reaction energy table\n\n" + _markdown_table(
        [
            "Reaction ID",
            "Label",
            "Quantity",
            "Complete",
            "Delta (Hartree)",
            "Delta (eV)",
            "Delta (kJ/mol)",
            "Missing species",
            "Notes",
        ],
        table_rows,
    )


def _method_provenance_summary(
    results: list[CalculationResult], reaction_rows: list[ReactionEnergyRow]
) -> str:
    groups: dict[tuple[str, str, str, str, str], list[CalculationResult]] = {}
    for result in results:
        key = (
            result.backend,
            result.method or MISSING,
            result.basis or MISSING,
            result.task or MISSING,
            _metadata_value(result, "solvent"),
        )
        groups.setdefault(key, []).append(result)

    rows = []
    for (backend, method, basis, task, solvent), group in sorted(groups.items()):
        source_paths = sorted(
            str(result.source_path) for result in group if result.source_path is not None
        )
        rows.append(
            (
                backend,
                method,
                basis,
                task,
                solvent,
                len(group),
                "; ".join(source_paths) if source_paths else MISSING,
            )
        )
    if not rows:
        rows = [(MISSING, MISSING, MISSING, MISSING, MISSING, 0, MISSING)]

    warnings = _method_consistency_warnings(results, reaction_rows)
    warning_text = (
        "No method/provenance consistency warnings."
        if not warnings
        else _markdown_table(["Warning"], [(warning,) for warning in warnings])
    )
    table = _markdown_table(
        ["Backend", "Method", "Basis", "Task", "Solvent", "Result count", "Source paths"],
        rows,
    )
    return f"## Method/provenance summary\n\n{warning_text}\n\n{table}"


def _method_consistency_warnings(
    results: list[CalculationResult], reaction_rows: list[ReactionEnergyRow]
) -> list[str]:
    warnings = []
    if len(_distinct_values(results, "backend")) > 1:
        warnings.append("Multiple backends are present in the result set.")
    if len(_distinct_values(results, "method")) > 1:
        warnings.append("Multiple methods are present in the result set.")
    if len(_distinct_values(results, "basis")) > 1:
        warnings.append("Multiple basis sets are present in the result set.")
    if reaction_rows and len(_backend_method_basis_groups(results)) > 1:
        warnings.append(
            "Reaction rows are shown with mixed backend/method/basis results; "
            "verify each row was computed from a consistent result subset."
        )
    return warnings


def _distinct_values(results: list[CalculationResult], field_name: str) -> set[str]:
    return {
        str(getattr(result, field_name) or MISSING)
        for result in results
    }


def _backend_method_basis_groups(
    results: list[CalculationResult],
) -> set[tuple[str, str, str]]:
    return {
        (result.backend, result.method or MISSING, result.basis or MISSING)
        for result in results
    }


def _metadata_value(result: CalculationResult, key: str) -> str:
    value = result.metadata.get(key)
    if value is None or value == "":
        return MISSING
    return str(value)


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


def _markdown_text(value: object) -> str:
    text = _format_value(value)
    return text.replace("|", "\\|").replace("\n", "<br>")
