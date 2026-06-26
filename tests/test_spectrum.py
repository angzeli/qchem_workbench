from __future__ import annotations

import csv

import pytest

from qchem_workbench.core.properties import CalculationProperties, VibrationalMode
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.reports.spectrum import (
    broaden_stick_spectrum,
    plot_vibrational_spectrum,
    vibrational_sticks_from_result,
)


def test_broadened_csv_generated(tmp_path):
    result = _spectrum_result()
    sticks = vibrational_sticks_from_result(result, spectrum_type="ir")

    spectrum = broaden_stick_spectrum(sticks, width_cm1=10.0, step_cm1=5.0)

    assert spectrum.wavenumbers_cm1[0] == 0.0
    assert len(spectrum.wavenumbers_cm1) == len(spectrum.intensities)
    assert max(spectrum.intensities) > 0.0
    assert spectrum.intensity_unit == "km/mol"


def test_png_and_csv_generated_from_result(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "mpl"))
    out_path = tmp_path / "water_ir.png"
    csv_path = tmp_path / "water_ir.csv"

    plot_path, written_csv_path = plot_vibrational_spectrum(
        _spectrum_result(),
        out_path,
        csv_path=csv_path,
        width_cm1=10.0,
        step_cm1=5.0,
    )

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    assert plot_path.read_bytes().startswith(b"\x89PNG")
    assert written_csv_path == csv_path
    assert rows[0].keys() == {"wavenumber_cm1", "intensity_km_mol"}


def test_missing_intensity_is_error():
    result = CalculationResult(
        species_name="water",
        backend="gaussian",
        method="b3lyp",
        basis="def2-svp",
        task="freq",
        success=True,
        properties=CalculationProperties(
            vibrational_modes=(VibrationalMode(frequency_cm1=100.0),)
        ),
    )

    with pytest.raises(ValueError, match="missing IR intensities"):
        vibrational_sticks_from_result(result, spectrum_type="ir")


def _spectrum_result() -> CalculationResult:
    return CalculationResult(
        species_name="water",
        backend="gaussian",
        method="b3lyp",
        basis="def2-svp",
        task="freq",
        success=True,
        properties=CalculationProperties(
            vibrational_modes=(
                VibrationalMode(frequency_cm1=-50.0, ir_intensity_km_mol=1.0),
                VibrationalMode(frequency_cm1=100.0, ir_intensity_km_mol=2.0),
                VibrationalMode(frequency_cm1=250.0, ir_intensity_km_mol=3.0),
            )
        ),
    )
