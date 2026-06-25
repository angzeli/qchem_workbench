"""Gaussian output parsing."""

from __future__ import annotations

import re
from pathlib import Path

from qchem_workbench.core.result import CalculationResult


_SCF_DONE_RE = re.compile(
    r"SCF Done:\s+E\([^)]+\)\s+=\s+([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?)"
)
_ROUTE_START_RE = re.compile(r"^\s*#")


def parse_gaussian_output(path: Path) -> CalculationResult:
    source_path = Path(path)
    warnings: list[str] = []

    try:
        text = source_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return CalculationResult(
            species_name=source_path.stem,
            backend="gaussian",
            method=None,
            basis=None,
            task=None,
            success=False,
            warnings=[f"could not read Gaussian output: {exc}"],
            metadata={},
            source_path=source_path,
        )

    normal_termination = "Normal termination of Gaussian" in text
    error_termination = "Error termination" in text
    if not normal_termination:
        warnings.append("Gaussian normal termination not found.")
    if error_termination:
        warnings.append("Gaussian error termination found.")

    route = _extract_route(text)
    if route is None:
        warnings.append("Gaussian route section was not found.")

    scf_energies = [_parse_float(match) for match in _SCF_DONE_RE.findall(text)]
    electronic_energy = None
    if scf_energies:
        electronic_energy = scf_energies[-1]
        if len(scf_energies) > 1:
            warnings.append("Multiple SCF energies found; using the last value.")
    else:
        warnings.append("SCF electronic energy was not found.")

    metadata = {
        "normal_termination": normal_termination,
        "error_termination": error_termination,
    }
    if route is not None:
        metadata["route"] = route

    return CalculationResult(
        species_name=source_path.stem,
        backend="gaussian",
        method=None,
        basis=None,
        task=None,
        success=normal_termination and not error_termination,
        electronic_energy_hartree=electronic_energy,
        warnings=warnings,
        metadata=metadata,
        source_path=source_path,
    )


def _extract_route(text: str) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not _ROUTE_START_RE.match(line):
            continue

        route_lines = [line.strip()]
        for continuation in lines[index + 1 :]:
            stripped = continuation.strip()
            if not stripped or set(stripped) == {"-"}:
                break
            route_lines.append(stripped)
        return " ".join(route_lines)
    return None


def _parse_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))
