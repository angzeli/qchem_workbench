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
_FREQUENCIES_LINE_RE = re.compile(r"Frequencies\s+--\s+(.+)", re.IGNORECASE)
_ORCA_FREQUENCY_RE = re.compile(
    rf"^\s*\d+\s*:\s*({_NUMBER})\s+cm\*\*-?1\b", re.IGNORECASE
)
_HOMO_EV_RE = re.compile(
    rf"\bHOMO(?:\s+ENERGY)?\s*(?::|=)?\s*({_NUMBER})\s*eV\b",
    re.IGNORECASE,
)
_LUMO_EV_RE = re.compile(
    rf"\bLUMO(?:\s+ENERGY)?\s*(?::|=)?\s*({_NUMBER})\s*eV\b",
    re.IGNORECASE,
)
_SPIN_BEFORE_RE = re.compile(
    rf"S\*\*2\s+before\s+annihilation\s*(?::|=)?\s*({_NUMBER})",
    re.IGNORECASE,
)
_SPIN_AFTER_RE = re.compile(
    rf"S\*\*2\s+after\s+annihilation\s*(?::|=)?\s*({_NUMBER})",
    re.IGNORECASE,
)
_S2_EXPECTATION_RE = re.compile(
    rf"(?:Expectation\s+value\s+of\s+)?<?S\*\*2>?\s*(?::|=)\s*({_NUMBER})",
    re.IGNORECASE,
)
_THERMOCHEMISTRY_PATTERNS = {
    "zero_point_correction_hartree": re.compile(
        rf"^\s*Zero\s+point(?:\s+energy|\s+correction)?"
        rf"\s*(?::|=)?\s*({_NUMBER})\s*(?:Eh|Hartree)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "thermal_correction_energy_hartree": re.compile(
        rf"^\s*Thermal\s+correction\s+to\s+Energy"
        rf"\s*(?::|=)?\s*({_NUMBER})\s*(?:Eh|Hartree)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "thermal_correction_enthalpy_hartree": re.compile(
        rf"^\s*Thermal\s+correction\s+to\s+Enthalpy"
        rf"\s*(?::|=)?\s*({_NUMBER})\s*(?:Eh|Hartree)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "thermal_correction_gibbs_hartree": re.compile(
        rf"^\s*Thermal\s+correction\s+to\s+Gibbs\s+Free\s+Energy"
        rf"\s*(?::|=)?\s*({_NUMBER})\s*(?:Eh|Hartree)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "gibbs_free_energy_hartree": re.compile(
        rf"^\s*(?:Final\s+)?Gibbs\s+free\s+energy"
        rf"\s*(?::|=)?\s*({_NUMBER})\s*(?:Eh|Hartree)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
}
_THERMOCHEMISTRY_CORRECTION_KEYS = (
    "zero_point_correction_hartree",
    "thermal_correction_energy_hartree",
    "thermal_correction_enthalpy_hartree",
    "thermal_correction_gibbs_hartree",
)
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

    thermochemistry = _extract_thermochemistry(text, warnings)
    frequencies = _extract_frequencies(text, warnings)
    negative_frequencies = [value for value in frequencies if value < 0.0]
    if negative_frequencies:
        warnings.append(
            "Negative frequencies found; parser reports values without assigning "
            "transition-state identity."
        )
    homo_ev, lumo_ev, gap_ev = _extract_orbital_summary(text)
    spin_metadata = _extract_spin_metadata(text, warnings)

    metadata = {
        "normal_termination": normal_termination,
        "error_termination": error_termination,
        "frequencies_cm1": frequencies,
        "negative_frequency_count": len(negative_frequencies),
        "most_negative_frequency_cm1": (
            min(negative_frequencies) if negative_frequencies else None
        ),
    }
    metadata.update(spin_metadata)
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
        gibbs_free_energy_hartree=thermochemistry.get("gibbs_free_energy_hartree"),
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
        homo_ev=homo_ev,
        lumo_ev=lumo_ev,
        gap_ev=gap_ev,
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


def _extract_thermochemistry(
    text: str, warnings: list[str]
) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    for key, pattern in _THERMOCHEMISTRY_PATTERNS.items():
        matches = list(pattern.finditer(text))
        if matches:
            values[key] = _parse_float(matches[-1].group(1))

    parsed_corrections = [
        key for key in _THERMOCHEMISTRY_CORRECTION_KEYS if key in values
    ]
    if parsed_corrections and len(parsed_corrections) != len(
        _THERMOCHEMISTRY_CORRECTION_KEYS
    ):
        warnings.append("Incomplete ORCA thermochemistry section found.")
    return values


def _extract_frequencies(text: str, warnings: list[str]) -> list[float]:
    frequencies: list[float] = []
    malformed_tokens = 0
    malformed_rows = 0

    for line in text.splitlines():
        line_match = _FREQUENCIES_LINE_RE.search(line)
        if line_match:
            for token in line_match.group(1).split():
                try:
                    frequencies.append(_parse_float(token))
                except ValueError:
                    malformed_tokens += 1
            continue

        if "cm**" not in line.lower():
            continue
        row_match = _ORCA_FREQUENCY_RE.search(line)
        if row_match:
            frequencies.append(_parse_float(row_match.group(1)))
        else:
            malformed_rows += 1

    if malformed_tokens or malformed_rows:
        warnings.append("Malformed ORCA frequency value(s) were ignored.")
    return frequencies


def _extract_orbital_summary(
    text: str,
) -> tuple[float | None, float | None, float | None]:
    homo_matches = list(_HOMO_EV_RE.finditer(text))
    lumo_matches = list(_LUMO_EV_RE.finditer(text))
    homo_ev = _parse_float(homo_matches[-1].group(1)) if homo_matches else None
    lumo_ev = _parse_float(lumo_matches[-1].group(1)) if lumo_matches else None
    gap_ev = None
    if homo_ev is not None and lumo_ev is not None:
        gap_ev = lumo_ev - homo_ev
    return homo_ev, lumo_ev, gap_ev


def _extract_spin_metadata(text: str, warnings: list[str]) -> dict[str, float]:
    spin_values: dict[str, float] = {}

    for line in text.splitlines():
        if "s**2" not in line.lower():
            continue

        before_match = _SPIN_BEFORE_RE.search(line)
        after_match = _SPIN_AFTER_RE.search(line)
        expectation_match = _S2_EXPECTATION_RE.search(line)
        if before_match:
            spin_values["s2_before_annihilation"] = _parse_float(
                before_match.group(1)
            )
        if after_match:
            spin_values["s2_after_annihilation"] = _parse_float(after_match.group(1))
        if expectation_match and "s2_before_annihilation" not in spin_values:
            spin_values["s2_before_annihilation"] = _parse_float(
                expectation_match.group(1)
            )
        if not (before_match or after_match or expectation_match):
            warnings.append("Malformed ORCA S**2 spin line was ignored.")

    return spin_values
