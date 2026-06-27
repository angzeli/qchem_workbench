"""ORCA output parsing."""

from __future__ import annotations

import re
from pathlib import Path

from qchem_workbench.core.properties import (
    AtomicCharge,
    CalculationProperties,
    DipoleMoment,
    ElectronicExcitation,
    MolecularOrbital,
    OrbitalTable,
    PopulationAnalysis,
    VibrationalMode,
    wavelength_nm_from_ev,
)
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.units import HARTREE_TO_EV


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DEde][-+]?\d+)?"
_FINAL_ENERGY_RE = re.compile(
    rf"FINAL\s+SINGLE\s+POINT\s+ENERGY\s+({_NUMBER})", re.IGNORECASE
)
_ROUTE_RE = re.compile(r"^\s*!\s+(.+)$", re.MULTILINE)
_FREQUENCIES_LINE_RE = re.compile(r"Frequencies\s+--\s+(.+)", re.IGNORECASE)
_IR_INTENSITIES_LINE_RE = re.compile(r"IR\s+Inten(?:sities)?\s+--\s+(.+)", re.IGNORECASE)
_RAMAN_ACTIVITIES_LINE_RE = re.compile(
    r"Raman\s+Activ(?:ities)?\s+--\s+(.+)", re.IGNORECASE
)
_ORCA_FREQUENCY_RE = re.compile(
    rf"^\s*\d+\s*:\s*({_NUMBER})\s+cm\*\*-?1\b", re.IGNORECASE
)
_ORCA_IR_VALUE_RE = re.compile(
    rf"\bIR(?:\s+Intensity)?\s*(?:=|:)?\s*({_NUMBER})", re.IGNORECASE
)
_ORCA_RAMAN_VALUE_RE = re.compile(
    rf"\bRaman(?:\s+Activity)?\s*(?:=|:)?\s*({_NUMBER})", re.IGNORECASE
)
_ORCA_EXCITATION_RE = re.compile(
    rf"^\s*STATE\s+(\d+)\s*:\s*(?:E\s*=\s*)?({_NUMBER})\s*eV"
    rf"(?:\s+({_NUMBER})\s*nm)?(?:.*?\bf\s*=\s*({_NUMBER}))?",
    re.IGNORECASE | re.MULTILINE,
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
_ATOM_COUNT_RE = re.compile(
    r"Number\s+of\s+atoms\s*(?::|=)?\s*(\d+)", re.IGNORECASE
)
_DIPOLE_COMPONENT_RE = re.compile(
    rf"Total\s+Dipole\s+Moment\s*\(Debye\)\s*(?::|=)\s*"
    rf"({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})",
    re.IGNORECASE,
)
_DIPOLE_TOTAL_RE = re.compile(
    rf"Magnitude\s*\(Debye\)\s*(?::|=)\s*({_NUMBER})", re.IGNORECASE
)
_CHARGE_SECTION_RE = re.compile(
    r"^\s*(Mulliken|Lowdin|Loewdin|Löwdin|NPA)\s+"
    r"(?:atomic\s+)?charges\b",
    re.IGNORECASE,
)
_CHARGE_ROW_RE = re.compile(
    rf"^\s*(\d+)\s+([A-Z][a-z]?)\s*:?\s+({_NUMBER})\s*$"
)
_ORBITAL_SECTION_RE = re.compile(
    r"^\s*(?:(ALPHA|BETA|SPIN\s+UP|SPIN\s+DOWN)\s+)?"
    r"(?:ORBITAL\s+ENERGIES|ORBITALS)\b",
    re.IGNORECASE,
)
_ORBITAL_ROW_RE = re.compile(
    rf"^\s*(\d+)\s+({_NUMBER})\s+({_NUMBER})(?:\s+({_NUMBER}))?\s*$"
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
    vibrational_modes = _extract_vibrational_modes(text, warnings)
    excitations = _extract_excitations(text)
    atom_count = _extract_atom_count(text)
    dipole_moment = _extract_dipole_moment(text, warnings)
    population_analyses = _extract_population_analyses(text, warnings, atom_count)
    atomic_charges = tuple(
        charge
        for analysis in population_analyses
        for charge in analysis.atomic_charges
    )
    orbital_table = _extract_orbital_table(text, warnings)
    frequencies = [
        float(mode.frequency_cm1)
        for mode in vibrational_modes
        if mode.frequency_cm1 is not None
    ]
    negative_frequencies = [value for value in frequencies if value < 0.0]
    if negative_frequencies:
        warnings.append(
            "Negative frequencies found; parser reports values without assigning "
            "transition-state identity."
        )
    homo_ev, lumo_ev, gap_ev = (
        _orbital_summary_from_table(orbital_table)
        if orbital_table is not None
        else _extract_orbital_summary(text)
    )
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
        properties=CalculationProperties(
            vibrational_modes=tuple(vibrational_modes),
            excitations=tuple(excitations),
            dipole_moment=dipole_moment,
            atomic_charges=atomic_charges,
            population_analyses=tuple(population_analyses),
            orbital_table=orbital_table,
        ),
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


def _extract_vibrational_modes(text: str, warnings: list[str]) -> list[VibrationalMode]:
    modes: list[VibrationalMode] = []
    lines = text.splitlines()
    malformed_tokens = 0
    malformed_rows = 0

    for index, line in enumerate(lines):
        line_match = _FREQUENCIES_LINE_RE.search(line)
        if line_match:
            frequencies, malformed = _parse_float_tokens(line_match.group(1).split())
            malformed_tokens += malformed
            ir_values: list[float] = []
            raman_values: list[float] = []
            for followup in lines[index + 1 :]:
                if _FREQUENCIES_LINE_RE.search(followup):
                    break
                ir_match = _IR_INTENSITIES_LINE_RE.search(followup)
                if ir_match:
                    parsed, malformed = _parse_float_tokens(ir_match.group(1).split())
                    ir_values = parsed
                    malformed_tokens += malformed
                raman_match = _RAMAN_ACTIVITIES_LINE_RE.search(followup)
                if raman_match:
                    parsed, malformed = _parse_float_tokens(
                        raman_match.group(1).split()
                    )
                    raman_values = parsed
                    malformed_tokens += malformed
            for mode_index, frequency in enumerate(frequencies):
                modes.append(
                    VibrationalMode(
                        frequency_cm1=frequency,
                        ir_intensity_km_mol=(
                            ir_values[mode_index]
                            if mode_index < len(ir_values)
                            else None
                        ),
                        raman_activity_angstrom4_amu=(
                            raman_values[mode_index]
                            if mode_index < len(raman_values)
                            else None
                        ),
                        is_imaginary=frequency < 0.0,
                    )
                )
            continue

        if "cm**" not in line.lower():
            continue
        row_match = _ORCA_FREQUENCY_RE.search(line)
        if row_match:
            frequency = _parse_float(row_match.group(1))
            ir_match = _ORCA_IR_VALUE_RE.search(line)
            raman_match = _ORCA_RAMAN_VALUE_RE.search(line)
            modes.append(
                VibrationalMode(
                    frequency_cm1=frequency,
                    ir_intensity_km_mol=(
                        _parse_float(ir_match.group(1)) if ir_match else None
                    ),
                    raman_activity_angstrom4_amu=(
                        _parse_float(raman_match.group(1)) if raman_match else None
                    ),
                    is_imaginary=frequency < 0.0,
                )
            )
        else:
            malformed_rows += 1

    if malformed_tokens or malformed_rows:
        warnings.append("Malformed ORCA frequency value(s) were ignored.")
    return modes


def _parse_float_tokens(tokens: list[str]) -> tuple[list[float], int]:
    values: list[float] = []
    malformed = 0
    for token in tokens:
        try:
            values.append(_parse_float(token))
        except ValueError:
            malformed += 1
    return values, malformed


def _extract_excitations(text: str) -> list[ElectronicExcitation]:
    excitations: list[ElectronicExcitation] = []
    for match in _ORCA_EXCITATION_RE.finditer(text):
        state_index = match.group(1)
        energy_ev = _parse_float(match.group(2))
        wavelength_nm = (
            _parse_float(match.group(3))
            if match.group(3) is not None
            else wavelength_nm_from_ev(energy_ev)
        )
        oscillator_strength = (
            _parse_float(match.group(4)) if match.group(4) is not None else None
        )
        excitations.append(
            ElectronicExcitation(
                energy_ev=energy_ev,
                wavelength_nm=wavelength_nm,
                oscillator_strength=oscillator_strength,
                state_label=f"STATE {state_index}",
            )
        )
    return excitations


def _extract_atom_count(text: str) -> int | None:
    matches = _ATOM_COUNT_RE.findall(text)
    return int(matches[-1]) if matches else None


def _extract_dipole_moment(text: str, warnings: list[str]) -> DipoleMoment | None:
    component_matches = list(_DIPOLE_COMPONENT_RE.finditer(text))
    total_matches = list(_DIPOLE_TOTAL_RE.finditer(text))
    if not component_matches and not total_matches:
        return None
    if len(component_matches) > 1 or len(total_matches) > 1:
        warnings.append("Multiple ORCA dipole sections found; using the last values.")

    component_match = component_matches[-1] if component_matches else None
    return DipoleMoment(
        x_debye=(
            _parse_float(component_match.group(1)) if component_match else None
        ),
        y_debye=(
            _parse_float(component_match.group(2)) if component_match else None
        ),
        z_debye=(
            _parse_float(component_match.group(3)) if component_match else None
        ),
        total_debye=(
            _parse_float(total_matches[-1].group(1)) if total_matches else None
        ),
        source_backend="orca",
        source_section_label="Dipole moment (Debye)",
    )


def _extract_population_analyses(
    text: str,
    warnings: list[str],
    atom_count: int | None,
) -> list[PopulationAnalysis]:
    analyses_by_scheme: dict[str, PopulationAnalysis] = {}
    lines = text.splitlines()

    for index, line in enumerate(lines):
        header = _CHARGE_SECTION_RE.match(line)
        if not header:
            continue

        scheme = _normalise_charge_scheme(header.group(1))
        charges, section_warnings = _parse_charge_rows(lines[index + 1 :], scheme)
        warnings.extend(section_warnings)
        if not charges:
            warnings.append(f"ORCA {scheme} charge section contained no parseable rows.")
            continue
        if atom_count is not None and len(charges) != atom_count:
            warnings.append(
                f"ORCA {scheme} charge count {len(charges)} does not match "
                f"number of atoms {atom_count}."
            )
        if scheme in analyses_by_scheme:
            warnings.append(
                f"Multiple ORCA {scheme} charge sections found; using the last."
            )
        analyses_by_scheme[scheme] = PopulationAnalysis(
            scheme=scheme,
            atomic_charges=tuple(charges),
            warnings=tuple(section_warnings),
            source_backend="orca",
            source_section_label=line.strip(),
        )

    return list(analyses_by_scheme.values())


def _parse_charge_rows(
    lines: list[str],
    scheme: str,
) -> tuple[list[AtomicCharge], list[str]]:
    charges: list[AtomicCharge] = []
    warnings: list[str] = []
    malformed_rows = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if charges:
                break
            continue
        if _CHARGE_SECTION_RE.match(line):
            break
        if set(stripped) <= {"-", " "}:
            continue
        if stripped.lower().startswith(("atom", "index", "number")):
            continue

        match = _CHARGE_ROW_RE.match(line)
        if match:
            charges.append(
                AtomicCharge(
                    atom_index=int(match.group(1)),
                    symbol=match.group(2),
                    charge_e=_parse_float(match.group(3)),
                    scheme=scheme,
                )
            )
            continue

        if charges:
            malformed_rows += 1

    if malformed_rows:
        warnings.append(f"Malformed ORCA {scheme} charge row(s) were ignored.")
    return charges, warnings


def _normalise_charge_scheme(raw_scheme: str) -> str:
    lower = raw_scheme.lower()
    if lower.startswith(("lowdin", "loewdin", "löwdin")):
        return "Lowdin"
    if lower.startswith("mulliken"):
        return "Mulliken"
    return raw_scheme.upper()


def _extract_orbital_table(text: str, warnings: list[str]) -> OrbitalTable | None:
    orbitals: list[MolecularOrbital] = []
    table_warnings: list[str] = []
    malformed_rows = 0
    in_section = False
    current_spin: str | None = None

    for line in text.splitlines():
        section_match = _ORBITAL_SECTION_RE.match(line)
        if section_match:
            in_section = True
            current_spin = _normalise_spin_channel(section_match.group(1))
            continue
        if not in_section:
            continue

        stripped = line.strip()
        if not stripped:
            if orbitals:
                in_section = False
            continue
        if set(stripped) <= {"-", " "}:
            continue
        if stripped.lower().startswith(("no", "index", "orb")):
            continue
        if stripped.startswith("*") or "terminated normally" in stripped.lower():
            in_section = False
            continue

        row_match = _ORBITAL_ROW_RE.match(line)
        if row_match:
            energy_hartree, energy_ev = _orbital_energies_from_row(row_match)
            orbitals.append(
                MolecularOrbital(
                    index=int(row_match.group(1)),
                    occupation=_parse_float(row_match.group(2)),
                    energy_hartree=energy_hartree,
                    energy_ev=energy_ev,
                    spin_channel=current_spin,
                )
            )
            continue

        if orbitals:
            malformed_rows += 1
            in_section = False

    if malformed_rows:
        message = "Malformed ORCA orbital table row(s) were ignored."
        warnings.append(message)
        table_warnings.append(message)
    if not orbitals:
        return None

    homo, lumo = _homo_lumo_orbitals(orbitals)
    if homo is None or lumo is None:
        message = "Incomplete ORCA orbital table; HOMO/LUMO may be missing."
        warnings.append(message)
        table_warnings.append(message)

    return OrbitalTable(
        backend="orca",
        orbitals=tuple(orbitals),
        homo_index=homo.index if homo else None,
        lumo_index=lumo.index if lumo else None,
        warnings=tuple(table_warnings),
        source_section_label="Orbital energies",
    )


def _normalise_spin_channel(raw_spin: str | None) -> str | None:
    if raw_spin is None:
        return None
    normalized = raw_spin.strip().lower().replace(" ", "_")
    if normalized == "spin_up":
        return "alpha"
    if normalized == "spin_down":
        return "beta"
    return normalized


def _orbital_energies_from_row(
    row_match: re.Match[str],
) -> tuple[float | None, float | None]:
    first_energy = _parse_float(row_match.group(3))
    second_energy = row_match.group(4)
    if second_energy is None:
        return first_energy, first_energy * HARTREE_TO_EV
    return first_energy, _parse_float(second_energy)


def _homo_lumo_orbitals(
    orbitals: list[MolecularOrbital] | tuple[MolecularOrbital, ...],
) -> tuple[MolecularOrbital | None, MolecularOrbital | None]:
    occupied = [
        orbital
        for orbital in orbitals
        if orbital.occupation is not None
        and orbital.occupation > 0.0
        and orbital.energy_ev is not None
    ]
    virtual = [
        orbital
        for orbital in orbitals
        if orbital.occupation is not None
        and orbital.occupation == 0.0
        and orbital.energy_ev is not None
    ]
    homo = max(occupied, key=lambda orbital: orbital.energy_ev) if occupied else None
    lumo = min(virtual, key=lambda orbital: orbital.energy_ev) if virtual else None
    return homo, lumo


def _orbital_summary_from_table(
    orbital_table: OrbitalTable,
) -> tuple[float | None, float | None, float | None]:
    homo, lumo = _homo_lumo_orbitals(orbital_table.orbitals)
    homo_ev = homo.energy_ev if homo else None
    lumo_ev = lumo.energy_ev if lumo else None
    gap_ev = lumo_ev - homo_ev if homo_ev is not None and lumo_ev is not None else None
    return homo_ev, lumo_ev, gap_ev


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
