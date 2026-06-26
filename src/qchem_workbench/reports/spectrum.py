"""Simple vibrational spectrum broadening and plotting utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from qchem_workbench.core.properties import VibrationalMode
from qchem_workbench.core.result import CalculationResult


SPECTRUM_TYPES = ("ir", "raman")


@dataclass(frozen=True)
class SpectrumStick:
    wavenumber_cm1: float
    intensity: float
    intensity_unit: str


@dataclass(frozen=True)
class BroadenedSpectrum:
    wavenumbers_cm1: tuple[float, ...]
    intensities: tuple[float, ...]
    intensity_unit: str


def vibrational_sticks_from_result(
    result: CalculationResult,
    *,
    spectrum_type: str = "ir",
) -> tuple[SpectrumStick, ...]:
    if spectrum_type not in SPECTRUM_TYPES:
        allowed = ", ".join(SPECTRUM_TYPES)
        raise ValueError(f"spectrum_type must be one of: {allowed}")

    modes = result.properties.vibrational_modes
    if not modes:
        raise ValueError(f"{result.species_name}: no vibrational modes are available")

    sticks = []
    missing_intensities = 0
    for mode in modes:
        if mode.frequency_cm1 is None or mode.frequency_cm1 <= 0.0:
            continue
        intensity = _mode_intensity(mode, spectrum_type)
        if intensity is None:
            missing_intensities += 1
            continue
        sticks.append(
            SpectrumStick(
                wavenumber_cm1=float(mode.frequency_cm1),
                intensity=float(intensity),
                intensity_unit=_intensity_unit(spectrum_type),
            )
        )

    if missing_intensities:
        raise ValueError(
            f"{result.species_name}: {missing_intensities} positive-frequency "
            f"mode(s) are missing {spectrum_type.upper()} intensities"
        )
    if not sticks:
        raise ValueError(
            f"{result.species_name}: no positive-frequency {spectrum_type.upper()} "
            "sticks are available"
        )
    return tuple(sticks)


def broaden_stick_spectrum(
    sticks: tuple[SpectrumStick, ...],
    *,
    width_cm1: float = 20.0,
    step_cm1: float = 1.0,
    start_cm1: float | None = None,
    stop_cm1: float | None = None,
) -> BroadenedSpectrum:
    if not sticks:
        raise ValueError("at least one spectrum stick is required")
    if width_cm1 <= 0.0:
        raise ValueError("width_cm1 must be positive")
    if step_cm1 <= 0.0:
        raise ValueError("step_cm1 must be positive")

    min_wavenumber = min(stick.wavenumber_cm1 for stick in sticks)
    max_wavenumber = max(stick.wavenumber_cm1 for stick in sticks)
    start = 0.0 if start_cm1 is None else float(start_cm1)
    start = min(start, max(0.0, min_wavenumber - 4.0 * width_cm1))
    stop = (
        max_wavenumber + 4.0 * width_cm1
        if stop_cm1 is None
        else float(stop_cm1)
    )
    if stop <= start:
        raise ValueError("stop_cm1 must be greater than start_cm1")

    x_values = np.arange(start, stop + step_cm1 * 0.5, step_cm1, dtype=float)
    y_values = np.zeros_like(x_values)
    for stick in sticks:
        y_values += stick.intensity * np.exp(
            -0.5 * ((x_values - stick.wavenumber_cm1) / width_cm1) ** 2
        )

    return BroadenedSpectrum(
        wavenumbers_cm1=tuple(float(value) for value in x_values),
        intensities=tuple(float(value) for value in y_values),
        intensity_unit=sticks[0].intensity_unit,
    )


def write_broadened_spectrum_csv(
    spectrum: BroadenedSpectrum,
    path: Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    intensity_header = _csv_intensity_header(spectrum.intensity_unit)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["wavenumber_cm1", intensity_header])
        for wavenumber, intensity in zip(
            spectrum.wavenumbers_cm1, spectrum.intensities
        ):
            writer.writerow([wavenumber, intensity])
    return output_path


def plot_vibrational_spectrum(
    result: CalculationResult,
    out_path: Path,
    *,
    spectrum_type: str = "ir",
    csv_path: Path | None = None,
    width_cm1: float = 20.0,
    step_cm1: float = 1.0,
) -> tuple[Path, Path]:
    sticks = vibrational_sticks_from_result(result, spectrum_type=spectrum_type)
    spectrum = broaden_stick_spectrum(
        sticks,
        width_cm1=width_cm1,
        step_cm1=step_cm1,
    )
    csv_output_path = csv_path or Path(out_path).with_suffix(".csv")
    write_broadened_spectrum_csv(spectrum, csv_output_path)
    _write_spectrum_plot(result, spectrum, out_path, spectrum_type=spectrum_type)
    return Path(out_path), csv_output_path


def _write_spectrum_plot(
    result: CalculationResult,
    spectrum: BroadenedSpectrum,
    out_path: Path,
    *,
    spectrum_type: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.plot(spectrum.wavenumbers_cm1, spectrum.intensities)
    ax.set_xlabel("Wavenumber (cm^-1)")
    ax.set_ylabel(f"{spectrum_type.upper()} intensity ({spectrum.intensity_unit})")
    ax.set_title(f"{result.species_name} {spectrum_type.upper()} spectrum")
    ax.text(
        0.02,
        0.98,
        "Broadened spectrum is a visual aid, not an experimental prediction.",
        ha="left",
        va="top",
        transform=ax.transAxes,
        fontsize="x-small",
    )
    fig.tight_layout()

    output_path = Path(out_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)


def _mode_intensity(mode: VibrationalMode, spectrum_type: str) -> float | None:
    if spectrum_type == "ir":
        return mode.ir_intensity_km_mol
    if spectrum_type == "raman":
        return mode.raman_activity_angstrom4_amu
    raise ValueError(f"unsupported spectrum type {spectrum_type!r}")


def _intensity_unit(spectrum_type: str) -> str:
    if spectrum_type == "ir":
        return "km/mol"
    if spectrum_type == "raman":
        return "angstrom^4/amu"
    raise ValueError(f"unsupported spectrum type {spectrum_type!r}")


def _csv_intensity_header(unit: str) -> str:
    if unit == "km/mol":
        return "intensity_km_mol"
    if unit == "angstrom^4/amu":
        return "intensity_angstrom4_amu"
    return "intensity"
