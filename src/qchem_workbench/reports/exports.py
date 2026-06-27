"""CSV and LaTeX table exports for qchem-workbench reports."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Iterable

from qchem_workbench.analysis.reactions import ReactionEnergyRow
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species


MISSING_TEXT = "N/A"
PROPERTY_EXPORT_TYPES = (
    "dipoles",
    "charges",
    "orbitals",
    "vibrations",
    "excitations",
)


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


def property_rows_for_type(
    results: Iterable[CalculationResult],
    property_type: str,
) -> list[dict[str, str]]:
    """Return tidy property rows for *property_type*."""

    result_list = list(results)
    if property_type == "dipoles":
        return _dipole_rows(result_list)
    if property_type == "charges":
        return _charge_rows(result_list)
    if property_type == "orbitals":
        return _orbital_rows(result_list)
    if property_type == "vibrations":
        return _vibration_rows(result_list)
    if property_type == "excitations":
        return _excitation_rows(result_list)
    raise ValueError(f"unsupported property export type {property_type!r}")


def property_rows_to_csv(property_type: str, rows: list[dict[str, str]]) -> str:
    """Return CSV text for property rows of *property_type*."""

    return _dict_rows_to_csv(rows, _PROPERTY_HEADERS[property_type])


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

_PROPERTY_BASE_HEADERS = [
    "species",
    "backend",
    "method",
    "basis",
    "task",
    "source_path",
]

_PROPERTY_HEADERS = {
    "dipoles": [
        *_PROPERTY_BASE_HEADERS,
        "property_backend",
        "source_section",
        "x_debye",
        "y_debye",
        "z_debye",
        "total_debye",
        "unit",
    ],
    "charges": [
        *_PROPERTY_BASE_HEADERS,
        "property_backend",
        "source_section",
        "scheme",
        "atom_index",
        "element_symbol",
        "atom_label",
        "charge_e",
        "charge_unit",
        "warnings",
    ],
    "orbitals": [
        *_PROPERTY_BASE_HEADERS,
        "table_backend",
        "source_section",
        "orbital_index",
        "energy_hartree",
        "energy_hartree_unit",
        "energy_ev",
        "energy_ev_unit",
        "occupation",
        "spin_channel",
        "symmetry_label",
        "homo_index",
        "lumo_index",
        "warnings",
    ],
    "vibrations": [
        *_PROPERTY_BASE_HEADERS,
        "mode_index",
        "frequency_cm1",
        "frequency_unit",
        "ir_intensity_km_mol",
        "ir_intensity_unit",
        "raman_activity_angstrom4_amu",
        "raman_activity_unit",
        "reduced_mass_amu",
        "reduced_mass_unit",
        "force_constant_mdyne_angstrom",
        "force_constant_unit",
        "is_imaginary",
    ],
    "excitations": [
        *_PROPERTY_BASE_HEADERS,
        "state_index",
        "state_label",
        "spin_multiplicity_label",
        "energy_ev",
        "energy_unit",
        "wavelength_nm",
        "wavelength_unit",
        "oscillator_strength",
        "transition_description",
        "warnings",
    ],
}


def _dipole_rows(results: list[CalculationResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in results:
        dipole = result.properties.dipole_moment
        if dipole is None:
            continue
        row = _property_base_row(result)
        row.update(
            {
                "property_backend": _csv_value(dipole.source_backend or result.backend),
                "source_section": _csv_value(dipole.source_section_label),
                "x_debye": _csv_value(dipole.x_debye),
                "y_debye": _csv_value(dipole.y_debye),
                "z_debye": _csv_value(dipole.z_debye),
                "total_debye": _csv_value(dipole.total_debye),
                "unit": dipole.unit,
            }
        )
        rows.append(row)
    return rows


def _charge_rows(results: list[CalculationResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in results:
        analyses = result.properties.population_analyses
        if analyses:
            for analysis in analyses:
                for charge in analysis.atomic_charges:
                    row = _property_base_row(result)
                    row.update(
                        {
                            "property_backend": _csv_value(
                                analysis.source_backend or result.backend
                            ),
                            "source_section": _csv_value(
                                analysis.source_section_label
                            ),
                            "scheme": analysis.scheme,
                            "atom_index": _csv_value(charge.atom_index),
                            "element_symbol": _csv_value(charge.symbol),
                            "atom_label": _csv_value(charge.atom_label),
                            "charge_e": _csv_value(charge.charge_e),
                            "charge_unit": charge.charge_unit,
                            "warnings": ";".join(analysis.warnings),
                        }
                    )
                    rows.append(row)
            continue

        for charge in result.properties.atomic_charges:
            row = _property_base_row(result)
            row.update(
                {
                    "property_backend": result.backend,
                    "source_section": "",
                    "scheme": _csv_value(charge.scheme),
                    "atom_index": _csv_value(charge.atom_index),
                    "element_symbol": _csv_value(charge.symbol),
                    "atom_label": _csv_value(charge.atom_label),
                    "charge_e": _csv_value(charge.charge_e),
                    "charge_unit": charge.charge_unit,
                    "warnings": "",
                }
            )
            rows.append(row)
    return rows


def _orbital_rows(results: list[CalculationResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in results:
        table = result.properties.orbital_table
        if table is None:
            continue
        for orbital in table.orbitals:
            row = _property_base_row(result)
            row.update(
                {
                    "table_backend": _csv_value(table.backend or result.backend),
                    "source_section": _csv_value(table.source_section_label),
                    "orbital_index": _csv_value(orbital.index),
                    "energy_hartree": _csv_value(orbital.energy_hartree),
                    "energy_hartree_unit": orbital.hartree_unit,
                    "energy_ev": _csv_value(orbital.energy_ev),
                    "energy_ev_unit": orbital.ev_unit,
                    "occupation": _csv_value(orbital.occupation),
                    "spin_channel": _csv_value(orbital.spin_channel),
                    "symmetry_label": _csv_value(orbital.symmetry_label),
                    "homo_index": _csv_value(table.homo_index),
                    "lumo_index": _csv_value(table.lumo_index),
                    "warnings": ";".join(table.warnings),
                }
            )
            rows.append(row)
    return rows


def _vibration_rows(results: list[CalculationResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in results:
        for mode in result.properties.vibrational_modes:
            row = _property_base_row(result)
            row.update(
                {
                    "mode_index": _csv_value(mode.mode_index),
                    "frequency_cm1": _csv_value(mode.frequency_cm1),
                    "frequency_unit": mode.frequency_unit,
                    "ir_intensity_km_mol": _csv_value(mode.ir_intensity_km_mol),
                    "ir_intensity_unit": mode.ir_intensity_unit,
                    "raman_activity_angstrom4_amu": _csv_value(
                        mode.raman_activity_angstrom4_amu
                    ),
                    "raman_activity_unit": mode.raman_activity_unit,
                    "reduced_mass_amu": _csv_value(mode.reduced_mass_amu),
                    "reduced_mass_unit": mode.reduced_mass_unit,
                    "force_constant_mdyne_angstrom": _csv_value(
                        mode.force_constant_mdyne_angstrom
                    ),
                    "force_constant_unit": mode.force_constant_unit,
                    "is_imaginary": _csv_value(mode.is_imaginary),
                }
            )
            rows.append(row)
    return rows


def _excitation_rows(results: list[CalculationResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in results:
        for excitation in result.properties.excitations:
            row = _property_base_row(result)
            row.update(
                {
                    "state_index": _csv_value(excitation.state_index),
                    "state_label": _csv_value(excitation.state_label),
                    "spin_multiplicity_label": _csv_value(
                        excitation.spin_multiplicity_label
                    ),
                    "energy_ev": _csv_value(excitation.energy_ev),
                    "energy_unit": excitation.energy_unit,
                    "wavelength_nm": _csv_value(excitation.wavelength_nm),
                    "wavelength_unit": excitation.wavelength_unit,
                    "oscillator_strength": _csv_value(
                        excitation.oscillator_strength
                    ),
                    "transition_description": _csv_value(
                        excitation.transition_description
                    ),
                    "warnings": ";".join(excitation.warnings),
                }
            )
            rows.append(row)
    return rows


def _property_base_row(result: CalculationResult) -> dict[str, str]:
    return {
        "species": result.species_name,
        "backend": result.backend,
        "method": _csv_value(result.method),
        "basis": _csv_value(result.basis),
        "task": _csv_value(result.task),
        "source_path": str(result.source_path) if result.source_path else "",
    }


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
