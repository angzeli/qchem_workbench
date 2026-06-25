"""Gaussian output parsing."""

from __future__ import annotations

import re
from pathlib import Path

from qchem_workbench.core.result import CalculationResult


_SCF_DONE_RE = re.compile(
    r"SCF Done:\s+E\([^)]+\)\s+=\s+([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?)"
)
_ROUTE_START_RE = re.compile(r"^\s*#")
_FREQUENCIES_RE = re.compile(r"Frequencies\s+--\s+(.+)")
_SPIN_LINE_RE = re.compile(r"S\*\*2\s+before\s+annihilation", re.IGNORECASE)
_SPIN_VALUES_RE = re.compile(
    r"S\*\*2\s+before\s+annihilation\s+"
    r"([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?),?\s+after\s+"
    r"([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?)",
    re.IGNORECASE,
)
_THERMOCHEMISTRY_PATTERNS = {
    "zero_point_correction_hartree": re.compile(
        r"Zero-point correction=\s+([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?)"
    ),
    "thermal_correction_energy_hartree": re.compile(
        r"Thermal correction to Energy=\s+([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?)"
    ),
    "thermal_correction_enthalpy_hartree": re.compile(
        r"Thermal correction to Enthalpy=\s+([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?)"
    ),
    "thermal_correction_gibbs_hartree": re.compile(
        r"Thermal correction to Gibbs Free Energy=\s+"
        r"([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?)"
    ),
    "sum_electronic_zero_point_energy_hartree": re.compile(
        r"Sum of electronic and zero-point Energies=\s+"
        r"([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?)"
    ),
    "sum_electronic_thermal_free_energy_hartree": re.compile(
        r"Sum of electronic and thermal Free Energies=\s+"
        r"([-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?)"
    ),
}
_THERMOCHEMISTRY_KEYS = tuple(_THERMOCHEMISTRY_PATTERNS)


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

    thermochemistry = _extract_thermochemistry(text, warnings)
    frequencies = _extract_frequencies(text, warnings)
    negative_frequencies = [value for value in frequencies if value < 0.0]
    if negative_frequencies:
        warnings.append(
            "Negative frequencies found; parser reports values without assigning "
            "transition-state identity."
        )

    metadata = {
        "normal_termination": normal_termination,
        "error_termination": error_termination,
        "frequencies_cm1": frequencies,
        "negative_frequency_count": len(negative_frequencies),
        "most_negative_frequency_cm1": (
            min(negative_frequencies) if negative_frequencies else None
        ),
    }
    spin_metadata = _extract_spin_metadata(text, warnings)
    metadata.update(spin_metadata)
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
        gibbs_free_energy_hartree=thermochemistry.get(
            "sum_electronic_thermal_free_energy_hartree"
        ),
        zero_point_correction_hartree=thermochemistry.get(
            "zero_point_correction_hartree"
        ),
        thermal_correction_energy_hartree=thermochemistry.get(
            "thermal_correction_energy_hartree"
        ),
        thermal_correction_enthalpy_hartree=thermochemistry.get(
            "thermal_correction_enthalpy_hartree"
        ),
        thermal_correction_gibbs_hartree=thermochemistry.get(
            "thermal_correction_gibbs_hartree"
        ),
        sum_electronic_zero_point_energy_hartree=thermochemistry.get(
            "sum_electronic_zero_point_energy_hartree"
        ),
        sum_electronic_thermal_free_energy_hartree=thermochemistry.get(
            "sum_electronic_thermal_free_energy_hartree"
        ),
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


def _extract_thermochemistry(
    text: str, warnings: list[str]
) -> dict[str, float | None]:
    sections = _thermochemistry_sections(text)
    if not sections:
        return {}

    complete_sections = [
        section
        for section in sections
        if all(key in section for key in _THERMOCHEMISTRY_KEYS)
    ]
    if complete_sections:
        if len(complete_sections) > 1:
            warnings.append(
                "Multiple complete thermochemistry sections found; using the last."
            )
        return complete_sections[-1]

    warnings.append("Incomplete Gaussian thermochemistry section found.")
    return sections[-1]


def _thermochemistry_sections(text: str) -> list[dict[str, float | None]]:
    sections: list[dict[str, float | None]] = []
    current: dict[str, float | None] = {}

    for line in text.splitlines():
        parsed_key = None
        parsed_value = None
        for key, pattern in _THERMOCHEMISTRY_PATTERNS.items():
            match = pattern.search(line)
            if match:
                parsed_key = key
                parsed_value = _parse_float(match.group(1))
                break

        if parsed_key is None:
            continue
        if parsed_key == "zero_point_correction_hartree" and current:
            sections.append(current)
            current = {}
        current[parsed_key] = parsed_value

    if current:
        sections.append(current)
    return sections


def _extract_frequencies(text: str, warnings: list[str]) -> list[float]:
    frequencies: list[float] = []
    malformed_lines = 0

    for line in text.splitlines():
        match = _FREQUENCIES_RE.search(line)
        if not match:
            continue

        for token in match.group(1).split():
            try:
                frequencies.append(_parse_float(token))
            except ValueError:
                malformed_lines += 1

    if malformed_lines:
        warnings.append(
            "Malformed Gaussian frequency token(s) were ignored during parsing."
        )
    return frequencies


def _extract_spin_metadata(text: str, warnings: list[str]) -> dict[str, float]:
    spin_values: dict[str, float] = {}

    for line in text.splitlines():
        if not _SPIN_LINE_RE.search(line):
            continue

        match = _SPIN_VALUES_RE.search(line)
        if not match:
            warnings.append("Malformed Gaussian S**2 spin line was ignored.")
            continue
        spin_values = {
            "s2_before_annihilation": _parse_float(match.group(1)),
            "s2_after_annihilation": _parse_float(match.group(2)),
        }

    return spin_values
