"""Optional PySCF backend."""

from __future__ import annotations

import importlib
from types import ModuleType

from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species


PYSCF_INSTALL_HINT = "Install PySCF support with `pip install 'qchem-workbench[pyscf]'`."


class MissingOptionalDependencyError(ImportError):
    """Raised when an optional backend dependency is unavailable."""


class PySCFBackend:
    """Backend skeleton for PySCF calculations."""

    name = "pyscf"

    def run(self, species: Species, spec: CalculationSpec) -> CalculationResult:
        self._load_pyscf_modules()
        raise NotImplementedError("PySCF calculations are not implemented yet.")

    def _load_pyscf_modules(self) -> dict[str, ModuleType]:
        try:
            return {
                "dft": importlib.import_module("pyscf.dft"),
                "gto": importlib.import_module("pyscf.gto"),
            }
        except ImportError as exc:
            raise MissingOptionalDependencyError(
                f"PySCF is required for the PySCF backend. {PYSCF_INSTALL_HINT}"
            ) from exc
