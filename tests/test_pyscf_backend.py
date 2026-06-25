from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

from qchem_workbench.backends.pyscf_backend import (
    MissingOptionalDependencyError,
    PYSCF_INSTALL_HINT,
    PySCFBackend,
    _geometry_to_pyscf_atom,
    _result_from_mean_field,
)
from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.geometry import Atom, MoleculeGeometry
from qchem_workbench.core.species import Species


def test_pyscf_backend_import_is_lazy():
    backend = PySCFBackend()

    assert backend.name == "pyscf"


def test_missing_pyscf_error_message(monkeypatch):
    def missing_import(name: str):
        if name.startswith("pyscf"):
            raise ImportError(name)
        return importlib.import_module(name)

    backend = PySCFBackend()
    monkeypatch.setattr(
        "qchem_workbench.backends.pyscf_backend.importlib.import_module",
        missing_import,
    )

    with pytest.raises(
        MissingOptionalDependencyError, match=re.escape(PYSCF_INSTALL_HINT)
    ):
        backend._load_pyscf_modules()


def test_optional_pyscf_modules_load_when_installed():
    pytest.importorskip("pyscf")

    modules = PySCFBackend()._load_pyscf_modules()

    assert {"dft", "gto"} <= set(modules)


def test_geometry_to_pyscf_atom_format():
    geometry = MoleculeGeometry(
        atoms=(Atom("H", 0.0, 0.0, 0.0), Atom("H", 0.0, 0.0, 0.74)),
        comment="synthetic fixture h2 geometry",
    )

    assert _geometry_to_pyscf_atom(geometry) == [
        ("H", (0.0, 0.0, 0.0)),
        ("H", (0.0, 0.0, 0.74)),
    ]


def test_result_from_mean_field_marks_nonconvergence():
    species = Species(
        name="h2",
        formula="H2",
        charge=0,
        multiplicity=1,
        geometry_path=Path("xyz/h2.xyz"),
    )
    spec = CalculationSpec(
        backend="pyscf",
        method="b3lyp",
        basis="sto-3g",
        task="single_point",
    )

    result = _result_from_mean_field(
        species=species,
        spec=spec,
        electronic_energy=-1.0,
        converged=False,
        n_atoms=2,
        spin=0,
        scf_class="RKS",
    )

    assert result.success is False
    assert result.electronic_energy_hartree == -1.0
    assert result.metadata["n_atoms"] == 2
    assert result.metadata["pyscf_spin"] == 0
    assert "did not converge" in result.warnings[0]


def test_pyscf_single_point_runs_when_installed(tmp_path):
    pytest.importorskip("pyscf")

    xyz_path = tmp_path / "h2.xyz"
    xyz_path.write_text(
        "2\n"
        "synthetic fixture h2 geometry\n"
        "H 0 0 0\n"
        "H 0 0 0.74\n",
        encoding="utf-8",
    )
    species = Species(
        name="h2",
        formula="H2",
        charge=0,
        multiplicity=1,
        geometry_path=xyz_path,
    )
    spec = CalculationSpec(
        backend="pyscf",
        method="b3lyp",
        basis="sto-3g",
        task="single_point",
        keywords={"max_cycle": 20},
    )

    result = PySCFBackend().run(species, spec)

    assert result.backend == "pyscf"
    assert result.metadata["n_atoms"] == 2
    assert result.metadata["pyscf_spin"] == 0
    assert result.electronic_energy_hartree is not None
