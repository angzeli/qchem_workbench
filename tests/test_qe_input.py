from __future__ import annotations

import pytest

from qchem_workbench.backends.qe_input import (
    QEKPoints,
    QEInputSpec,
    render_qe_pw_input,
    validate_pseudopotentials_for_elements,
)
from qchem_workbench.core.geometry import Atom
from qchem_workbench.core.structure import AtomisticStructure


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
        atomic_masses={"Cu": 63.546},
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
        atomic_masses={"H": 1.008},
        additional_settings={
            "system": {"nosym": True},
            "electrons": {"conv_thr": 1e-8},
        },
    )

    assert spec.additional_settings == {
        "system": {"nosym": True},
        "electrons": {"conv_thr": 1e-8},
    }


def test_render_qe_pw_input_for_molecule_in_box():
    structure = AtomisticStructure(
        atoms=(Atom("H", 0.0, 0.0, 0.0), Atom("H", 0.0, 0.0, 0.74)),
        cell=((12.0, 0.0, 0.0), (0.0, 12.0, 0.0), (0.0, 0.0, 12.0)),
        metadata={"label": "synthetic fixture hydrogen molecule in box"},
    )
    spec = QEInputSpec(
        calculation="scf",
        prefix="h2",
        pseudo_dir="./pseudos",
        outdir="./tmp",
        ecutwfc=30.0,
        k_points=QEKPoints(mode="gamma"),
        pseudopotentials={"H": "H.pbe.UPF"},
        atomic_masses={"H": 1.008},
        additional_settings={"system": {"assume_isolated": "mt"}},
    )

    rendered = render_qe_pw_input(structure, spec)

    assert "&CONTROL\n  calculation = 'scf'," in rendered
    assert "  nat = 2,\n  ntyp = 1,\n  ecutwfc = 30," in rendered
    assert "  assume_isolated = 'mt'," in rendered
    assert "ATOMIC_SPECIES\nH 1.008 H.pbe.UPF\n" in rendered
    assert "ATOMIC_POSITIONS angstrom\nH 0 0 0\nH 0 0 0.74\n" in rendered
    assert "CELL_PARAMETERS angstrom\n12 0 0\n0 12 0\n0 0 12\n" in rendered
    assert rendered.endswith("K_POINTS gamma\n")


def test_render_qe_pw_input_for_periodic_cell():
    structure = AtomisticStructure(
        atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
        cell=((3.6, 0.0, 0.0), (0.0, 3.6, 0.0), (0.0, 0.0, 3.6)),
        pbc=(True, True, True),
        metadata={"label": "synthetic fixture copper cell"},
    )
    spec = QEInputSpec(
        calculation="vc-relax",
        prefix="cu",
        pseudo_dir="./pseudos",
        outdir="./tmp",
        ecutwfc=40.0,
        ecutrho=320.0,
        k_points=QEKPoints(grid=(4, 4, 4), shift=(0, 0, 0)),
        pseudopotentials={"Cu": "Cu.pbe.UPF"},
        atomic_masses={"Cu": 63.546},
    )

    rendered = render_qe_pw_input(structure, spec)

    assert "&IONS\n/\n" in rendered
    assert "&CELL\n/\n" in rendered
    assert "  ecutrho = 320," in rendered
    assert "K_POINTS automatic\n4 4 4 0 0 0\n" in rendered


def test_render_qe_pw_input_missing_pseudopotential_error():
    structure = AtomisticStructure(
        atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
        cell=((3.6, 0.0, 0.0), (0.0, 3.6, 0.0), (0.0, 0.0, 3.6)),
    )
    spec = QEInputSpec(
        calculation="scf",
        prefix="cu",
        pseudo_dir="./pseudos",
        outdir="./tmp",
        ecutwfc=40.0,
        pseudopotentials={"H": "H.UPF"},
        atomic_masses={"Cu": 63.546},
    )

    with pytest.raises(ValueError, match="missing element"):
        render_qe_pw_input(structure, spec)


def test_render_qe_pw_input_missing_cell_error():
    structure = AtomisticStructure(
        atoms=(Atom("H", 0.0, 0.0, 0.0),),
    )
    spec = QEInputSpec(
        calculation="scf",
        prefix="h",
        pseudo_dir="./pseudos",
        outdir="./tmp",
        ecutwfc=30.0,
        pseudopotentials={"H": "H.UPF"},
        atomic_masses={"H": 1.008},
    )

    with pytest.raises(ValueError, match="explicit cell"):
        render_qe_pw_input(structure, spec)
