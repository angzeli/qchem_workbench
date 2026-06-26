from __future__ import annotations

import pytest

from qchem_workbench.backends.qe_parser import RYDBERG_TO_HARTREE, parse_qe_output


def test_parse_qe_completed_scf_output(tmp_path):
    output_path = tmp_path / "cu.out"
    output_path.write_text(
        "number of atoms/cell      = 1\n"
        "CELL_PARAMETERS (angstrom)\n"
        " 3.6 0.0 0.0\n"
        " 0.0 3.6 0.0\n"
        " 0.0 0.0 3.6\n"
        "     convergence has been achieved in 6 iterations\n"
        "!    total energy              =     -114.000000 Ry\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)

    assert result.backend == "qe"
    assert result.success is True
    assert result.electronic_energy_hartree == -114.0 * RYDBERG_TO_HARTREE
    assert result.metadata["total_energy_ry"] == -114.0
    assert result.metadata["n_atoms"] == 1
    assert result.metadata["cell"][0] == [3.6, 0.0, 0.0]
    assert result.source_path == output_path


def test_parse_qe_incomplete_output(tmp_path):
    output_path = tmp_path / "incomplete.out"
    output_path.write_text(
        "number of atoms/cell      = 2\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)

    assert result.success is False
    assert result.electronic_energy_hartree is None
    assert "QE job completion marker was not found." in result.warnings
    assert "QE total energy was not found." in result.warnings


def test_parse_qe_non_converged_output(tmp_path):
    output_path = tmp_path / "not_converged.out"
    output_path.write_text(
        "     convergence NOT achieved after 100 iterations\n"
        "!    total energy              =     -10.000000 Ry\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)

    assert result.success is False
    assert result.metadata["scf_converged"] is False
    assert "QE SCF convergence was not achieved." in result.warnings


def test_parse_qe_force_output(tmp_path):
    output_path = tmp_path / "forces.out"
    output_path.write_text(
        "     convergence has been achieved in 4 iterations\n"
        "!    total energy              =     -20.000000 Ry\n"
        "Maximum force = 0.0012 Ry/bohr\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)

    assert result.success is True
    assert result.metadata["max_force"] == pytest.approx(0.0012)
    assert result.metadata["max_force_unit"] == "Ry/bohr"
