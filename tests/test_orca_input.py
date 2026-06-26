from __future__ import annotations

import pytest

from qchem_workbench.backends.orca_input import (
    ORCAInputOptions,
    orca_route_from_spec,
    render_orca_input,
)
from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.species import Species


def test_render_orca_input_for_water(tmp_path):
    xyz_path = tmp_path / "water.xyz"
    xyz_path.write_text(
        "3\n"
        "synthetic fixture water geometry\n"
        "O 0 0 0\n"
        "H 0 0.757 0.586\n"
        "H 0 -0.757 0.586\n",
        encoding="utf-8",
    )
    species = Species(
        name="water",
        formula="H2O",
        charge=0,
        multiplicity=1,
        geometry_path=xyz_path,
    )
    spec = CalculationSpec(
        backend="orca",
        method="b3lyp",
        basis="def2-svp",
        task="single_point",
    )

    rendered = render_orca_input(
        species,
        spec,
        ORCAInputOptions(title="water single point"),
    )

    assert rendered == (
        "# water single point\n"
        "! b3lyp def2-svp SP\n"
        "* xyz 0 1\n"
        "O 0 0 0\n"
        "H 0 0.757 0.586\n"
        "H 0 -0.757 0.586\n"
        "*\n"
    )


def test_render_orca_input_uses_spec_charge_and_multiplicity(tmp_path):
    xyz_path = tmp_path / "oxygen.xyz"
    xyz_path.write_text(
        "1\nsynthetic fixture oxygen atom geometry\nO 0 0 0\n",
        encoding="utf-8",
    )
    species = Species(
        name="oxygen_anion",
        formula="O",
        charge=0,
        multiplicity=1,
        geometry_path=xyz_path,
    )
    spec = CalculationSpec(
        backend="orca",
        method="b3lyp",
        basis="def2-svp",
        task="single_point",
        charge=-1,
        multiplicity=2,
    )

    rendered = render_orca_input(species, spec, ORCAInputOptions())

    assert "\n* xyz -1 2\n" in rendered


@pytest.mark.parametrize(
    ("task", "expected_route"),
    [
        ("single_point", "! wb97xd def2-svp SP"),
        ("opt", "! wb97xd def2-svp Opt"),
        ("freq", "! wb97xd def2-svp Freq"),
        ("opt_freq", "! wb97xd def2-svp Opt Freq"),
    ],
)
def test_orca_route_task_presets(task, expected_route):
    spec = CalculationSpec(
        backend="orca",
        method="wb97xd",
        basis="def2-svp",
        task=task,
    )

    assert orca_route_from_spec(spec) == expected_route


def test_render_orca_input_pal_maxcore_and_blocks(tmp_path):
    xyz_path = tmp_path / "co2.xyz"
    xyz_path.write_text(
        "3\n"
        "synthetic fixture carbon dioxide geometry\n"
        "C 0 0 0\n"
        "O 0 0 1.16\n"
        "O 0 0 -1.16\n",
        encoding="utf-8",
    )
    species = Species(
        name="carbon_dioxide",
        formula="CO2",
        charge=0,
        multiplicity=1,
        geometry_path=xyz_path,
    )
    spec = CalculationSpec(
        backend="orca",
        method="b3lyp",
        basis="def2-svp",
        task="opt_freq",
    )

    rendered = render_orca_input(
        species,
        spec,
        ORCAInputOptions(
            pal_nprocs=4,
            maxcore_mb=2000,
            blocks={"scf": "  MaxIter 200"},
        ),
    )

    assert "%pal\n  nprocs 4\nend\n" in rendered
    assert "%maxcore 2000\n" in rendered
    assert "%scf\n  MaxIter 200\nend\n" in rendered
    assert rendered.endswith("O 0 0 -1.16\n*\n")


def test_orca_route_rejects_unknown_task():
    spec = CalculationSpec(
        backend="orca",
        method="wb97xd",
        basis="def2-svp",
        task="unknown",
    )

    with pytest.raises(ValueError, match="unsupported ORCA task"):
        orca_route_from_spec(spec)


def test_orca_route_rejects_solvent_shortcut():
    spec = CalculationSpec(
        backend="orca",
        method="wb97xd",
        basis="def2-svp",
        task="single_point",
        solvent="water",
    )

    with pytest.raises(ValueError, match="explicit ORCA blocks"):
        orca_route_from_spec(spec)
