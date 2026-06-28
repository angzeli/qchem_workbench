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


def test_parse_qe_atomic_forces_and_total_force(tmp_path):
    output_path = tmp_path / "atomic_forces.out"
    output_path.write_text(
        "     convergence has been achieved in 4 iterations\n"
        "!    total energy              =     -20.000000 Ry\n"
        "     atom    1 type  1   force =     0.001000  -0.002000   0.000000\n"
        "     atom    2 type  1   force =    -0.001000   0.002000   0.000000\n"
        "     total force =     0.002236 Ry/bohr\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)
    forces = result.metadata["atomic_forces"]["forces"]

    assert result.success is True
    assert result.metadata["atomic_forces"]["unit"] == "Ry/bohr"
    assert result.metadata["atomic_forces"]["converted_unit"] == "eV/angstrom"
    assert len(forces) == 2
    assert forces[0]["atom_index"] == 1
    assert forces[0]["magnitude_ry_bohr"] == pytest.approx(0.0022360679)
    assert forces[0]["magnitude_ev_angstrom"] is not None
    assert result.metadata["total_force"]["unit"] == "Ry/bohr"


def test_parse_qe_stress_tensor(tmp_path):
    output_path = tmp_path / "stress.out"
    output_path.write_text(
        "     convergence has been achieved in 4 iterations\n"
        "!    total energy              =     -20.000000 Ry\n"
        "total   stress  (Ry/bohr**3)                   (kbar)     P=   12.34\n"
        "   0.001  0.000  0.000     1.0  0.0  0.0\n"
        "   0.000  0.002  0.000     0.0  2.0  0.0\n"
        "   0.000  0.000  0.003     0.0  0.0  3.0\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)

    assert result.metadata["stress"]["unit"] == "Ry/bohr**3"
    assert result.metadata["stress"]["pressure"] == pytest.approx(12.34)
    assert result.metadata["stress"]["pressure_unit"] == "kbar"
    assert result.metadata["stress"]["tensor"][2] == [0.0, 0.0, 0.003]


def test_parse_qe_magnetisation(tmp_path):
    output_path = tmp_path / "mag.out"
    output_path.write_text(
        "     convergence has been achieved in 4 iterations\n"
        "!    total energy              =     -20.000000 Ry\n"
        "     total magnetization       =     1.00 Bohr mag/cell\n"
        "     absolute magnetization    =     1.25 Bohr mag/cell\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)

    assert result.metadata["magnetisation"]["total_magnetisation"] == 1.0
    assert result.metadata["magnetisation"]["absolute_magnetisation"] == 1.25
    assert (
        result.metadata["magnetisation"]["total_magnetisation_unit"]
        == "Bohr mag/cell"
    )


def test_parse_qe_malformed_force_line_warns(tmp_path):
    output_path = tmp_path / "bad_force.out"
    output_path.write_text(
        "     convergence has been achieved in 4 iterations\n"
        "!    total energy              =     -20.000000 Ry\n"
        "     atom bad type  1   force =     not-a-number\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)

    assert "Malformed QE atomic force row(s) were ignored." in result.warnings


def test_parse_qe_completed_relax_trajectory(tmp_path):
    output_path = tmp_path / "relax.out"
    output_path.write_text(
        "number of atoms/cell      = 1\n"
        "     convergence has been achieved in 4 iterations\n"
        "!    total energy              =     -20.000000 Ry\n"
        "Maximum force = 0.0100 Ry/bohr\n"
        "     convergence has been achieved in 5 iterations\n"
        "!    total energy              =     -21.000000 Ry\n"
        "Maximum force = 0.0010 Ry/bohr\n"
        "ATOMIC_POSITIONS (angstrom)\n"
        "Cu 0.0 0.0 0.1\n"
        "\n"
        "End of BFGS Geometry Optimization\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)
    trajectory = result.metadata["relaxation_trajectory"]

    assert result.success is True
    assert len(trajectory["steps"]) == 2
    assert trajectory["steps"][0]["total_energy_ry"] == -20.0
    assert trajectory["final_total_energy_ry"] == -21.0
    assert trajectory["final_max_force"] == pytest.approx(0.001)
    assert trajectory["relaxation_converged"] is True
    assert trajectory["final_atomic_positions"]["unit"] == "angstrom"
    assert trajectory["final_atomic_positions"]["atoms"][0]["z"] == pytest.approx(0.1)


def test_parse_qe_incomplete_relax_keeps_partial_trajectory(tmp_path):
    output_path = tmp_path / "incomplete_relax.out"
    output_path.write_text(
        "!    total energy              =     -20.000000 Ry\n"
        "Maximum force = 0.0100 Ry/bohr\n"
        "!    total energy              =     -20.100000 Ry\n"
        "Maximum force = 0.0080 Ry/bohr\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)

    assert result.success is False
    assert result.metadata["relaxation_trajectory"]["steps"][0]["max_force"] == 0.01
    assert "QE job completion marker was not found." in result.warnings
    assert (
        "QE relaxation trajectory has no final atomic positions."
        in result.warnings
    )


def test_parse_qe_vc_relax_final_cell_uses_last_block(tmp_path):
    output_path = tmp_path / "vc_relax.out"
    output_path.write_text(
        "CELL_PARAMETERS (angstrom)\n"
        "3.0 0.0 0.0\n"
        "0.0 3.0 0.0\n"
        "0.0 0.0 10.0\n"
        "!    total energy              =     -20.000000 Ry\n"
        "CELL_PARAMETERS (angstrom)\n"
        "3.1 0.0 0.0\n"
        "0.0 3.1 0.0\n"
        "0.0 0.0 10.5\n"
        "!    total energy              =     -20.500000 Ry\n"
        "ATOMIC_POSITIONS (angstrom)\n"
        "Cu 0.0 0.0 0.2\n"
        "bfgs converged in 2 scf cycles\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)
    trajectory = result.metadata["relaxation_trajectory"]

    assert result.metadata["cell"][0] == [3.1, 0.0, 0.0]
    assert trajectory["final_cell"]["vectors"][2] == [0.0, 0.0, 10.5]
    assert trajectory["relaxation_converged"] is True


def test_parse_qe_non_converged_relaxation(tmp_path):
    output_path = tmp_path / "non_converged_relax.out"
    output_path.write_text(
        "!    total energy              =     -20.000000 Ry\n"
        "Maximum force = 0.0500 Ry/bohr\n"
        "relaxation NOT converged\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )

    result = parse_qe_output(output_path)

    assert result.success is False
    assert result.metadata["relaxation_trajectory"]["relaxation_converged"] is False
    assert "QE relaxation convergence was not achieved." in result.warnings
