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
