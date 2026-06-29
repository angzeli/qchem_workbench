"""Microkinetic dashboard table helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qchem_workbench.dashboard.data import DashboardData
from qchem_workbench.microkinetics.schema import MicrokineticModel, load_microkinetic_model


def microkinetic_network_rows(model: MicrokineticModel) -> dict[str, list[dict[str, Any]]]:
    return {
        "site_types": [
            {
                "id": item.id,
                "total_sites": item.total_sites,
                "unit": item.unit,
                "notes": item.notes,
                "provenance": item.provenance,
            }
            for item in model.site_types.values()
        ],
        "species": [
            {
                "id": item.id,
                "phase": item.phase,
                "site_type": item.site_type,
                "notes": item.notes,
                "provenance": item.provenance,
            }
            for item in model.species.values()
        ],
        "steps": [
            {
                "id": step.id,
                "reversible": step.reversible,
                "reactants": _stoichiometry_text(step.reactants),
                "products": _stoichiometry_text(step.products),
                "rate_constant_forward": step.rate_constant_forward,
                "rate_constant_reverse": step.rate_constant_reverse,
                "notes": step.notes,
                "provenance": step.provenance,
            }
            for step in model.steps
        ],
        "rate_parameters": [
            {"parameter_id": parameter_id} for parameter_id in model.rate_parameter_ids
        ],
    }


def load_microkinetic_network_rows(path: Path) -> tuple[dict[str, list[dict[str, Any]]] | None, list[str]]:
    try:
        model = load_microkinetic_model(path)
    except (OSError, ValueError) as exc:
        return None, [f"microkinetic model could not be loaded: {exc}"]
    return microkinetic_network_rows(model), []


def microkinetic_output_sections(data: DashboardData) -> dict[str, list[dict[str, Any]]]:
    sections = {
        "simulation": [],
        "steady_state": [],
        "rates": [],
        "sensitivity": [],
        "uncertainty": [],
        "unknown": [],
    }
    for section in data.loaded_sections:
        if section.kind != "microkinetic_output":
            continue
        for row in section.rows:
            sections[_classify_microkinetic_row(row)].append(row)
    return sections


def final_coverage_rows(simulation_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not simulation_rows:
        return []
    final = simulation_rows[-1]
    return [
        {"species": key, "coverage": value}
        for key, value in final.items()
        if key != "time"
    ]


def steady_state_warning_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    warnings = []
    for row in rows:
        if str(row.get("success", "")).lower() != "true":
            warnings.append(
                {
                    "species": row.get("species"),
                    "warning": "steady-state solver did not report success",
                    "residual": row.get("residual"),
                    "max_abs_residual": row.get("max_abs_residual"),
                }
            )
    return warnings


def _classify_microkinetic_row(row: dict[str, Any]) -> str:
    if "time" in row:
        return "simulation"
    if {"species", "coverage", "residual"}.issubset(row):
        return "steady_state"
    if "row_type" in row and "rate" in row:
        return "rates"
    if "sensitivity" in row and "parameter_id" in row:
        return "sensitivity"
    if {"observable", "success_count", "failure_count"}.issubset(row):
        return "uncertainty"
    return "unknown"


def _stoichiometry_text(values: dict[str, float]) -> str:
    return " + ".join(f"{coefficient:g} {species_id}" for species_id, coefficient in values.items())
