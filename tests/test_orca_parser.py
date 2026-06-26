from __future__ import annotations

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
