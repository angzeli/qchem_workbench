"""CSV and LaTeX table exports for qchem-workbench reports."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Iterable

from qchem_workbench.analysis.reactions import ReactionEnergyRow
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species


MISSING_TEXT = "N/A"


def results_to_csv(results: Iterable[CalculationResult]) -> str:
    """Return a CSV table for calculation results."""

    rows = [
        {
            "Species": result.species_name,
            "Backend": result.backend,
            "Method": _csv_value(result.method),
            "Basis": _csv_value(result.basis),
            "Task": _csv_value(result.task),
            "Success": str(result.success),
            "Electronic energy (Hartree)": _csv_value(
                result.electronic_energy_hartree
            ),
            "Gibbs free energy (Hartree)": _csv_value(
                result.gibbs_free_energy_hartree
            ),
            "Zero-point correction (Hartree)": _csv_value(
                result.zero_point_correction_hartree
            ),
            "Thermal correction to Gibbs (Hartree)": _csv_value(
                result.thermal_correction_gibbs_hartree
            ),
            "HOMO (eV)": _csv_value(result.homo_ev),
            "LUMO (eV)": _csv_value(result.lumo_ev),
            "Gap (eV)": _csv_value(result.gap_ev),
            "Warnings": str(len(result.warnings)),
            "Source path": str(result.source_path) if result.source_path else "",
        }
        for result in results
    ]
    return _dict_rows_to_csv(rows, _RESULT_HEADERS)


def species_to_csv(species: Iterable[Species]) -> str:
    """Return a CSV table for registry species."""

    rows = [
        {
            "Name": item.name,
            "Formula": _csv_value(item.formula),
            "Charge": str(item.charge),
            "Multiplicity": str(item.multiplicity),
            "Geometry path": str(item.geometry_path),
            "Tags": ";".join(item.tags),
            "Notes": _csv_value(item.notes),
        }
        for item in species
    ]
    return _dict_rows_to_csv(rows, _SPECIES_HEADERS)


def reaction_rows_to_csv(rows: Iterable[ReactionEnergyRow]) -> str:
    """Return a CSV table for reaction energy rows."""

    csv_rows = [
        {
            "Reaction ID": row.reaction_id,
            "Label": _csv_value(row.label),
            "Quantity": row.quantity,
            "Complete": str(row.complete),
            "Delta (Hartree)": _csv_value(row.delta_hartree),
            "Delta (eV)": _csv_value(row.delta_ev),
            "Delta (kJ/mol)": _csv_value(row.delta_kj_mol),
            "Missing species": ";".join(row.missing_species),
            "Notes": _csv_value(row.notes),
        }
        for row in rows
    ]
    return _dict_rows_to_csv(csv_rows, _REACTION_HEADERS)


def results_to_latex_tabular(results: Iterable[CalculationResult]) -> str:
    """Return a simple LaTeX tabular for calculation results."""

    rows = [
        [
            result.species_name,
            result.backend,
            _latex_value(result.method),
            _latex_value(result.basis),
            _latex_value(result.task),
            _latex_value(result.electronic_energy_hartree),
            _latex_value(result.gibbs_free_energy_hartree),
            str(len(result.warnings)),
        ]
        for result in results
    ]
    headers = [
        "Species",
        "Backend",
        "Method",
        "Basis",
        "Task",
        "Electronic energy (Hartree)",
        "Gibbs free energy (Hartree)",
        "Warnings",
    ]
    return _latex_tabular(headers, rows)


def reaction_rows_to_latex_tabular(rows: Iterable[ReactionEnergyRow]) -> str:
    """Return a simple LaTeX tabular for reaction energy rows."""

    table_rows = [
        [
            row.reaction_id,
            _latex_value(row.label),
            row.quantity,
            str(row.complete),
            _latex_value(row.delta_hartree),
            _latex_value(row.delta_ev),
            _latex_value(row.delta_kj_mol),
            ";".join(row.missing_species) or MISSING_TEXT,
        ]
        for row in rows
    ]
    headers = [
        "Reaction ID",
        "Label",
        "Quantity",
        "Complete",
        "Delta (Hartree)",
        "Delta (eV)",
        "Delta (kJ/mol)",
        "Missing species",
    ]
    return _latex_tabular(headers, table_rows)


def latex_escape(value: object) -> str:
    """Escape LaTeX special characters in *value*."""

    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in text)


_RESULT_HEADERS = [
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
    "Source path",
]

_SPECIES_HEADERS = [
    "Name",
    "Formula",
    "Charge",
    "Multiplicity",
    "Geometry path",
    "Tags",
    "Notes",
]

_REACTION_HEADERS = [
    "Reaction ID",
    "Label",
    "Quantity",
    "Complete",
    "Delta (Hartree)",
    "Delta (eV)",
    "Delta (kJ/mol)",
    "Missing species",
    "Notes",
]


def _dict_rows_to_csv(rows: list[dict[str, str]], fieldnames: list[str]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _latex_tabular(headers: list[str], rows: list[list[object]]) -> str:
    column_spec = "l" * len(headers)
    lines = [
        rf"\begin{{tabular}}{{{column_spec}}}",
        " & ".join(latex_escape(header) for header in headers) + r" \\",
        r"\hline",
    ]
    lines.extend(
        " & ".join(latex_escape(_latex_value(value)) for value in row) + r" \\"
        for row in rows
    )
    lines.append(r"\end{tabular}")
    return "\n".join(lines) + "\n"


def _csv_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _latex_value(value: object) -> str:
    if value is None:
        return MISSING_TEXT
    if isinstance(value, str) and value == "":
        return MISSING_TEXT
    return str(value)
