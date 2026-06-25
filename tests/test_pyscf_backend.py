from __future__ import annotations

import importlib
import re

import pytest

from qchem_workbench.backends.pyscf_backend import (
    MissingOptionalDependencyError,
    PYSCF_INSTALL_HINT,
    PySCFBackend,
)


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

    with pytest.raises(MissingOptionalDependencyError, match=re.escape(PYSCF_INSTALL_HINT)):
        backend._load_pyscf_modules()


def test_optional_pyscf_modules_load_when_installed():
    pytest.importorskip("pyscf")

    modules = PySCFBackend()._load_pyscf_modules()

    assert {"dft", "gto"} <= set(modules)
