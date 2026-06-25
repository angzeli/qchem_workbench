from __future__ import annotations

from pathlib import Path

import pytest

from qchem_workbench.backends.gaussian_input import (
    GaussianInputOptions,
    gaussian_route_from_spec,
    render_gaussian_input,
)
from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.species import Species


def test_render_gaussian_input_for_water(tmp_path):
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
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="single_point",
    )

    rendered = render_gaussian_input(
        species,
        spec,
        GaussianInputOptions(route="# wb97xd/6-31g", title="water single point"),
    )

    assert rendered == (
        "# wb97xd/6-31g\n"
        "\n"
        "water single point\n"
        "\n"
        "0 1\n"
        "O 0 0 0\n"
        "H 0 0.757 0.586\n"
        "H 0 -0.757 0.586\n"
        "\n"
    )


def test_render_gaussian_input_uses_spec_charge_and_multiplicity(tmp_path):
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
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="single_point",
        charge=-1,
        multiplicity=2,
    )

    rendered = render_gaussian_input(
        species,
        spec,
        GaussianInputOptions(route="wb97xd/6-31g", title="oxygen anion doublet"),
    )

    assert "\n-1 2\n" in rendered


def test_render_gaussian_input_link0_options(tmp_path):
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
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="single_point",
    )

    rendered = render_gaussian_input(
        species,
        spec,
        GaussianInputOptions(
            nprocshared=8,
            mem="8GB",
            checkpoint=Path("carbon_dioxide.chk"),
            route="wb97xd/6-31g",
            title="carbon dioxide single point",
        ),
    )

    assert rendered.startswith(
        "%nprocshared=8\n%mem=8GB\n%chk=carbon_dioxide.chk\n# wb97xd/6-31g\n"
    )


def test_render_gaussian_input_requires_route(tmp_path):
    xyz_path = tmp_path / "h.xyz"
    xyz_path.write_text(
        "1\nsynthetic fixture hydrogen atom geometry\nH 0 0 0\n",
        encoding="utf-8",
    )
    species = Species(
        name="hydrogen",
        formula="H",
        charge=0,
        multiplicity=2,
        geometry_path=xyz_path,
    )
    spec = CalculationSpec(
        backend="gaussian",
        method="hf",
        basis="sto-3g",
        task="single_point",
    )

    with pytest.raises(ValueError, match="route"):
        render_gaussian_input(species, spec, GaussianInputOptions())


@pytest.mark.parametrize(
    ("task", "expected_route"),
    [
        ("single_point", "# wb97xd/6-31+G(d,p)"),
        ("opt", "# wb97xd/6-31+G(d,p) opt"),
        ("freq", "# wb97xd/6-31+G(d,p) freq"),
        ("opt_freq", "# wb97xd/6-31+G(d,p) opt freq"),
    ],
)
def test_gaussian_route_task_presets(task, expected_route):
    spec = CalculationSpec(
        backend="gaussian",
        method="wb97xd",
        basis="6-31+G(d,p)",
        task=task,
    )

    assert gaussian_route_from_spec(spec) == expected_route


def test_gaussian_route_includes_solvent_when_supplied():
    spec = CalculationSpec(
        backend="gaussian",
        method="wb97xd",
        basis="6-31+G(d,p)",
        task="opt_freq",
        solvent="smd,solvent=water",
    )

    assert gaussian_route_from_spec(spec) == (
        "# wb97xd/6-31+G(d,p) opt freq scrf=(smd,solvent=water)"
    )


def test_gaussian_route_appends_additional_keywords():
    spec = CalculationSpec(
        backend="gaussian",
        method="wb97xd",
        basis="6-31+G(d,p)",
        task="single_point",
    )

    assert gaussian_route_from_spec(spec, additional_keywords=("scf=tight",)) == (
        "# wb97xd/6-31+G(d,p) scf=tight"
    )


def test_gaussian_route_rejects_unknown_task():
    spec = CalculationSpec(
        backend="gaussian",
        method="wb97xd",
        basis="6-31+G(d,p)",
        task="unknown",
    )

    with pytest.raises(ValueError, match="unsupported Gaussian task"):
        gaussian_route_from_spec(spec)
