"""Markdown report generation for qchem-workbench result collections."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

from qchem_workbench.analysis.adsorption import AdsorptionEnergyRow
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
    adsorption_rows: Iterable[AdsorptionEnergyRow] | None = None,
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
    adsorption_row_list = list(adsorption_rows or [])

    sections = [
        f"# {_markdown_text(title)}",
        _project_summary(
            result_list,
            species_list,
            check_list,
            reaction_row_list,
            adsorption_row_list,
        ),
    ]
    if species_list is not None:
        sections.append(_species_table(species_list))
    sections.append(_result_table(result_list))
    sections.append(_quality_check_summary(check_list))
    if reaction_row_list:
        sections.append(_reaction_energy_table(reaction_row_list))
    if adsorption_row_list:
        sections.append(_adsorption_system_summary(adsorption_row_list, result_list))
        sections.append(_adsorption_energy_table(adsorption_row_list))
    if _has_vibrational_data(result_list):
        sections.append(_vibrational_summary(result_list))
    if _has_imaginary_frequencies(result_list):
        sections.append(_imaginary_frequency_summary(result_list))
    if _has_excitation_data(result_list):
        sections.append(_excitation_summary(result_list))
    if _has_orbital_data(result_list):
        sections.append(_orbital_summary(result_list))
    if _property_plot_rows(result_list):
        sections.append(_property_plot_links(result_list))
    sections.append(
        _method_provenance_summary(
            result_list,
            reaction_row_list,
            adsorption_row_list,
        )
    )
    return "\n\n".join(sections).rstrip() + "\n"


def write_markdown_report(
    path: Path,
    results: Iterable[CalculationResult],
    *,
    species: Iterable[Species] | None = None,
    quality_checks: Iterable[QualityCheck] | None = None,
    reaction_rows: Iterable[ReactionEnergyRow] | None = None,
    adsorption_rows: Iterable[AdsorptionEnergyRow] | None = None,
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
            adsorption_rows=adsorption_rows,
            title=title,
        ),
        encoding="utf-8",
    )


def _project_summary(
    results: list[CalculationResult],
    species: list[Species] | None,
    checks: list[QualityCheck],
    reaction_rows: list[ReactionEnergyRow],
    adsorption_rows: list[AdsorptionEnergyRow],
) -> str:
    counts = Counter(check.severity for check in checks)
    rows = [
        ("Species in registry", _format_value(len(species)) if species is not None else MISSING),
        ("Calculation results", _format_value(len(results))),
        ("Reaction rows", _format_value(len(reaction_rows))),
        ("Adsorption rows", _format_value(len(adsorption_rows))),
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


def _adsorption_system_summary(
    rows: list[AdsorptionEnergyRow], results: list[CalculationResult]
) -> str:
    result_by_name = {result.species_name: result for result in results}
    table_rows = [
        (
            row.system_id,
            row.slab_result,
            _source_path_for_result(result_by_name, row.slab_result),
            row.adsorbate_result,
            _source_path_for_result(result_by_name, row.adsorbate_result),
            row.combined_result,
            _source_path_for_result(result_by_name, row.combined_result),
        )
        for row in rows
    ]
    return "## Adsorption system summary\n\n" + _markdown_table(
        [
            "System ID",
            "Clean slab result",
            "Clean slab source",
            "Adsorbate result",
            "Adsorbate source",
            "Combined result",
            "Combined source",
        ],
        table_rows,
    )


def _adsorption_energy_table(rows: list[AdsorptionEnergyRow]) -> str:
    table_rows = [
        (
            row.system_id,
            row.quantity,
            row.complete,
            _format_number(row.adsorption_hartree),
            _format_number(row.adsorption_ev),
            _format_number(row.adsorption_kj_mol),
            ", ".join(row.missing),
            ", ".join(row.warnings),
            row.notes,
        )
        for row in rows
    ]
    return "## Adsorption energy/free-energy table\n\n" + _markdown_table(
        [
            "System ID",
            "Quantity",
            "Complete",
            "Adsorption energy/free energy (Hartree)",
            "Adsorption energy/free energy (eV)",
            "Adsorption energy/free energy (kJ/mol)",
            "Missing data",
            "Warnings",
            "Notes",
        ],
        table_rows,
    )


def _has_vibrational_data(results: list[CalculationResult]) -> bool:
    return any(
        mode.frequency_cm1 is not None
        for result in results
        for mode in result.properties.vibrational_modes
    )


def _has_imaginary_frequencies(results: list[CalculationResult]) -> bool:
    return any(
        _is_imaginary_mode(mode)
        for result in results
        for mode in result.properties.vibrational_modes
    )


def _has_excitation_data(results: list[CalculationResult]) -> bool:
    return any(result.properties.excitations for result in results)


def _has_orbital_data(results: list[CalculationResult]) -> bool:
    return any(
        result.homo_ev is not None
        or result.lumo_ev is not None
        or result.gap_ev is not None
        for result in results
    )


def _vibrational_summary(results: list[CalculationResult]) -> str:
    rows = []
    for result in results:
        modes = result.properties.vibrational_modes
        frequencies = [
            mode.frequency_cm1
            for mode in modes
            if mode.frequency_cm1 is not None
        ]
        if not frequencies:
            continue
        rows.append(
            (
                result.species_name,
                len(frequencies),
                _format_number(min(frequencies)),
                _format_number(max(frequencies)),
                sum(1 for mode in modes if _is_imaginary_mode(mode)),
                sum(1 for mode in modes if mode.ir_intensity_km_mol is not None),
                sum(
                    1
                    for mode in modes
                    if mode.raman_activity_angstrom4_amu is not None
                ),
            )
        )
    return "## Vibrational summary\n\n" + _markdown_table(
        [
            "Species",
            "Modes with frequencies",
            "Min frequency (cm^-1)",
            "Max frequency (cm^-1)",
            "Imaginary modes",
            "Modes with IR intensity (km/mol)",
            "Modes with Raman activity (angstrom^4/amu)",
        ],
        rows,
    )


def _imaginary_frequency_summary(results: list[CalculationResult]) -> str:
    rows = []
    for result in results:
        frequencies = [
            mode.frequency_cm1
            for mode in result.properties.vibrational_modes
            if _is_imaginary_mode(mode) and mode.frequency_cm1 is not None
        ]
        if not frequencies:
            continue
        rows.append(
            (
                result.species_name,
                len(frequencies),
                _format_number(min(frequencies)),
            )
        )
    return "## Imaginary-frequency summary\n\n" + _markdown_table(
        ["Species", "Imaginary modes", "Most negative frequency (cm^-1)"],
        rows,
    )


def _excitation_summary(results: list[CalculationResult]) -> str:
    rows = [
        (
            result.species_name,
            excitation.state_label,
            _format_number(excitation.energy_ev),
            _format_number(excitation.wavelength_nm),
            _format_number(excitation.oscillator_strength),
        )
        for result in results
        for excitation in result.properties.excitations
    ]
    return "## Excitation summary\n\n" + _markdown_table(
        [
            "Species",
            "State",
            "Excitation energy (eV)",
            "Wavelength (nm)",
            "Oscillator strength",
        ],
        rows,
    )


def _orbital_summary(results: list[CalculationResult]) -> str:
    rows = [
        (
            result.species_name,
            _format_number(result.homo_ev),
            _format_number(result.lumo_ev),
            _format_number(result.gap_ev),
        )
        for result in results
        if (
            result.homo_ev is not None
            or result.lumo_ev is not None
            or result.gap_ev is not None
        )
    ]
    return "## Orbital summary\n\n" + _markdown_table(
        ["Species", "HOMO (eV)", "LUMO (eV)", "Gap (eV)"],
        rows,
    )


def _property_plot_links(results: list[CalculationResult]) -> str:
    return "## Property plot links\n\n" + _markdown_table(
        ["Species", "Plot type", "Path"],
        _property_plot_rows(results),
    )


def _property_plot_rows(results: list[CalculationResult]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for result in results:
        for metadata_key in ("spectrum_plots", "property_plots"):
            value = result.metadata.get(metadata_key)
            if isinstance(value, dict):
                rows.extend(
                    (result.species_name, str(plot_type), str(path))
                    for plot_type, path in sorted(value.items())
                )
            elif isinstance(value, (list, tuple)):
                rows.extend((result.species_name, "plot", str(path)) for path in value)
            elif value:
                rows.append((result.species_name, "plot", str(value)))
    return rows


def _is_imaginary_mode(mode: object) -> bool:
    is_imaginary = getattr(mode, "is_imaginary", None)
    frequency = getattr(mode, "frequency_cm1", None)
    return bool(is_imaginary) or (frequency is not None and frequency < 0.0)


def _method_provenance_summary(
    results: list[CalculationResult],
    reaction_rows: list[ReactionEnergyRow],
    adsorption_rows: list[AdsorptionEnergyRow],
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

    warnings = _method_consistency_warnings(results, reaction_rows, adsorption_rows)
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
    results: list[CalculationResult],
    reaction_rows: list[ReactionEnergyRow],
    adsorption_rows: list[AdsorptionEnergyRow],
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
    for row in adsorption_rows:
        for warning in row.warnings:
            warnings.append(f"Adsorption row {row.system_id}: {warning}")
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


def _source_path_for_result(
    result_by_name: dict[str, CalculationResult], species_name: str
) -> str:
    result = result_by_name.get(species_name)
    if result is None or result.source_path is None:
        return MISSING
    return str(result.source_path)


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
