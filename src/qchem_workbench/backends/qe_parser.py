"""Quantum ESPRESSO pw.x output parsing."""

from __future__ import annotations

import re
from pathlib import Path

from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.units import HARTREE_TO_EV


RYDBERG_TO_HARTREE = 0.5
RYDBERG_TO_EV = HARTREE_TO_EV * RYDBERG_TO_HARTREE
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DEde][-+]?\d+)?"
_TOTAL_ENERGY_RE = re.compile(
    rf"!\s+total\s+energy\s+=\s+({_NUMBER})\s+([A-Za-z/]+)", re.IGNORECASE
)
_NAT_RE = re.compile(r"number\s+of\s+atoms/cell\s*=\s*(\d+)", re.IGNORECASE)
_MAX_FORCE_RE = re.compile(
    rf"(?:maximum|max)\s+force\s*=\s*({_NUMBER})\s*([A-Za-z/]+)?",
    re.IGNORECASE,
)
_CELL_START_RE = re.compile(r"^\s*CELL_PARAMETERS\b", re.IGNORECASE)
_ATOMIC_POSITIONS_START_RE = re.compile(r"^\s*ATOMIC_POSITIONS\b", re.IGNORECASE)
_ATOMIC_POSITION_ROW_RE = re.compile(
    rf"^\s*([A-Z][a-z]?)\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})"
)


def parse_qe_output(path: Path) -> CalculationResult:
    source_path = Path(path)
    warnings: list[str] = []

    try:
        text = source_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return CalculationResult(
            species_name=source_path.stem,
            backend="qe",
            method=None,
            basis=None,
            task=None,
            success=False,
            warnings=[f"could not read QE output: {exc}"],
            metadata={},
            source_path=source_path,
        )

    completed = "JOB DONE." in text
    scf_converged = _scf_converged(text)
    if not completed:
        warnings.append("QE job completion marker was not found.")
    if scf_converged is False:
        warnings.append("QE SCF convergence was not achieved.")
    elif scf_converged is None:
        warnings.append("QE SCF convergence status was not found.")

    energies: list[dict[str, float | str]] = []
    for match in _TOTAL_ENERGY_RE.finditer(text):
        try:
            energies.append(_energy_values(match))
        except ValueError as exc:
            warnings.append(str(exc))
    electronic_energy_hartree = None
    energy_metadata: dict[str, float | str] = {}
    if energies:
        energy_metadata = energies[-1]
        electronic_energy_hartree = float(energy_metadata["total_energy_hartree"])
        if len(energies) > 1:
            warnings.append("Multiple QE total energies found; using the last value.")
    else:
        warnings.append("QE total energy was not found.")

    metadata = {
        "completed": completed,
        "scf_converged": scf_converged,
        **energy_metadata,
    }
    n_atoms = _number_of_atoms(text)
    if n_atoms is not None:
        metadata["n_atoms"] = n_atoms
    cell = _cell_parameters(text, warnings)
    if cell is not None:
        metadata["cell"] = cell
    max_force = _maximum_force(text)
    if max_force is not None:
        metadata.update(max_force)
    relaxation = _relaxation_trajectory(text, warnings, energies)
    if relaxation is not None:
        metadata["relaxation_trajectory"] = relaxation
        if relaxation.get("relaxation_converged") is False:
            warnings.append("QE relaxation convergence was not achieved.")

    return CalculationResult(
        species_name=source_path.stem,
        backend="qe",
        method=None,
        basis=None,
        task=None,
        success=(
            completed
            and scf_converged is not False
            and not (
                relaxation is not None
                and relaxation.get("relaxation_converged") is False
            )
        ),
        electronic_energy_hartree=electronic_energy_hartree,
        warnings=warnings,
        metadata=metadata,
        source_path=source_path,
    )


def _scf_converged(text: str) -> bool | None:
    lower = text.lower()
    if "convergence not achieved" in lower or "not converged" in lower:
        return False
    if "convergence has been achieved" in lower:
        return True
    return None


def _energy_values(match: re.Match[str]) -> dict[str, float | str]:
    value = _parse_float(match.group(1))
    unit = match.group(2).lower()
    if unit in {"ry", "rydberg", "rydbergs"}:
        hartree = value * RYDBERG_TO_HARTREE
        ev = value * RYDBERG_TO_EV
        ry = value
    elif unit in {"ev"}:
        hartree = value / HARTREE_TO_EV
        ev = value
        ry = value / RYDBERG_TO_EV
    elif unit in {"ha", "hartree", "hartrees"}:
        hartree = value
        ev = value * HARTREE_TO_EV
        ry = value / RYDBERG_TO_HARTREE
    else:
        raise ValueError(f"unsupported QE total energy unit {unit!r}")
    return {
        "total_energy_unit": unit,
        "total_energy_hartree": hartree,
        "total_energy_ev": ev,
        "total_energy_ry": ry,
    }


def _number_of_atoms(text: str) -> int | None:
    match = _NAT_RE.search(text)
    return int(match.group(1)) if match else None


def _cell_parameters(text: str, warnings: list[str]) -> list[list[float]] | None:
    cells = _all_cell_parameters(text, warnings)
    return cells[-1]["vectors"] if cells else None


def _all_cell_parameters(
    text: str,
    warnings: list[str],
) -> list[dict[str, object]]:
    lines = text.splitlines()
    cells: list[dict[str, object]] = []
    for index, line in enumerate(lines):
        if not _CELL_START_RE.match(line):
            continue
        vectors: list[list[float]] = []
        for offset in range(1, 4):
            try:
                values = [_parse_float(value) for value in lines[index + offset].split()]
            except (IndexError, ValueError):
                warnings.append("Malformed QE CELL_PARAMETERS block was ignored.")
                break
            if len(values) < 3:
                warnings.append("Malformed QE CELL_PARAMETERS block was ignored.")
                break
            vectors.append(values[:3])
        if len(vectors) == 3:
            cells.append({"unit": _block_unit(line) or "", "vectors": vectors})
    return cells


def _maximum_force(text: str) -> dict[str, float | str] | None:
    values = _maximum_force_values(text)
    if not values:
        return None
    return values[-1]


def _maximum_force_values(text: str) -> list[dict[str, float | str]]:
    values: list[dict[str, float | str]] = []
    for match in _MAX_FORCE_RE.finditer(text):
        values.append(
            {
                "max_force": _parse_float(match.group(1)),
                "max_force_unit": match.group(2) or "",
            }
        )
    return values


def _relaxation_trajectory(
    text: str,
    warnings: list[str],
    energies: list[dict[str, float | str]],
) -> dict[str, object] | None:
    force_values = _maximum_force_values(text)
    cells = _all_cell_parameters(text, warnings)
    positions = _atomic_positions_blocks(text, warnings)
    convergence_markers = _scf_convergence_markers(text)
    relaxation_converged = _relaxation_converged(text)

    has_trajectory = (
        len(energies) > 1
        or len(force_values) > 1
        or len(cells) > 1
        or positions
        or relaxation_converged is not None
    )
    if not has_trajectory:
        return None

    steps: list[dict[str, object]] = []
    for index, energy in enumerate(energies):
        step: dict[str, object] = {"step_index": index + 1, **energy}
        if index < len(force_values):
            step.update(force_values[index])
        if index < len(convergence_markers):
            step["scf_converged"] = convergence_markers[index]
        steps.append(step)

    trajectory: dict[str, object] = {
        "steps": steps,
        "relaxation_converged": relaxation_converged,
    }
    if energies:
        trajectory["final_total_energy_hartree"] = energies[-1][
            "total_energy_hartree"
        ]
        trajectory["final_total_energy_ev"] = energies[-1]["total_energy_ev"]
        trajectory["final_total_energy_ry"] = energies[-1]["total_energy_ry"]
    if force_values:
        trajectory["final_max_force"] = force_values[-1]["max_force"]
        trajectory["final_max_force_unit"] = force_values[-1]["max_force_unit"]
    if cells:
        trajectory["final_cell"] = cells[-1]
    if positions:
        trajectory["final_atomic_positions"] = positions[-1]
    elif relaxation_converged is not None or len(energies) > 1:
        warnings.append("QE relaxation trajectory has no final atomic positions.")
    return trajectory


def _atomic_positions_blocks(
    text: str,
    warnings: list[str],
) -> list[dict[str, object]]:
    lines = text.splitlines()
    blocks: list[dict[str, object]] = []
    for index, line in enumerate(lines):
        if not _ATOMIC_POSITIONS_START_RE.match(line):
            continue
        atoms: list[dict[str, object]] = []
        malformed_rows = 0
        for row in lines[index + 1 :]:
            if not row.strip():
                if atoms:
                    break
                continue
            if _CELL_START_RE.match(row) or _ATOMIC_POSITIONS_START_RE.match(row):
                break
            match = _ATOMIC_POSITION_ROW_RE.match(row)
            if not match:
                if atoms:
                    malformed_rows += 1
                    break
                continue
            atoms.append(
                {
                    "symbol": match.group(1),
                    "x": _parse_float(match.group(2)),
                    "y": _parse_float(match.group(3)),
                    "z": _parse_float(match.group(4)),
                }
            )
        if malformed_rows:
            warnings.append("Malformed QE ATOMIC_POSITIONS row(s) were ignored.")
        if atoms:
            blocks.append({"unit": _block_unit(line) or "", "atoms": atoms})
    return blocks


def _scf_convergence_markers(text: str) -> list[bool]:
    markers: list[bool] = []
    for line in text.splitlines():
        lower = line.lower()
        if "convergence has been achieved" in lower:
            markers.append(True)
        elif "convergence not achieved" in lower or "not converged" in lower:
            markers.append(False)
    return markers


def _relaxation_converged(text: str) -> bool | None:
    lower = text.lower()
    if (
        "relaxation not converged" in lower
        or "bfgs failed" in lower
        or "geometry optimization failed" in lower
    ):
        return False
    if (
        "relaxation converged" in lower
        or "bfgs converged" in lower
        or "end of bfgs geometry optimization" in lower
    ):
        return True
    return None


def _block_unit(line: str) -> str | None:
    match = re.search(r"\(([^)]+)\)", line)
    if match:
        return match.group(1).strip()
    parts = line.split()
    return parts[1].strip() if len(parts) > 1 else None


def _parse_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))
