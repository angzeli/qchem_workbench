from __future__ import annotations

import pytest

from qchem_workbench.analysis.quality_checks import run_quality_checks
from qchem_workbench.backends.orca_parser import parse_orca_output
from qchem_workbench.core.units import HARTREE_TO_EV


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
    assert [mode.mode_index for mode in modes] == [1, 2]
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
    assert mode.mode_index == 1
    assert mode.ir_intensity_km_mol == 12.5
    assert mode.raman_activity_angstrom4_amu == 3.0


def test_parse_orca_ir_spectrum_section(tmp_path):
    output_path = tmp_path / "ir-spectrum.out"
    output_path.write_text(
        "! B3LYP def2-SVP Freq\n"
        "IR SPECTRUM\n"
        " Mode    Frequency    Intensity\n"
        "  0      100.0000     12.5000\n"
        "  1      250.0000     30.0000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    modes = result.properties.vibrational_modes

    assert [mode.frequency_cm1 for mode in modes] == [100.0, 250.0]
    assert [mode.ir_intensity_km_mol for mode in modes] == [12.5, 30.0]
    assert [mode.is_imaginary for mode in modes] == [False, False]


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


def test_parse_orca_closed_shell_orbital_table(tmp_path):
    output_path = tmp_path / "orbital-table.out"
    output_path.write_text(
        "! B3LYP def2-SVP SP\n"
        "ORBITAL ENERGIES\n"
        " NO   OCC          E(Eh)          E(eV)\n"
        "  0   2.0000      -0.5000      -13.6057\n"
        "  1   2.0000      -0.3000       -8.1634\n"
        "  2   0.0000       0.1000        2.7211\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    table = result.properties.orbital_table

    assert table is not None
    assert len(table.orbitals) == 3
    assert table.homo_index == 1
    assert table.lumo_index == 2
    assert table.orbitals[0].energy_hartree == -0.5
    assert result.homo_ev == -8.1634
    assert result.lumo_ev == 2.7211
    assert result.gap_ev == pytest.approx(10.8845)


def test_parse_orca_unrestricted_orbital_table(tmp_path):
    output_path = tmp_path / "unrestricted-orbital-table.out"
    output_path.write_text(
        "! UKS def2-SVP SP\n"
        "ALPHA ORBITALS\n"
        " NO   OCC          E(Eh)          E(eV)\n"
        "  0   1.0000      -0.5000      -13.6057\n"
        "  1   0.0000       0.1000        2.7211\n"
        "\n"
        "BETA ORBITALS\n"
        " NO   OCC          E(Eh)          E(eV)\n"
        "  0   1.0000      -0.4500      -12.2451\n"
        "  1   0.0000       0.0500        1.3606\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    table = result.properties.orbital_table

    assert table is not None
    assert [orbital.spin_channel for orbital in table.orbitals] == [
        "alpha",
        "alpha",
        "beta",
        "beta",
    ]
    assert result.homo_ev == -12.2451
    assert result.lumo_ev == 1.3606


def test_parse_orca_partial_orbital_table_warns(tmp_path):
    output_path = tmp_path / "partial-orbital-table.out"
    output_path.write_text(
        "! B3LYP def2-SVP SP\n"
        "ORBITAL ENERGIES\n"
        " NO   OCC          E(Eh)\n"
        "  0   2.0000      -0.5000\n"
        "  1   2.0000      -0.3000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    table = result.properties.orbital_table

    assert table is not None
    assert table.lumo_index is None
    assert result.homo_ev == pytest.approx(-0.3 * HARTREE_TO_EV)
    assert result.lumo_ev is None
    assert any("Incomplete ORCA orbital table" in warning for warning in result.warnings)


def test_parse_orca_missing_orbital_table_is_not_failure(tmp_path):
    output_path = tmp_path / "no-orbital-table.out"
    output_path.write_text(
        "! B3LYP def2-SVP SP\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.success is True
    assert result.properties.orbital_table is None


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


def test_parse_orca_excitation_fixture(tmp_path):
    output_path = tmp_path / "tddft.out"
    output_path.write_text(
        "! B3LYP def2-SVP TDDFT\n"
        "STATE 1: E=3.5000 eV 354.2406 nm f=0.0450\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    excitation = result.properties.excitations[0]

    assert excitation.energy_ev == 3.5
    assert excitation.wavelength_nm == 354.2406
    assert excitation.oscillator_strength == 0.045
    assert excitation.state_label == "STATE 1"


def test_parse_orca_excitation_missing_oscillator_strength(tmp_path):
    output_path = tmp_path / "tddft-no-f.out"
    output_path.write_text(
        "! B3LYP def2-SVP TDDFT\n"
        "STATE 2: E=2.0000 eV\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    excitation = result.properties.excitations[0]

    assert excitation.energy_ev == 2.0
    assert excitation.wavelength_nm == 619.9209921660013
    assert excitation.oscillator_strength is None


def test_parse_orca_dipole_moment(tmp_path):
    output_path = tmp_path / "dipole.out"
    output_path.write_text(
        "! B3LYP def2-SVP SP\n"
        "Total Dipole Moment (Debye) :    0.1000   -0.2000    1.5000\n"
        "Magnitude (Debye)          :    1.5166\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    dipole = result.properties.dipole_moment

    assert result.success is True
    assert dipole is not None
    assert dipole.x_debye == 0.1
    assert dipole.y_debye == -0.2
    assert dipole.z_debye == 1.5
    assert dipole.total_debye == 1.5166
    assert dipole.source_backend == "orca"


def test_parse_orca_mulliken_charges(tmp_path):
    output_path = tmp_path / "mulliken.out"
    output_path.write_text(
        "! B3LYP def2-SVP SP\n"
        "Number of atoms     3\n"
        "MULLIKEN ATOMIC CHARGES\n"
        "  0 O : -0.8340\n"
        "  1 H :  0.4170\n"
        "  2 H :  0.4170\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    analyses = result.properties.population_analyses

    assert len(analyses) == 1
    assert analyses[0].scheme == "Mulliken"
    assert len(analyses[0].atomic_charges) == 3
    assert analyses[0].atomic_charges[0].symbol == "O"
    assert analyses[0].atomic_charges[0].charge_e == -0.834
    assert len(result.properties.atomic_charges) == 3


def test_parse_orca_mulliken_and_lowdin_charges(tmp_path):
    output_path = tmp_path / "charges.out"
    output_path.write_text(
        "! B3LYP def2-SVP SP\n"
        "Number of atoms     2\n"
        "MULLIKEN ATOMIC CHARGES\n"
        "  0 H :  0.1000\n"
        "  1 H : -0.1000\n"
        "\n"
        "LOEWDIN ATOMIC CHARGES\n"
        "  0 H :  0.0500\n"
        "  1 H : -0.0500\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)
    analyses = {analysis.scheme: analysis for analysis in result.properties.population_analyses}

    assert set(analyses) == {"Mulliken", "Lowdin"}
    assert analyses["Lowdin"].atomic_charges[0].charge_e == 0.05


def test_parse_orca_missing_population_analysis_is_not_failure(tmp_path):
    output_path = tmp_path / "no-charges.out"
    output_path.write_text(
        "! B3LYP def2-SVP SP\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.success is True
    assert result.properties.population_analyses == ()
    assert result.properties.atomic_charges == ()


def test_parse_orca_malformed_charge_table_warns(tmp_path):
    output_path = tmp_path / "malformed-charges.out"
    output_path.write_text(
        "! B3LYP def2-SVP SP\n"
        "Number of atoms     2\n"
        "MULLIKEN ATOMIC CHARGES\n"
        "  0 H :  0.1000\n"
        "  malformed row\n"
        "  1 H : -0.1000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )

    result = parse_orca_output(output_path)

    assert result.success is True
    assert len(result.properties.population_analyses[0].atomic_charges) == 2
    assert any("Malformed ORCA Mulliken charge row" in warning for warning in result.warnings)
