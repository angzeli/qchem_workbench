"""Molecular result and property table helpers for the dashboard."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from qchem_workbench.dashboard.data import DashboardData


PROPERTY_TABLE_TYPES = ("dipoles", "charges", "orbitals", "vibrations", "excitations")


def molecular_result_rows(
    data: DashboardData,
    *,
    species: str | None = None,
    backend: str | None = None,
    method: str | None = None,
) -> list[dict[str, Any]]:
    rows = [
        {
            "species": result.get("species_name"),
            "backend": result.get("backend"),
            "method": result.get("method"),
            "basis": result.get("basis"),
            "task": result.get("task"),
            "success": result.get("success"),
            "electronic_energy_hartree": result.get("electronic_energy_hartree"),
            "gibbs_free_energy_hartree": result.get("gibbs_free_energy_hartree"),
            "source_path": result.get("source_path"),
            "warning_count": len(result.get("warnings", [])),
            "missing_values": _missing_result_fields(result),
        }
        for result in _result_rows(data)
    ]
    return _filter_rows(rows, species=species, backend=backend, method=method)


def molecular_property_rows(
    data: DashboardData,
    property_type: str,
    *,
    species: str | None = None,
    backend: str | None = None,
    method: str | None = None,
) -> list[dict[str, Any]]:
    if property_type not in PROPERTY_TABLE_TYPES:
        raise ValueError(f"unsupported molecular property table {property_type!r}")
    rows: list[dict[str, Any]] = []
    for result in _result_rows(data):
        if not _result_matches(result, species=species, backend=backend, method=method):
            continue
        properties = result.get("properties") or {}
        if property_type == "dipoles":
            rows.extend(_dipole_rows(result, properties))
        elif property_type == "charges":
            rows.extend(_charge_rows(result, properties))
        elif property_type == "orbitals":
            rows.extend(_orbital_rows(result, properties))
        elif property_type == "vibrations":
            rows.extend(_vibration_rows(result, properties))
        elif property_type == "excitations":
            rows.extend(_excitation_rows(result, properties))
    return rows


def table_rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers: list[str] = []
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)
    handle = StringIO()
    writer = csv.DictWriter(handle, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def _dipole_rows(result: dict[str, Any], properties: dict[str, Any]) -> list[dict[str, Any]]:
    dipole = properties.get("dipole_moment")
    if not isinstance(dipole, dict):
        return []
    return [
        {
            **_result_context(result),
            "x_debye": dipole.get("x_debye"),
            "y_debye": dipole.get("y_debye"),
            "z_debye": dipole.get("z_debye"),
            "total_debye": dipole.get("total_debye"),
            "source_backend": dipole.get("source_backend"),
            "source_section_label": dipole.get("source_section_label"),
        }
    ]


def _charge_rows(result: dict[str, Any], properties: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    analyses = properties.get("population_analyses") or []
    for analysis in analyses:
        for charge in analysis.get("atomic_charges", []):
            rows.append(
                {
                    **_result_context(result),
                    "scheme": analysis.get("scheme") or charge.get("scheme"),
                    "atom_index": charge.get("atom_index"),
                    "symbol": charge.get("symbol"),
                    "charge_e": charge.get("charge_e"),
                    "atom_label": charge.get("atom_label"),
                    "source_backend": analysis.get("source_backend"),
                    "source_section_label": analysis.get("source_section_label"),
                    "warnings": "; ".join(analysis.get("warnings", [])),
                }
            )
    if rows:
        return rows
    for charge in properties.get("atomic_charges") or []:
        rows.append(
            {
                **_result_context(result),
                "scheme": charge.get("scheme"),
                "atom_index": charge.get("atom_index"),
                "symbol": charge.get("symbol"),
                "charge_e": charge.get("charge_e"),
                "atom_label": charge.get("atom_label"),
            }
        )
    return rows


def _orbital_rows(result: dict[str, Any], properties: dict[str, Any]) -> list[dict[str, Any]]:
    orbital_table = properties.get("orbital_table") or {}
    orbitals = orbital_table.get("orbitals") or []
    return [
        {
            **_result_context(result),
            "orbital_index": orbital.get("index"),
            "energy_hartree": orbital.get("energy_hartree"),
            "energy_ev": orbital.get("energy_ev"),
            "occupation": orbital.get("occupation"),
            "spin_channel": orbital.get("spin_channel"),
            "symmetry_label": orbital.get("symmetry_label"),
            "homo_index": orbital_table.get("homo_index"),
            "lumo_index": orbital_table.get("lumo_index"),
            "warnings": "; ".join(orbital_table.get("warnings", [])),
        }
        for orbital in orbitals
    ]


def _vibration_rows(result: dict[str, Any], properties: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **_result_context(result),
            "mode_index": mode.get("mode_index"),
            "frequency_cm1": mode.get("frequency_cm1"),
            "ir_intensity_km_mol": mode.get("ir_intensity_km_mol"),
            "raman_activity_angstrom4_amu": mode.get("raman_activity_angstrom4_amu"),
            "reduced_mass_amu": mode.get("reduced_mass_amu"),
            "force_constant_mdyne_angstrom": mode.get("force_constant_mdyne_angstrom"),
            "is_imaginary": mode.get("is_imaginary"),
        }
        for mode in properties.get("vibrational_modes") or []
    ]


def _excitation_rows(result: dict[str, Any], properties: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **_result_context(result),
            "state_index": state.get("state_index"),
            "energy_ev": state.get("energy_ev"),
            "wavelength_nm": state.get("wavelength_nm"),
            "oscillator_strength": state.get("oscillator_strength"),
            "spin_multiplicity_label": state.get("spin_multiplicity_label"),
            "transition_description": state.get("transition_description"),
            "warnings": "; ".join(state.get("warnings", [])),
        }
        for state in properties.get("excitations") or []
    ]


def _result_rows(data: DashboardData) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in data.loaded_sections:
        if section.kind == "result_store":
            rows.extend(section.rows)
    return rows


def _result_context(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "species": result.get("species_name"),
        "backend": result.get("backend"),
        "method": result.get("method"),
        "basis": result.get("basis"),
        "task": result.get("task"),
        "source_path": result.get("source_path"),
    }


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    species: str | None,
    backend: str | None,
    method: str | None,
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if (not species or row.get("species") == species)
        and (not backend or row.get("backend") == backend)
        and (not method or row.get("method") == method)
    ]


def _result_matches(
    result: dict[str, Any],
    *,
    species: str | None,
    backend: str | None,
    method: str | None,
) -> bool:
    return (
        (not species or result.get("species_name") == species)
        and (not backend or result.get("backend") == backend)
        and (not method or result.get("method") == method)
    )


def _missing_result_fields(result: dict[str, Any]) -> str:
    missing = [
        label
        for label in (
            "electronic_energy_hartree",
            "gibbs_free_energy_hartree",
        )
        if result.get(label) is None
    ]
    return ";".join(missing)
