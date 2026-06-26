from __future__ import annotations

from qchem_workbench.analysis.quality_checks import run_quality_checks
from qchem_workbench.backends.orca_parser import parse_orca_output


def test_parse_orca_normal_completion_fixture(tmp_path):
    output_path = tmp_path / "water.out"
    output_path.write_text(
        "! B3LYP def2-SVP SP\n"
        "FINAL SINGLE POINT ENERGY     -76.1000000000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.species_name == "water"
    assert result.backend == "orca"
    assert result.method == "B3LYP"
    assert result.basis == "def2-SVP"
    assert result.task == "single_point"
    assert result.success is True
    assert result.electronic_energy_hartree == -76.1
    assert result.source_path == output_path
    assert result.metadata["normal_termination"] is True
    assert result.metadata["route"] == "! B3LYP def2-SVP SP"


def test_parse_orca_incomplete_error_fixture(tmp_path):
    output_path = tmp_path / "failed.out"
    output_path.write_text(
        "! B3LYP def2-SVP Opt\n"
        "ORCA TERMINATED WITH ERROR\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.success is False
    assert result.task == "opt"
    assert result.electronic_energy_hartree is None
    assert result.metadata["error_termination"] is True
    assert "ORCA normal termination not found." in result.warnings
    assert "ORCA error termination found." in result.warnings


def test_parse_orca_missing_energy_fixture(tmp_path):
    output_path = tmp_path / "no_energy.out"
    output_path.write_text(
        "! PBE0 def2-TZVP Freq\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.success is True
    assert result.task == "freq"
    assert result.electronic_energy_hartree is None
    assert "ORCA final single-point energy was not found." in result.warnings


def test_parse_orca_multiple_energy_lines_use_final_value(tmp_path):
    output_path = tmp_path / "opt.out"
    output_path.write_text(
        "! B3LYP def2-SVP Opt Freq\n"
        "FINAL SINGLE POINT ENERGY     -75.0000000000\n"
        "FINAL SINGLE POINT ENERGY     -76.0000000000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.task == "opt_freq"
    assert result.electronic_energy_hartree == -76.0
    assert any("using the last value" in warning for warning in result.warnings)


def test_parse_orca_frequency_thermochemistry_fixture(tmp_path):
    output_path = tmp_path / "freq.out"
    output_path.write_text(
        "! B3LYP def2-SVP Freq\n"
        "FINAL SINGLE POINT ENERGY     -76.0000000000\n"
        "VIBRATIONAL FREQUENCIES\n"
        "  0:        100.0000 cm**-1\n"
        "  1:        250.0000 cm**-1\n"
        "Zero point energy                  0.010000 Eh\n"
        "Thermal correction to Energy       0.020000 Eh\n"
        "Thermal correction to Enthalpy     0.021000 Eh\n"
        "Thermal correction to Gibbs Free Energy 0.005000 Eh\n"
        "Final Gibbs free energy          -75.995000 Eh\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.metadata["frequencies_cm1"] == [100.0, 250.0]
    assert [mode.frequency_cm1 for mode in result.properties.vibrational_modes] == [
        100.0,
        250.0,
    ]
    assert result.metadata["negative_frequency_count"] == 0
    assert result.zero_point_correction_hartree == 0.01
    assert result.thermal_correction_energy_hartree == 0.02
    assert result.thermal_correction_enthalpy_hartree == 0.021
    assert result.thermal_correction_gibbs_hartree == 0.005
    assert result.gibbs_free_energy_hartree == -75.995


def test_parse_orca_vibrational_spectrum_properties(tmp_path):
    output_path = tmp_path / "spectrum.out"
    output_path.write_text(
        "! B3LYP def2-SVP Freq\n"
        "Frequencies --   -12.5   100.0\n"
        "IR Intensities --  1.2     2.3\n"
        "Raman Activities -- 0.4     0.5\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    modes = result.properties.vibrational_modes

    assert [mode.frequency_cm1 for mode in modes] == [-12.5, 100.0]
    assert [mode.ir_intensity_km_mol for mode in modes] == [1.2, 2.3]
    assert [mode.raman_activity_angstrom4_amu for mode in modes] == [0.4, 0.5]
    assert [mode.is_imaginary for mode in modes] == [True, False]


def test_parse_orca_row_vibrational_properties(tmp_path):
    output_path = tmp_path / "row-spectrum.out"
    output_path.write_text(
        "! B3LYP def2-SVP Freq\n"
        "  0:        100.0000 cm**-1  IR=12.5  Raman=3.0\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    mode = result.properties.vibrational_modes[0]

    assert mode.frequency_cm1 == 100.0
    assert mode.ir_intensity_km_mol == 12.5
    assert mode.raman_activity_angstrom4_amu == 3.0


def test_parse_orca_imaginary_frequency_quality_metadata(tmp_path):
    output_path = tmp_path / "imaginary.out"
    output_path.write_text(
        "! B3LYP def2-SVP Freq\n"
        "FINAL SINGLE POINT ENERGY     -10.0000000000\n"
        "Frequencies --   -12.5   100.0\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    checks = run_quality_checks([result])

    assert result.metadata["negative_frequency_count"] == 1
    assert result.properties.vibrational_modes[0].is_imaginary is True
    assert result.metadata["most_negative_frequency_cm1"] == -12.5
    assert any("Negative frequencies found" in warning for warning in result.warnings)
    assert any(check.code == "imaginary_frequencies_present" for check in checks)


def test_parse_orca_orbital_and_spin_fixture(tmp_path):
    output_path = tmp_path / "orbitals.out"
    output_path.write_text(
        "! UKS def2-SVP SP\n"
        "FINAL SINGLE POINT ENERGY     -20.0000000000\n"
        "HOMO ENERGY    -6.1000 eV\n"
        "LUMO ENERGY    -1.2000 eV\n"
        "Expectation value of <S**2>     : 0.7520\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.homo_ev == -6.1
    assert result.lumo_ev == -1.2
    assert result.gap_ev == 4.8999999999999995
    assert result.metadata["s2_before_annihilation"] == 0.752


def test_parse_orca_incomplete_thermochemistry_fixture(tmp_path):
    output_path = tmp_path / "incomplete_thermo.out"
    output_path.write_text(
        "! B3LYP def2-SVP Freq\n"
        "FINAL SINGLE POINT ENERGY     -76.0000000000\n"
        "Zero point correction 0.010000 Eh\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.zero_point_correction_hartree == 0.01
    assert result.thermal_correction_gibbs_hartree is None
    assert "Incomplete ORCA thermochemistry section found." in result.warnings


def test_parse_orca_missing_intensities_remain_missing(tmp_path):
    output_path = tmp_path / "missing-intensity.out"
    output_path.write_text(
        "! B3LYP def2-SVP Freq\n"
        "Frequencies --   100.0\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.properties.vibrational_modes[0].ir_intensity_km_mol is None
    assert result.properties.vibrational_modes[0].raman_activity_angstrom4_amu is None


def test_parse_orca_malformed_vibrational_line(tmp_path):
    output_path = tmp_path / "malformed-spectrum.out"
    output_path.write_text(
        "! B3LYP def2-SVP Freq\n"
        "Frequencies --   bad-token   100.0\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert [mode.frequency_cm1 for mode in result.properties.vibrational_modes] == [
        100.0
    ]
    assert "Malformed ORCA frequency value(s) were ignored." in result.warnings
