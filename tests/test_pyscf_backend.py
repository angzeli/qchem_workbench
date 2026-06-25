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
    _extract_orbital_summary,
    _result_from_mean_field,
)
from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.geometry import Atom, MoleculeGeometry
from qchem_workbench.core.species import Species
from qchem_workbench.core.units import HARTREE_TO_EV


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


def test_restricted_orbital_summary():
    class MeanField:
        mo_energy = [-0.5, 0.1]
        mo_occ = [2.0, 0.0]

    summary, metadata = _extract_orbital_summary(MeanField())

    assert summary["homo_ev"] == pytest.approx(-0.5 * HARTREE_TO_EV)
    assert summary["lumo_ev"] == pytest.approx(0.1 * HARTREE_TO_EV)
    assert summary["gap_ev"] == pytest.approx(0.6 * HARTREE_TO_EV)
    assert metadata == {}


def test_unrestricted_orbital_summary_metadata_is_explicit():
    class MeanField:
        mo_energy = ([-0.4, 0.2], [-0.3, 0.25])
        mo_occ = ([1.0, 0.0], [1.0, 0.0])

    summary, metadata = _extract_orbital_summary(MeanField())

    assert summary["homo_ev"] == pytest.approx(-0.3 * HARTREE_TO_EV)
    assert summary["lumo_ev"] == pytest.approx(0.2 * HARTREE_TO_EV)
    assert summary["gap_ev"] == pytest.approx(0.5 * HARTREE_TO_EV)
    assert metadata["alpha"]["homo_ev"] == pytest.approx(-0.4 * HARTREE_TO_EV)
    assert metadata["beta"]["lumo_ev"] == pytest.approx(0.25 * HARTREE_TO_EV)


def test_missing_orbitals_remain_missing():
    summary, metadata = _extract_orbital_summary(object())

    assert summary == {"homo_ev": None, "lumo_ev": None, "gap_ev": None}
    assert metadata == {}


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
    assert result.gap_ev is None or result.gap_ev >= 0.0
