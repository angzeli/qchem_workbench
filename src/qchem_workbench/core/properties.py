"""Backend-independent parsed molecular property models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


EV_NM_PRODUCT = 1239.8419843320026


def wavelength_nm_from_ev(energy_ev: float) -> float:
    if energy_ev <= 0.0:
        raise ValueError("energy_ev must be positive")
    return EV_NM_PRODUCT / energy_ev


@dataclass(frozen=True)
class VibrationalMode:
    frequency_cm1: float | None
    ir_intensity_km_mol: float | None = None
    raman_activity_angstrom4_amu: float | None = None
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "frequency_cm1": self.frequency_cm1,
            "frequency_unit": self.frequency_unit,
            "ir_intensity_km_mol": self.ir_intensity_km_mol,
            "ir_intensity_unit": self.ir_intensity_unit,
            "raman_activity_angstrom4_amu": self.raman_activity_angstrom4_amu,
            "raman_activity_unit": self.raman_activity_unit,
            "is_imaginary": self.is_imaginary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VibrationalMode":
        return cls(
            frequency_cm1=data.get("frequency_cm1"),
            ir_intensity_km_mol=data.get("ir_intensity_km_mol"),
            raman_activity_angstrom4_amu=data.get("raman_activity_angstrom4_amu"),
            is_imaginary=data.get("is_imaginary"),
        )


@dataclass(frozen=True)
class ElectronicExcitation:
    energy_ev: float | None
    wavelength_nm: float | None = None
    oscillator_strength: float | None = None
    state_label: str | None = None

    @property
    def energy_unit(self) -> str:
        return "eV"

    @property
    def wavelength_unit(self) -> str:
        return "nm"

    def to_dict(self) -> dict[str, Any]:
        return {
            "energy_ev": self.energy_ev,
            "energy_unit": self.energy_unit,
            "wavelength_nm": self.wavelength_nm,
            "wavelength_unit": self.wavelength_unit,
            "oscillator_strength": self.oscillator_strength,
            "state_label": self.state_label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ElectronicExcitation":
        return cls(
            energy_ev=data.get("energy_ev"),
            wavelength_nm=data.get("wavelength_nm"),
            oscillator_strength=data.get("oscillator_strength"),
            state_label=data.get("state_label"),
        )


@dataclass(frozen=True)
class DipoleMoment:
    x_debye: float | None = None
    y_debye: float | None = None
    z_debye: float | None = None
    total_debye: float | None = None

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
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DipoleMoment":
        return cls(
            x_debye=data.get("x_debye"),
            y_debye=data.get("y_debye"),
            z_debye=data.get("z_debye"),
            total_debye=data.get("total_debye"),
        )


@dataclass(frozen=True)
class AtomicCharge:
    atom_index: int
    symbol: str | None = None
    charge_e: float | None = None
    method: str | None = None

    @property
    def charge_unit(self) -> str:
        return "e"

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_index": self.atom_index,
            "symbol": self.symbol,
            "charge_e": self.charge_e,
            "charge_unit": self.charge_unit,
            "method": self.method,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AtomicCharge":
        return cls(
            atom_index=int(data["atom_index"]),
            symbol=data.get("symbol"),
            charge_e=data.get("charge_e"),
            method=data.get("method"),
        )


@dataclass(frozen=True)
class CalculationProperties:
    vibrational_modes: tuple[VibrationalMode, ...] = ()
    excitations: tuple[ElectronicExcitation, ...] = ()
    dipole_moment: DipoleMoment | None = None
    atomic_charges: tuple[AtomicCharge, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vibrational_modes": [
                mode.to_dict() for mode in self.vibrational_modes
            ],
            "excitations": [
                excitation.to_dict() for excitation in self.excitations
            ],
            "dipole_moment": (
                self.dipole_moment.to_dict() if self.dipole_moment else None
            ),
            "atomic_charges": [
                charge.to_dict() for charge in self.atomic_charges
            ],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CalculationProperties":
        if not data:
            return cls()
        dipole_data = data.get("dipole_moment")
        return cls(
            vibrational_modes=tuple(
                VibrationalMode.from_dict(item)
                for item in data.get("vibrational_modes", [])
            ),
            excitations=tuple(
                ElectronicExcitation.from_dict(item)
                for item in data.get("excitations", [])
            ),
            dipole_moment=(
                DipoleMoment.from_dict(dipole_data) if dipole_data else None
            ),
            atomic_charges=tuple(
                AtomicCharge.from_dict(item)
                for item in data.get("atomic_charges", [])
            ),
            metadata=dict(data.get("metadata", {})),
        )
