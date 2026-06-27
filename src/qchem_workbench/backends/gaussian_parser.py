"""Gaussian output parsing."""

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


_NUMBER = r"[-+]?\d+(?:\.\d+)?(?:[DEde][-+]?\d+)?"
_SCF_DONE_RE = re.compile(
    rf"SCF Done:\s+E\([^)]+\)\s+=\s+({_NUMBER})"
)
_ROUTE_START_RE = re.compile(r"^\s*#")
_FREQUENCIES_RE = re.compile(r"Frequencies\s+--\s+(.+)")
_REDUCED_MASSES_RE = re.compile(r"Red\.\s+masses\s+--\s+(.+)", re.IGNORECASE)
_FORCE_CONSTANTS_RE = re.compile(r"Frc\s+consts\s+--\s+(.+)", re.IGNORECASE)
_IR_INTENSITIES_RE = re.compile(r"IR\s+Inten\s+--\s+(.+)", re.IGNORECASE)
_RAMAN_ACTIVITIES_RE = re.compile(r"Raman\s+Activ\s+--\s+(.+)", re.IGNORECASE)
_EXCITED_STATE_RE = re.compile(
    rf"^\s*Excited\s+State\s+(\d+):\s+(.+?)\s+({_NUMBER})\s+eV"
    rf"(?:\s+({_NUMBER})\s+nm)?(?:.*?\bf\s*=\s*({_NUMBER}))?",
    re.IGNORECASE,
)
_TD_TRANSITION_RE = re.compile(
    r"^\s*([A-Za-z0-9_.+\-]+\s*(?:->|<-)\s*[A-Za-z0-9_.+\-]+.*)$"
)
_SPIN_LINE_RE = re.compile(r"S\*\*2\s+before\s+annihilation", re.IGNORECASE)
_SPIN_VALUES_RE = re.compile(
    r"S\*\*2\s+before\s+annihilation\s+"
    rf"({_NUMBER}),?\s+after\s+"
    rf"({_NUMBER})",
    re.IGNORECASE,
)
_ATOM_COUNT_RE = re.compile(r"\bNAtoms=\s*(\d+)")
_DIPOLE_SECTION_RE = re.compile(
    r"Dipole moment.*?Debye.*?\n"
    rf"\s*X=\s*({_NUMBER})\s+Y=\s*({_NUMBER})\s+"
    rf"Z=\s*({_NUMBER})\s+Tot=\s*({_NUMBER})",
    re.IGNORECASE | re.DOTALL,
)
_CHARGE_SECTION_RE = re.compile(
    r"^\s*(Mulliken|Lowdin|Löwdin|NPA|Natural Population Analysis)"
    r"(?:\s+(?:atomic\s+)?)?charges\b",
    re.IGNORECASE,
)
_CHARGE_ROW_RE = re.compile(
    rf"^\s*(\d+)\s+([A-Z][a-z]?)(?:\s+\S+)?\s+({_NUMBER})\s*$"
)
_ORBITAL_EIGENVALUE_RE = re.compile(
    r"^\s*(?:(Alpha|Beta)\s+)?(occ\.|virt\.)\s+eigenvalues\s+--\s+(.+)$",
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
    vibrational_modes = _extract_vibrational_modes(text, warnings)
    excitations = _extract_excitations(text, warnings)
    atom_count = _extract_atom_count(text)
    dipole_moment = _extract_dipole_moment(text, warnings)
    population_analyses = _extract_population_analyses(text, warnings, atom_count)
    atomic_charges = tuple(
        charge
        for analysis in population_analyses
        for charge in analysis.atomic_charges
    )
    orbital_table = _extract_orbital_table(text, warnings)
    homo_ev, lumo_ev, gap_ev = _orbital_summary_from_table(orbital_table)
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


def _extract_vibrational_modes(
    text: str, warnings: list[str]
) -> list[VibrationalMode]:
    modes: list[VibrationalMode] = []
    lines = text.splitlines()
    malformed_frequency_tokens = 0
    malformed_property_tokens = 0

    for index, line in enumerate(lines):
        match = _FREQUENCIES_RE.search(line)
        if not match:
            continue

        frequencies: list[float] = []
        for token in match.group(1).split():
            try:
                frequencies.append(_parse_float(token))
            except ValueError:
                malformed_frequency_tokens += 1

        ir_values: list[float] = []
        raman_values: list[float] = []
        reduced_masses: list[float] = []
        force_constants: list[float] = []
        for followup in lines[index + 1 :]:
            if _FREQUENCIES_RE.search(followup):
                break
            reduced_match = _REDUCED_MASSES_RE.search(followup)
            if reduced_match:
                parsed, malformed = _parse_float_tokens(reduced_match.group(1).split())
                reduced_masses = parsed
                malformed_property_tokens += malformed
            force_match = _FORCE_CONSTANTS_RE.search(followup)
            if force_match:
                parsed, malformed = _parse_float_tokens(force_match.group(1).split())
                force_constants = parsed
                malformed_property_tokens += malformed
            ir_match = _IR_INTENSITIES_RE.search(followup)
            if ir_match:
                parsed, malformed = _parse_float_tokens(ir_match.group(1).split())
                ir_values = parsed
                malformed_property_tokens += malformed
            raman_match = _RAMAN_ACTIVITIES_RE.search(followup)
            if raman_match:
                parsed, malformed = _parse_float_tokens(raman_match.group(1).split())
                raman_values = parsed
                malformed_property_tokens += malformed

        for mode_index, frequency in enumerate(frequencies):
            modes.append(
                VibrationalMode(
                    mode_index=len(modes) + 1,
                    frequency_cm1=frequency,
                    ir_intensity_km_mol=(
                        ir_values[mode_index] if mode_index < len(ir_values) else None
                    ),
                    raman_activity_angstrom4_amu=(
                        raman_values[mode_index]
                        if mode_index < len(raman_values)
                        else None
                    ),
                    reduced_mass_amu=(
                        reduced_masses[mode_index]
                        if mode_index < len(reduced_masses)
                        else None
                    ),
                    force_constant_mdyne_angstrom=(
                        force_constants[mode_index]
                        if mode_index < len(force_constants)
                        else None
                    ),
                    is_imaginary=frequency < 0.0,
                )
            )

    if malformed_frequency_tokens:
        warnings.append(
            "Malformed Gaussian frequency token(s) were ignored during parsing."
        )
    if malformed_property_tokens:
        warnings.append(
            "Malformed Gaussian vibrational property token(s) were ignored."
        )
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


def _extract_excitations(
    text: str,
    warnings: list[str],
) -> list[ElectronicExcitation]:
    excitations: list[ElectronicExcitation] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "excited state" not in line.lower():
            continue
        match = _EXCITED_STATE_RE.match(line)
        if not match:
            warnings.append("Malformed Gaussian excited-state line was ignored.")
            continue

        state_index = int(match.group(1))
        state_label = match.group(2).strip()
        energy_ev = _parse_float(match.group(3))
        wavelength_nm = (
            _parse_float(match.group(4))
            if match.group(4) is not None
            else wavelength_nm_from_ev(energy_ev)
        )
        oscillator_strength = (
            _parse_float(match.group(5)) if match.group(5) is not None else None
        )
        transition_description = _extract_transition_description(lines[index + 1 :])
        excitations.append(
            ElectronicExcitation(
                energy_ev=energy_ev,
                state_index=state_index,
                wavelength_nm=wavelength_nm,
                oscillator_strength=oscillator_strength,
                spin_multiplicity_label=state_label,
                transition_description=transition_description,
                state_label=f"Excited State {state_index}: {state_label}",
            )
        )
    return excitations


def _extract_transition_description(lines: list[str]) -> str | None:
    transitions: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            break
        if "excited state" in stripped.lower():
            break
        match = _TD_TRANSITION_RE.match(line)
        if match:
            transitions.append(" ".join(match.group(1).split()))
    return "; ".join(transitions) if transitions else None


def _extract_atom_count(text: str) -> int | None:
    matches = _ATOM_COUNT_RE.findall(text)
    return int(matches[-1]) if matches else None


def _extract_dipole_moment(text: str, warnings: list[str]) -> DipoleMoment | None:
    matches = list(_DIPOLE_SECTION_RE.finditer(text))
    if not matches:
        return None
    if len(matches) > 1:
        warnings.append("Multiple Gaussian dipole sections found; using the last.")

    match = matches[-1]
    return DipoleMoment(
        x_debye=_parse_float(match.group(1)),
        y_debye=_parse_float(match.group(2)),
        z_debye=_parse_float(match.group(3)),
        total_debye=_parse_float(match.group(4)),
        source_backend="gaussian",
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
            warnings.append(
                f"Gaussian {scheme} charge section contained no parseable rows."
            )
            continue

        if atom_count is not None and len(charges) != atom_count:
            warnings.append(
                f"Gaussian {scheme} charge count {len(charges)} does not match "
                f"NAtoms={atom_count}."
            )
        if scheme in analyses_by_scheme:
            warnings.append(
                f"Multiple Gaussian {scheme} charge sections found; using the last."
            )
        analyses_by_scheme[scheme] = PopulationAnalysis(
            scheme=scheme,
            atomic_charges=tuple(charges),
            warnings=tuple(section_warnings),
            source_backend="gaussian",
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
        if stripped.lower().startswith("sum of"):
            break
        if set(stripped) <= {"-", " "}:
            continue
        if stripped.lower().startswith(("atom", "center", "number")):
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
        warnings.append(
            f"Malformed Gaussian {scheme} charge row(s) were ignored."
        )
    return charges, warnings


def _normalise_charge_scheme(raw_scheme: str) -> str:
    lower = raw_scheme.lower()
    if lower.startswith("lowdin") or lower.startswith("löwdin"):
        return "Lowdin"
    if lower.startswith("mulliken"):
        return "Mulliken"
    if lower.startswith("natural population"):
        return "NPA"
    return raw_scheme.upper()


def _extract_orbital_table(text: str, warnings: list[str]) -> OrbitalTable | None:
    parsed_lines: list[tuple[str | None, str, list[float]]] = []
    malformed_tokens = 0

    for line in text.splitlines():
        match = _ORBITAL_EIGENVALUE_RE.match(line)
        if not match:
            continue
        spin_channel = match.group(1).lower() if match.group(1) else None
        kind = match.group(2).lower()
        values, malformed = _parse_float_tokens(match.group(3).split())
        malformed_tokens += malformed
        if values:
            parsed_lines.append((spin_channel, kind, values))

    if malformed_tokens:
        warnings.append(
            "Malformed Gaussian orbital eigenvalue token(s) were ignored."
        )
    if not parsed_lines:
        return None

    has_beta = any(spin_channel == "beta" for spin_channel, _, _ in parsed_lines)
    has_occupied = any(kind == "occ." for _, kind, _ in parsed_lines)
    has_virtual = any(kind == "virt." for _, kind, _ in parsed_lines)
    table_warnings: list[str] = []
    if not (has_occupied and has_virtual):
        message = (
            "Incomplete Gaussian orbital eigenvalue section; HOMO/LUMO may be "
            "missing."
        )
        table_warnings.append(message)
        warnings.append(message)

    orbitals: list[MolecularOrbital] = []
    for spin_channel, kind, values in parsed_lines:
        occupation = _orbital_occupation(kind, spin_channel, has_beta)
        for value in values:
            orbitals.append(
                MolecularOrbital(
                    index=len(orbitals) + 1,
                    energy_hartree=value,
                    energy_ev=value * HARTREE_TO_EV,
                    occupation=occupation,
                    spin_channel=spin_channel,
                )
            )

    homo, lumo = _homo_lumo_orbitals(orbitals)
    return OrbitalTable(
        backend="gaussian",
        orbitals=tuple(orbitals),
        homo_index=homo.index if homo else None,
        lumo_index=lumo.index if lumo else None,
        warnings=tuple(table_warnings),
        source_section_label="Orbital eigenvalues",
    )


def _orbital_occupation(
    kind: str,
    spin_channel: str | None,
    has_beta: bool,
) -> float:
    if kind != "occ.":
        return 0.0
    if has_beta or spin_channel in {"alpha", "beta"}:
        return 1.0
    return 2.0


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
    orbital_table: OrbitalTable | None,
) -> tuple[float | None, float | None, float | None]:
    if orbital_table is None:
        return None, None, None
    homo, lumo = _homo_lumo_orbitals(orbital_table.orbitals)
    homo_ev = homo.energy_ev if homo else None
    lumo_ev = lumo.energy_ev if lumo else None
    gap_ev = lumo_ev - homo_ev if homo_ev is not None and lumo_ev is not None else None
    return homo_ev, lumo_ev, gap_ev


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
