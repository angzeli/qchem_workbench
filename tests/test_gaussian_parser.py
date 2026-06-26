from __future__ import annotations

from qchem_workbench.backends.gaussian_parser import parse_gaussian_output


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
