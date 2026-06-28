from __future__ import annotations

import pytest

from qchem_workbench.analysis.convergence import (
    convergence_table,
    generate_convergence_settings,
    load_convergence_study,
)
from qchem_workbench.core.result import CalculationResult


def test_valid_cutoff_study(tmp_path):
    path = _write_convergence_study(tmp_path)

    study = load_convergence_study(path)

    assert study.name == "synthetic cutoff test"
    assert study.variable.type == "ecutwfc"
    assert study.variable.values == (40, 50, 60)
    assert study.fixed_settings["ecutrho"] == 480
    assert study.tolerance is not None
    assert study.tolerance.unit == "eV_per_atom"


def test_valid_k_point_study_and_settings_generation(tmp_path):
    path = _write_convergence_study(
        tmp_path,
        variable=(
            "    type: kpoints\n"
            "    values:\n"
            "      - [2, 2, 1]\n"
            "      - [3, 3, 1]\n"
        ),
    )

    study = load_convergence_study(path)
    settings = generate_convergence_settings(study)

    assert settings == [
        {"ecutrho": 480, "kpoints": [2, 2, 1]},
        {"ecutrho": 480, "kpoints": [3, 3, 1]},
    ]


def test_missing_tolerance_is_error(tmp_path):
    path = tmp_path / "convergence.yaml"
    path.write_text(
        "schema_version: 1\n"
        "convergence_study:\n"
        "  name: synthetic bad study\n"
        "  quantity: total_energy\n"
        "  variable:\n"
        "    type: ecutwfc\n"
        "    values: [40, 50]\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="tolerance must be provided"):
        load_convergence_study(path)


def test_convergence_table_from_synthetic_results(tmp_path):
    study = load_convergence_study(_write_convergence_study(tmp_path))
    rows = convergence_table(
        study,
        [
            _result(40, -100.0, n_atoms=2),
            _result(50, -100.03, n_atoms=2),
            _result(60, -100.04, n_atoms=2),
        ],
    )

    assert rows[0].delta_from_previous_ev is None
    assert rows[1].delta_from_previous_ev == pytest.approx(-0.03)
    assert rows[1].delta_from_previous_ev_per_atom == pytest.approx(-0.015)
    assert rows[1].within_tolerance is False
    assert rows[2].within_tolerance is True


def test_convergence_table_missing_result(tmp_path):
    study = load_convergence_study(_write_convergence_study(tmp_path))
    rows = convergence_table(study, [_result(40, -100.0), _result(60, -100.1)])

    assert rows[1].complete is False
    assert rows[1].missing_reason == "missing_result"


def test_convergence_table_eV_unit(tmp_path):
    study = load_convergence_study(
        _write_convergence_study(
            tmp_path,
            tolerance="    value: 0.02\n    unit: eV\n",
        )
    )
    rows = convergence_table(study, [_result(40, -100.0), _result(50, -100.01)])

    assert rows[1].within_tolerance is True


def _write_convergence_study(
    tmp_path,
    *,
    variable: str = "    type: ecutwfc\n    values: [40, 50, 60]\n",
    tolerance: str = "    value: 0.01\n    unit: eV_per_atom\n",
):
    path = tmp_path / "convergence.yaml"
    path.write_text(
        "schema_version: 1\n"
        "convergence_study:\n"
        "  name: synthetic cutoff test\n"
        "  quantity: total_energy\n"
        "  variable:\n"
        f"{variable}"
        "  fixed_settings:\n"
        "    ecutrho: 480\n"
        "  tolerance:\n"
        f"{tolerance}",
        encoding="utf-8",
    )
    return path


def _result(value, energy_ev, *, n_atoms=1):
    return CalculationResult(
        species_name=f"synthetic_{value}",
        backend="qe",
        method=None,
        basis=None,
        task="scf",
        success=True,
        metadata={
            "ecutwfc": value,
            "total_energy_ev": energy_ev,
            "n_atoms": n_atoms,
        },
    )
