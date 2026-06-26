"""ORCA output parsing."""

from __future__ import annotations

import re
from pathlib import Path

from qchem_workbench.core.result import CalculationResult


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DEde][-+]?\d+)?"
_FINAL_ENERGY_RE = re.compile(
    rf"FINAL\s+SINGLE\s+POINT\s+ENERGY\s+({_NUMBER})", re.IGNORECASE
)
_ROUTE_RE = re.compile(r"^\s*!\s+(.+)$", re.MULTILINE)
_SINGLE_POINT_TOKENS = {"sp", "singlepoint", "single_point"}
_TASK_TOKENS = _SINGLE_POINT_TOKENS | {"opt", "freq"}


def parse_orca_output(path: Path) -> CalculationResult:
    source_path = Path(path)
    warnings: list[str] = []

    try:
        text = source_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return CalculationResult(
            species_name=source_path.stem,
            backend="orca",
            method=None,
            basis=None,
            task=None,
            success=False,
            warnings=[f"could not read ORCA output: {exc}"],
            metadata={},
            source_path=source_path,
        )

    upper_text = text.upper()
    normal_termination = "ORCA TERMINATED NORMALLY" in upper_text
    error_termination = (
        "ORCA TERMINATED WITH ERROR" in upper_text
        or "ERROR TERMINATION" in upper_text
    )
    if not normal_termination:
        warnings.append("ORCA normal termination not found.")
    if error_termination:
        warnings.append("ORCA error termination found.")

    route = _extract_route(text)
    if route is None:
        warnings.append("ORCA route line was not found.")
    method, basis, task = _method_basis_task_from_route(route)
    if route is not None and method is None:
        warnings.append("ORCA method was not detected from the route line.")
    if route is not None and basis is None:
        warnings.append("ORCA basis was not detected from the route line.")

    electronic_energies = [
        _parse_float(match.group(1)) for match in _FINAL_ENERGY_RE.finditer(text)
    ]
    electronic_energy = None
    if electronic_energies:
        electronic_energy = electronic_energies[-1]
        if len(electronic_energies) > 1:
            warnings.append(
                "Multiple ORCA final single-point energies found; using the last "
                "value."
            )
    else:
        warnings.append("ORCA final single-point energy was not found.")

    metadata = {
        "normal_termination": normal_termination,
        "error_termination": error_termination,
    }
    if route is not None:
        metadata["route"] = route

    return CalculationResult(
        species_name=source_path.stem,
        backend="orca",
        method=method,
        basis=basis,
        task=task,
        success=normal_termination and not error_termination,
        electronic_energy_hartree=electronic_energy,
        warnings=warnings,
        metadata=metadata,
        source_path=source_path,
    )


def _extract_route(text: str) -> str | None:
    match = _ROUTE_RE.search(text)
    if match is None:
        return None
    return "! " + match.group(1).strip()


def _method_basis_task_from_route(
    route: str | None,
) -> tuple[str | None, str | None, str | None]:
    if route is None:
        return None, None, None

    tokens = route.removeprefix("!").split()
    method = None
    basis = None
    task_tokens: set[str] = set()

    for token in tokens:
        normalized = token.lower()
        if normalized in _TASK_TOKENS:
            task_tokens.add(normalized)
            continue
        if method is None:
            method = token
            continue
        if basis is None:
            basis = token

    task = None
    if "opt" in task_tokens and "freq" in task_tokens:
        task = "opt_freq"
    elif "opt" in task_tokens:
        task = "opt"
    elif "freq" in task_tokens:
        task = "freq"
    elif task_tokens & _SINGLE_POINT_TOKENS:
        task = "single_point"

    return method, basis, task


def _parse_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))
