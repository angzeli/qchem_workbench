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
