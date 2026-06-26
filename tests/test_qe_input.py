from __future__ import annotations

import pytest

from qchem_workbench.backends.qe_input import (
    QEKPoints,
    QEInputSpec,
    validate_pseudopotentials_for_elements,
)


def test_valid_qe_input_spec():
    spec = QEInputSpec(
        calculation="scf",
        prefix="demo",
        pseudo_dir="pseudos",
        outdir="tmp",
        ecutwfc=40.0,
        ecutrho=320.0,
        occupations="smearing",
        smearing="mp",
        degauss=0.02,
        k_points=QEKPoints(grid=(2, 2, 1), shift=(0, 0, 0)),
        pseudopotentials={"Cu": "Cu.UPF"},
    )

    assert spec.calculation == "scf"
    assert spec.pseudopotentials == {"Cu": "Cu.UPF"}


def test_missing_pseudopotential_mapping_is_error():
    with pytest.raises(ValueError, match="pseudopotential mapping"):
        QEInputSpec(
            calculation="scf",
            prefix="demo",
            pseudo_dir="pseudos",
            outdir="tmp",
            ecutwfc=40.0,
        )


def test_missing_element_pseudopotential_mapping_is_error():
    with pytest.raises(ValueError, match="missing element"):
        validate_pseudopotentials_for_elements(
            {"Cu", "O"},
            {"Cu": "Cu.UPF"},
        )


def test_k_point_formatting():
    k_points = QEKPoints(grid=(4, 4, 2), shift=(1, 1, 0))

    assert k_points.to_lines() == [
        "K_POINTS automatic",
        "4 4 2 1 1 0",
    ]


def test_gamma_k_point_formatting():
    assert QEKPoints(mode="gamma").to_lines() == ["K_POINTS gamma"]


def test_additional_settings_are_preserved():
    spec = QEInputSpec(
        calculation="relax",
        prefix="demo",
        pseudo_dir="pseudos",
        outdir="tmp",
        ecutwfc=40.0,
        pseudopotentials={"H": "H.UPF"},
        additional_settings={
            "system": {"nosym": True},
            "electrons": {"conv_thr": 1e-8},
        },
    )

    assert spec.additional_settings == {
        "system": {"nosym": True},
        "electrons": {"conv_thr": 1e-8},
    }
