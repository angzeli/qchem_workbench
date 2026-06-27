from __future__ import annotations

import pytest

from qchem_workbench.backends.gaussian_parser import parse_gaussian_output
from qchem_workbench.core.units import HARTREE_TO_EV


def test_parse_gaussian_normal_termination(tmp_path):
    output_path = tmp_path / "water.log"
    output_path.write_text(
        " Entering Gaussian System\n"
        " # wb97xd/6-31g\n"
        "\n"
        " SCF Done:  E(RB3LYP) =  -76.1234567890     A.U. after 10 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.success is True
    assert result.backend == "gaussian"
    assert result.method is None
    assert result.electronic_energy_hartree == -76.1234567890
    assert result.metadata["route"] == "# wb97xd/6-31g"
    assert result.metadata["normal_termination"] is True
    assert result.source_path == output_path


def test_parse_gaussian_error_termination(tmp_path):
    output_path = tmp_path / "failed.out"
    output_path.write_text(
        " # hf/sto-3g\n"
        "\n"
        " SCF Done:  E(RHF) =  -1.0000000000     A.U. after 4 cycles\n"
        " Error termination request processed by link 9999.\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.success is False
    assert result.electronic_energy_hartree == -1.0
    assert result.metadata["error_termination"] is True
    assert any("error termination" in warning for warning in result.warnings)


def test_parse_gaussian_missing_energy(tmp_path):
    output_path = tmp_path / "missing-energy.log"
    output_path.write_text(
        " # hf/sto-3g\n\n Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.success is True
    assert result.electronic_energy_hartree is None
    assert any("SCF electronic energy" in warning for warning in result.warnings)


def test_parse_gaussian_uses_last_scf_energy(tmp_path):
    output_path = tmp_path / "multi.log"
    output_path.write_text(
        " # hf/sto-3g\n"
        "\n"
        " SCF Done:  E(RHF) =  -1.0000000000     A.U. after 4 cycles\n"
        " SCF Done:  E(RHF) =  -1.1000000000     A.U. after 5 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.electronic_energy_hartree == -1.1
    assert any("using the last value" in warning for warning in result.warnings)


def test_parse_complete_thermochemistry(tmp_path):
    output_path = tmp_path / "freq.log"
    output_path.write_text(
        " # wb97xd/6-31g freq\n"
        "\n"
        " SCF Done:  E(RB3LYP) =  -76.4000000000     A.U. after 10 cycles\n"
        " Zero-point correction=                           0.021240 (Hartree/Particle)\n"
        " Thermal correction to Energy=                    0.024117\n"
        " Thermal correction to Enthalpy=                  0.025061\n"
        " Thermal correction to Gibbs Free Energy=         0.003806\n"
        " Sum of electronic and zero-point Energies=      -76.378760\n"
        " Sum of electronic and thermal Free Energies=    -76.396194\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.zero_point_correction_hartree == 0.021240
    assert result.thermal_correction_energy_hartree == 0.024117
    assert result.thermal_correction_enthalpy_hartree == 0.025061
    assert result.thermal_correction_gibbs_hartree == 0.003806
    assert result.sum_electronic_zero_point_energy_hartree == -76.378760
    assert result.sum_electronic_thermal_free_energy_hartree == -76.396194
    assert result.gibbs_free_energy_hartree == -76.396194


def test_parse_incomplete_thermochemistry(tmp_path):
    output_path = tmp_path / "incomplete-freq.log"
    output_path.write_text(
        " # wb97xd/6-31g freq\n"
        "\n"
        " Zero-point correction=                           0.021240 (Hartree/Particle)\n"
        " Thermal correction to Gibbs Free Energy=         0.003806\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.zero_point_correction_hartree == 0.021240
    assert result.thermal_correction_energy_hartree is None
    assert result.thermal_correction_gibbs_hartree == 0.003806
    assert any(
        "Incomplete Gaussian thermochemistry" in warning
        for warning in result.warnings
    )


def test_parse_uses_last_complete_thermochemistry_section(tmp_path):
    output_path = tmp_path / "multiple-freq.log"
    section_template = (
        " Zero-point correction=                           {zero_point:.6f} (Hartree/Particle)\n"
        " Thermal correction to Energy=                    {energy:.6f}\n"
        " Thermal correction to Enthalpy=                  {enthalpy:.6f}\n"
        " Thermal correction to Gibbs Free Energy=         {gibbs:.6f}\n"
        " Sum of electronic and zero-point Energies=      {sum_zpe:.6f}\n"
        " Sum of electronic and thermal Free Energies=    {sum_gibbs:.6f}\n"
    )
    output_path.write_text(
        " # wb97xd/6-31g freq\n"
        + section_template.format(
            zero_point=0.010000,
            energy=0.020000,
            enthalpy=0.030000,
            gibbs=0.040000,
            sum_zpe=-1.010000,
            sum_gibbs=-1.040000,
        )
        + section_template.format(
            zero_point=0.011000,
            energy=0.021000,
            enthalpy=0.031000,
            gibbs=0.041000,
            sum_zpe=-1.011000,
            sum_gibbs=-1.041000,
        )
        + " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.zero_point_correction_hartree == 0.011
    assert result.sum_electronic_thermal_free_energy_hartree == -1.041
    assert any(
        "Multiple complete thermochemistry" in warning
        for warning in result.warnings
    )


def test_parse_no_imaginary_frequency(tmp_path):
    output_path = tmp_path / "real-frequencies.log"
    output_path.write_text(
        " # wb97xd/6-31g freq\n"
        " Frequencies --   100.0   250.5   3400.2\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.metadata["frequencies_cm1"] == [100.0, 250.5, 3400.2]
    assert result.metadata["negative_frequency_count"] == 0
    assert result.metadata["most_negative_frequency_cm1"] is None
    assert [mode.frequency_cm1 for mode in result.properties.vibrational_modes] == [
        100.0,
        250.5,
        3400.2,
    ]
    assert all(
        mode.is_imaginary is False for mode in result.properties.vibrational_modes
    )


def test_parse_gaussian_vibrational_spectrum_properties(tmp_path):
    output_path = tmp_path / "spectrum.log"
    output_path.write_text(
        " # wb97xd/6-31g freq\n"
        " Frequencies --   -50.0   100.0   250.0\n"
        " IR Inten    --     1.5     2.5     3.5\n"
        " Raman Activ --     0.1     0.2     0.3\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)
    modes = result.properties.vibrational_modes

    assert [mode.frequency_cm1 for mode in modes] == [-50.0, 100.0, 250.0]
    assert [mode.ir_intensity_km_mol for mode in modes] == [1.5, 2.5, 3.5]
    assert [mode.raman_activity_angstrom4_amu for mode in modes] == [0.1, 0.2, 0.3]
    assert [mode.is_imaginary for mode in modes] == [True, False, False]


def test_parse_one_imaginary_frequency(tmp_path):
    output_path = tmp_path / "one-imaginary.log"
    output_path.write_text(
        " # wb97xd/6-31g freq\n"
        " Frequencies --   -125.4   250.5   3400.2\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.metadata["negative_frequency_count"] == 1
    assert result.metadata["most_negative_frequency_cm1"] == -125.4
    assert any("Negative frequencies found" in warning for warning in result.warnings)


def test_parse_multiple_imaginary_frequencies(tmp_path):
    output_path = tmp_path / "multi-imaginary.log"
    output_path.write_text(
        " # wb97xd/6-31g freq\n"
        " Frequencies --   -25.0   -150.5   100.0\n"
        " Frequencies --   -300.2   250.5   3400.2\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.metadata["negative_frequency_count"] == 3
    assert result.metadata["most_negative_frequency_cm1"] == -300.2


def test_parse_malformed_frequency_line(tmp_path):
    output_path = tmp_path / "malformed-frequency.log"
    output_path.write_text(
        " # wb97xd/6-31g freq\n"
        " Frequencies --   bad-token   250.5\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.metadata["frequencies_cm1"] == [250.5]
    assert [mode.frequency_cm1 for mode in result.properties.vibrational_modes] == [
        250.5
    ]
    assert any("Malformed Gaussian frequency" in warning for warning in result.warnings)


def test_parse_gaussian_missing_intensities_remain_missing(tmp_path):
    output_path = tmp_path / "missing-intensity.log"
    output_path.write_text(
        " # wb97xd/6-31g freq\n"
        " Frequencies --   100.0   250.5\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.properties.vibrational_modes[0].ir_intensity_km_mol is None
    assert result.properties.vibrational_modes[0].raman_activity_angstrom4_amu is None


def test_parse_gaussian_excitation_fixture(tmp_path):
    output_path = tmp_path / "td.log"
    output_path.write_text(
        " # td b3lyp/def2svp\n"
        " Excited State   1:      Singlet-A      4.0000 eV  309.9605 nm  f=0.1234\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)
    excitation = result.properties.excitations[0]

    assert excitation.energy_ev == 4.0
    assert excitation.wavelength_nm == 309.9605
    assert excitation.oscillator_strength == 0.1234
    assert excitation.state_label == "Excited State 1: Singlet-A"


def test_parse_gaussian_excitation_computes_missing_wavelength(tmp_path):
    output_path = tmp_path / "td-computed-wavelength.log"
    output_path.write_text(
        " # td b3lyp/def2svp\n"
        " Excited State   1:      Singlet-A      2.0000 eV  f=0.0100\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.properties.excitations[0].wavelength_nm == 619.9209921660013


def test_parse_gaussian_dipole_moment(tmp_path):
    output_path = tmp_path / "dipole.log"
    output_path.write_text(
        " # wb97xd/6-31g\n"
        " Dipole moment (field-independent basis, Debye):\n"
        "    X=     0.1000    Y=    -0.2000    Z=     1.5000  Tot=     1.5166\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)
    dipole = result.properties.dipole_moment

    assert result.success is True
    assert dipole is not None
    assert dipole.x_debye == 0.1
    assert dipole.y_debye == -0.2
    assert dipole.z_debye == 1.5
    assert dipole.total_debye == 1.5166
    assert dipole.source_backend == "gaussian"


def test_parse_gaussian_mulliken_charges(tmp_path):
    output_path = tmp_path / "mulliken.log"
    output_path.write_text(
        " # wb97xd/6-31g pop=full\n"
        " NAtoms=    3\n"
        " Mulliken charges:\n"
        "              1\n"
        "     1  O   -0.8340\n"
        "     2  H    0.4170\n"
        "     3  H    0.4170\n"
        " Sum of Mulliken charges =   0.00000\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)
    analyses = result.properties.population_analyses

    assert len(analyses) == 1
    assert analyses[0].scheme == "Mulliken"
    assert len(analyses[0].atomic_charges) == 3
    assert analyses[0].atomic_charges[0].symbol == "O"
    assert analyses[0].atomic_charges[0].charge_e == -0.834
    assert len(result.properties.atomic_charges) == 3


def test_parse_gaussian_mulliken_and_lowdin_charges(tmp_path):
    output_path = tmp_path / "charges.log"
    output_path.write_text(
        " # wb97xd/6-31g pop=full\n"
        " NAtoms=    2\n"
        " Mulliken charges:\n"
        "     1  H    0.1000\n"
        "     2  H   -0.1000\n"
        " Sum of Mulliken charges =   0.00000\n"
        " Lowdin charges:\n"
        "     1  H    0.0500\n"
        "     2  H   -0.0500\n"
        " Sum of Lowdin charges =   0.00000\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)
    analyses = {analysis.scheme: analysis for analysis in result.properties.population_analyses}

    assert set(analyses) == {"Mulliken", "Lowdin"}
    assert analyses["Lowdin"].atomic_charges[0].charge_e == 0.05


def test_parse_gaussian_malformed_charge_table_warns(tmp_path):
    output_path = tmp_path / "malformed-charges.log"
    output_path.write_text(
        " # wb97xd/6-31g pop=full\n"
        " NAtoms=    2\n"
        " Mulliken charges:\n"
        "     1  H    0.1000\n"
        "     malformed row\n"
        "     2  H   -0.1000\n"
        " Sum of Mulliken charges =   0.00000\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.success is True
    assert len(result.properties.population_analyses[0].atomic_charges) == 2
    assert any("Malformed Gaussian Mulliken charge row" in warning for warning in result.warnings)


def test_parse_gaussian_missing_charge_analysis_is_not_failure(tmp_path):
    output_path = tmp_path / "no-charges.log"
    output_path.write_text(
        " # wb97xd/6-31g\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.success is True
    assert result.properties.population_analyses == ()
    assert result.properties.atomic_charges == ()


def test_parse_gaussian_duplicate_charge_scheme_uses_last(tmp_path):
    output_path = tmp_path / "duplicate-charges.log"
    output_path.write_text(
        " # wb97xd/6-31g pop=full\n"
        " Mulliken charges:\n"
        "     1  H    0.1000\n"
        " Sum of Mulliken charges =   0.10000\n"
        " Mulliken charges:\n"
        "     1  H    0.2000\n"
        " Sum of Mulliken charges =   0.20000\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.properties.population_analyses[0].atomic_charges[0].charge_e == 0.2
    assert any("Multiple Gaussian Mulliken charge sections" in warning for warning in result.warnings)


def test_parse_gaussian_closed_shell_orbital_table(tmp_path):
    output_path = tmp_path / "orbitals.log"
    output_path.write_text(
        " # rb3lyp/6-31g\n"
        " Alpha  occ. eigenvalues --   -0.5000   -0.3000\n"
        " Alpha virt. eigenvalues --    0.1000    0.2000\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)
    table = result.properties.orbital_table

    assert table is not None
    assert len(table.orbitals) == 4
    assert table.homo_index == 2
    assert table.lumo_index == 3
    assert table.orbitals[0].energy_hartree == -0.5
    assert table.orbitals[0].energy_ev == pytest.approx(-0.5 * HARTREE_TO_EV)
    assert result.homo_ev == pytest.approx(-0.3 * HARTREE_TO_EV)
    assert result.lumo_ev == pytest.approx(0.1 * HARTREE_TO_EV)
    assert result.gap_ev == pytest.approx(0.4 * HARTREE_TO_EV)


def test_parse_gaussian_unrestricted_alpha_beta_orbitals(tmp_path):
    output_path = tmp_path / "unrestricted-orbitals.log"
    output_path.write_text(
        " # ub3lyp/6-31g\n"
        " Alpha  occ. eigenvalues --   -0.6000   -0.2500\n"
        " Alpha virt. eigenvalues --    0.1200\n"
        " Beta  occ. eigenvalues --    -0.5500   -0.2000\n"
        " Beta virt. eigenvalues --     0.0800\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)
    table = result.properties.orbital_table

    assert table is not None
    assert [orbital.spin_channel for orbital in table.orbitals] == [
        "alpha",
        "alpha",
        "alpha",
        "beta",
        "beta",
        "beta",
    ]
    assert table.homo_index == 5
    assert table.lumo_index == 6
    assert result.homo_ev == pytest.approx(-0.2 * HARTREE_TO_EV)
    assert result.lumo_ev == pytest.approx(0.08 * HARTREE_TO_EV)


def test_parse_gaussian_occupied_only_orbitals_warn(tmp_path):
    output_path = tmp_path / "occupied-only.log"
    output_path.write_text(
        " # rb3lyp/6-31g\n"
        " occ. eigenvalues --   -0.5000   -0.3000\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)
    table = result.properties.orbital_table

    assert table is not None
    assert table.homo_index == 2
    assert table.lumo_index is None
    assert result.homo_ev == pytest.approx(-0.3 * HARTREE_TO_EV)
    assert result.lumo_ev is None
    assert any("Incomplete Gaussian orbital eigenvalue" in warning for warning in result.warnings)


def test_parse_gaussian_malformed_orbital_line_warns(tmp_path):
    output_path = tmp_path / "malformed-orbitals.log"
    output_path.write_text(
        " # rb3lyp/6-31g\n"
        " occ. eigenvalues --   bad-token   -0.3000\n"
        " virt. eigenvalues --   0.1000\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.properties.orbital_table is not None
    assert len(result.properties.orbital_table.orbitals) == 2
    assert any("Malformed Gaussian orbital eigenvalue" in warning for warning in result.warnings)


def test_parse_unrestricted_spin_info(tmp_path):
    output_path = tmp_path / "unrestricted.log"
    output_path.write_text(
        " # ub3lyp/6-31g\n"
        " S**2 before annihilation     0.7542,   after     0.7501\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert result.metadata["s2_before_annihilation"] == 0.7542
    assert result.metadata["s2_after_annihilation"] == 0.7501


def test_parse_missing_spin_info_is_normal(tmp_path):
    output_path = tmp_path / "closed-shell.log"
    output_path.write_text(
        " # rb3lyp/6-31g\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert "s2_before_annihilation" not in result.metadata
    assert not any("spin" in warning.lower() for warning in result.warnings)


def test_parse_malformed_spin_line(tmp_path):
    output_path = tmp_path / "malformed-spin.log"
    output_path.write_text(
        " # ub3lyp/6-31g\n"
        " S**2 before annihilation unavailable after unavailable\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )

    result = parse_gaussian_output(output_path)

    assert "s2_before_annihilation" not in result.metadata
    assert any("S**2 spin line" in warning for warning in result.warnings)
