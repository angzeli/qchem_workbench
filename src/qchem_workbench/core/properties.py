"""Backend-independent parsed molecular property models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


EV_NM_PRODUCT = 1239.8419843320026

__all__ = [
    "AtomicCharge",
    "CalculationProperties",
    "DipoleMoment",
    "EV_NM_PRODUCT",
    "ElectronicExcitation",
    "ExcitedState",
    "MolecularOrbital",
    "OrbitalTable",
    "PopulationAnalysis",
    "VibrationalMode",
    "wavelength_nm_from_ev",
]


def wavelength_nm_from_ev(energy_ev: float) -> float:
    if energy_ev <= 0.0:
        raise ValueError("energy_ev must be positive")
    return EV_NM_PRODUCT / energy_ev


@dataclass(frozen=True)
class VibrationalMode:
    frequency_cm1: float | None
    mode_index: int | None = None
    ir_intensity_km_mol: float | None = None
    raman_activity_angstrom4_amu: float | None = None
    reduced_mass_amu: float | None = None
    force_constant_mdyne_angstrom: float | None = None
    is_imaginary: bool | None = None

    @property
    def frequency_unit(self) -> str:
        return "cm^-1"

    @property
    def ir_intensity_unit(self) -> str:
        return "km/mol"

    @property
    def raman_activity_unit(self) -> str:
        return "angstrom^4/amu"

    @property
    def reduced_mass_unit(self) -> str:
        return "amu"

    @property
    def force_constant_unit(self) -> str:
        return "mDyne/angstrom"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_index": self.mode_index,
            "frequency_cm1": self.frequency_cm1,
            "frequency_unit": self.frequency_unit,
            "ir_intensity_km_mol": self.ir_intensity_km_mol,
            "ir_intensity_unit": self.ir_intensity_unit,
            "raman_activity_angstrom4_amu": self.raman_activity_angstrom4_amu,
            "raman_activity_unit": self.raman_activity_unit,
            "reduced_mass_amu": self.reduced_mass_amu,
            "reduced_mass_unit": self.reduced_mass_unit,
            "force_constant_mdyne_angstrom": self.force_constant_mdyne_angstrom,
            "force_constant_unit": self.force_constant_unit,
            "is_imaginary": self.is_imaginary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VibrationalMode":
        return cls(
            frequency_cm1=data.get("frequency_cm1"),
            mode_index=data.get("mode_index"),
            ir_intensity_km_mol=data.get("ir_intensity_km_mol"),
            raman_activity_angstrom4_amu=data.get("raman_activity_angstrom4_amu"),
            reduced_mass_amu=data.get("reduced_mass_amu"),
            force_constant_mdyne_angstrom=data.get(
                "force_constant_mdyne_angstrom"
            ),
            is_imaginary=data.get("is_imaginary"),
        )


@dataclass(frozen=True)
class ExcitedState:
    energy_ev: float | None
    state_index: int | None = None
    wavelength_nm: float | None = None
    oscillator_strength: float | None = None
    spin_multiplicity_label: str | None = None
    transition_description: str | None = None
    warnings: tuple[str, ...] = ()
    state_label: str | None = None

    def __post_init__(self) -> None:
        if self.state_label is None and self.spin_multiplicity_label is not None:
            object.__setattr__(self, "state_label", self.spin_multiplicity_label)

    @property
    def energy_unit(self) -> str:
        return "eV"

    @property
    def wavelength_unit(self) -> str:
        return "nm"

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_index": self.state_index,
            "energy_ev": self.energy_ev,
            "energy_unit": self.energy_unit,
            "wavelength_nm": self.wavelength_nm,
            "wavelength_unit": self.wavelength_unit,
            "oscillator_strength": self.oscillator_strength,
            "spin_multiplicity_label": self.spin_multiplicity_label,
            "transition_description": self.transition_description,
            "warnings": list(self.warnings),
            "state_label": self.state_label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExcitedState":
        return cls(
            energy_ev=data.get("energy_ev"),
            state_index=data.get("state_index"),
            wavelength_nm=data.get("wavelength_nm"),
            oscillator_strength=data.get("oscillator_strength"),
            spin_multiplicity_label=data.get("spin_multiplicity_label"),
            transition_description=data.get("transition_description"),
            warnings=tuple(data.get("warnings", [])),
            state_label=data.get("state_label"),
        )


ElectronicExcitation = ExcitedState


@dataclass(frozen=True)
class DipoleMoment:
    x_debye: float | None = None
    y_debye: float | None = None
    z_debye: float | None = None
    total_debye: float | None = None
    source_backend: str | None = None
    source_section_label: str | None = None

    @property
    def unit(self) -> str:
        return "Debye"

    def to_dict(self) -> dict[str, Any]:
        return {
            "x_debye": self.x_debye,
            "y_debye": self.y_debye,
            "z_debye": self.z_debye,
            "total_debye": self.total_debye,
            "unit": self.unit,
            "source_backend": self.source_backend,
            "source_section_label": self.source_section_label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DipoleMoment":
        return cls(
            x_debye=data.get("x_debye"),
            y_debye=data.get("y_debye"),
            z_debye=data.get("z_debye"),
            total_debye=data.get("total_debye"),
            source_backend=data.get("source_backend"),
            source_section_label=data.get("source_section_label"),
        )


@dataclass(frozen=True)
class AtomicCharge:
    atom_index: int
    symbol: str | None = None
    charge_e: float | None = None
    scheme: str | None = None
    atom_label: str | None = None
    method: str | None = None

    def __post_init__(self) -> None:
        if self.scheme is None and self.method is not None:
            object.__setattr__(self, "scheme", self.method)
        if self.method is None and self.scheme is not None:
            object.__setattr__(self, "method", self.scheme)

    @property
    def charge_unit(self) -> str:
        return "e"

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_index": self.atom_index,
            "symbol": self.symbol,
            "charge_e": self.charge_e,
            "charge_unit": self.charge_unit,
            "scheme": self.scheme,
            "atom_label": self.atom_label,
            "method": self.method,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AtomicCharge":
        return cls(
            atom_index=int(data["atom_index"]),
            symbol=data.get("symbol"),
            charge_e=data.get("charge_e"),
            scheme=data.get("scheme") or data.get("method"),
            atom_label=data.get("atom_label"),
            method=data.get("method"),
        )


@dataclass(frozen=True)
class PopulationAnalysis:
    scheme: str
    atomic_charges: tuple[AtomicCharge, ...] = ()
    warnings: tuple[str, ...] = ()
    source_backend: str | None = None
    source_section_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheme": self.scheme,
            "atomic_charges": [charge.to_dict() for charge in self.atomic_charges],
            "warnings": list(self.warnings),
            "source_backend": self.source_backend,
            "source_section_label": self.source_section_label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PopulationAnalysis":
        return cls(
            scheme=data["scheme"],
            atomic_charges=tuple(
                AtomicCharge.from_dict(item)
                for item in data.get("atomic_charges", [])
            ),
            warnings=tuple(data.get("warnings", [])),
            source_backend=data.get("source_backend"),
            source_section_label=data.get("source_section_label"),
        )


@dataclass(frozen=True)
class MolecularOrbital:
    index: int
    energy_hartree: float | None = None
    energy_ev: float | None = None
    occupation: float | None = None
    spin_channel: str | None = None
    symmetry_label: str | None = None

    @property
    def hartree_unit(self) -> str:
        return "Hartree"

    @property
    def ev_unit(self) -> str:
        return "eV"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "energy_hartree": self.energy_hartree,
            "energy_hartree_unit": self.hartree_unit,
            "energy_ev": self.energy_ev,
            "energy_ev_unit": self.ev_unit,
            "occupation": self.occupation,
            "spin_channel": self.spin_channel,
            "symmetry_label": self.symmetry_label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MolecularOrbital":
        return cls(
            index=int(data["index"]),
            energy_hartree=data.get("energy_hartree"),
            energy_ev=data.get("energy_ev"),
            occupation=data.get("occupation"),
            spin_channel=data.get("spin_channel"),
            symmetry_label=data.get("symmetry_label"),
        )


@dataclass(frozen=True)
class OrbitalTable:
    backend: str | None = None
    orbitals: tuple[MolecularOrbital, ...] = ()
    homo_index: int | None = None
    lumo_index: int | None = None
    warnings: tuple[str, ...] = ()
    source_section_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "orbitals": [orbital.to_dict() for orbital in self.orbitals],
            "homo_index": self.homo_index,
            "lumo_index": self.lumo_index,
            "warnings": list(self.warnings),
            "source_section_label": self.source_section_label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "OrbitalTable | None":
        if not data:
            return None
        return cls(
            backend=data.get("backend"),
            orbitals=tuple(
                MolecularOrbital.from_dict(item) for item in data.get("orbitals", [])
            ),
            homo_index=data.get("homo_index"),
            lumo_index=data.get("lumo_index"),
            warnings=tuple(data.get("warnings", [])),
            source_section_label=data.get("source_section_label"),
        )


@dataclass(frozen=True)
class CalculationProperties:
    vibrational_modes: tuple[VibrationalMode, ...] = ()
    excitations: tuple[ExcitedState, ...] = ()
    dipole_moment: DipoleMoment | None = None
    atomic_charges: tuple[AtomicCharge, ...] = ()
    population_analyses: tuple[PopulationAnalysis, ...] = ()
    orbital_table: OrbitalTable | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def excited_states(self) -> tuple[ExcitedState, ...]:
        return self.excitations

    def to_dict(self) -> dict[str, Any]:
        excited_states = [excitation.to_dict() for excitation in self.excitations]
        return {
            "vibrational_modes": [
                mode.to_dict() for mode in self.vibrational_modes
            ],
            "excited_states": excited_states,
            "excitations": excited_states,
            "dipole_moment": (
                self.dipole_moment.to_dict() if self.dipole_moment else None
            ),
            "atomic_charges": [
                charge.to_dict() for charge in self.atomic_charges
            ],
            "population_analyses": [
                analysis.to_dict() for analysis in self.population_analyses
            ],
            "orbital_table": (
                self.orbital_table.to_dict() if self.orbital_table else None
            ),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CalculationProperties":
        if not data:
            return cls()
        dipole_data = data.get("dipole_moment")
        excitation_data = data.get("excited_states", data.get("excitations", []))
        population_analyses = tuple(
            PopulationAnalysis.from_dict(item)
            for item in data.get("population_analyses", [])
        )
        atomic_charges = tuple(
            AtomicCharge.from_dict(item)
            for item in data.get("atomic_charges", [])
        )
        if not population_analyses and atomic_charges:
            schemes = sorted(
                {charge.scheme for charge in atomic_charges if charge.scheme}
            )
            population_analyses = tuple(
                PopulationAnalysis(
                    scheme=scheme,
                    atomic_charges=tuple(
                        charge for charge in atomic_charges if charge.scheme == scheme
                    ),
                )
                for scheme in schemes
            )
        return cls(
            vibrational_modes=tuple(
                VibrationalMode.from_dict(item)
                for item in data.get("vibrational_modes", [])
            ),
            excitations=tuple(
                ExcitedState.from_dict(item)
                for item in excitation_data
            ),
            dipole_moment=(
                DipoleMoment.from_dict(dipole_data) if dipole_data else None
            ),
            atomic_charges=atomic_charges,
            population_analyses=population_analyses,
            orbital_table=OrbitalTable.from_dict(data.get("orbital_table")),
            metadata=dict(data.get("metadata", {})),
        )
