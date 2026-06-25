"""Optional PySCF backend."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from types import ModuleType
from typing import Any

from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.geometry import MoleculeGeometry, read_xyz
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species
from qchem_workbench.core.units import hartree_to_ev


PYSCF_INSTALL_HINT = "Install PySCF support with `pip install 'qchem-workbench[pyscf]'`."


class MissingOptionalDependencyError(ImportError):
    """Raised when an optional backend dependency is unavailable."""


class PySCFBackend:
    """Backend for PySCF single-point calculations."""

    name = "pyscf"

    def run(self, species: Species, spec: CalculationSpec) -> CalculationResult:
        if spec.task != "single_point":
            return _failure_result(
                species,
                spec,
                f"PySCF backend only supports single_point tasks, got {spec.task!r}.",
            )
        if spec.basis is None:
            return _failure_result(
                species,
                spec,
                "PySCF basis is required; no production default is assumed.",
            )

        modules = self._load_pyscf_modules()
        warnings: list[str] = []
        charge, multiplicity = _resolve_charge_multiplicity(species, spec)
        spin = multiplicity - 1

        try:
            geometry = read_xyz(species.geometry_path)
            mol = modules["gto"].M(
                atom=_geometry_to_pyscf_atom(geometry),
                basis=spec.basis,
                charge=charge,
                spin=spin,
            )
            mean_field = _build_mean_field(
                modules["dft"],
                mol,
                spec.method,
                spin,
                spec.keywords,
                warnings,
            )
            electronic_energy = float(mean_field.kernel())
        except Exception as exc:
            return _failure_result(
                species,
                spec,
                f"PySCF calculation failed: {exc}",
                metadata={"exception_type": type(exc).__name__},
            )

        return _result_from_mean_field(
            species=species,
            spec=spec,
            electronic_energy=electronic_energy,
            converged=bool(getattr(mean_field, "converged", False)),
            n_atoms=len(geometry.atoms),
            spin=spin,
            scf_class=type(mean_field).__name__,
            warnings=warnings,
            mean_field=mean_field,
        )

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


def _resolve_charge_multiplicity(
    species: Species, spec: CalculationSpec
) -> tuple[int, int]:
    charge = species.charge if spec.charge is None else spec.charge
    multiplicity = (
        species.multiplicity if spec.multiplicity is None else spec.multiplicity
    )
    if multiplicity <= 0:
        raise ValueError("multiplicity must be positive")
    return charge, multiplicity


def _geometry_to_pyscf_atom(
    geometry: MoleculeGeometry,
) -> list[tuple[str, tuple[float, float, float]]]:
    return [(atom.symbol, (atom.x, atom.y, atom.z)) for atom in geometry.atoms]


def _build_mean_field(
    dft_module: ModuleType,
    mol: Any,
    method: str,
    spin: int,
    keywords: dict[str, Any],
    warnings: list[str],
) -> Any:
    mean_field = dft_module.RKS(mol) if spin == 0 else dft_module.UKS(mol)
    mean_field.xc = method

    for key, value in keywords.items():
        if hasattr(mean_field, key):
            setattr(mean_field, key, value)
        else:
            warnings.append(
                f"PySCF keyword {key!r} was not applied; no matching SCF attribute."
            )

    return mean_field


def _result_from_mean_field(
    species: Species,
    spec: CalculationSpec,
    electronic_energy: float,
    converged: bool,
    n_atoms: int,
    spin: int,
    scf_class: str,
    warnings: list[str] | None = None,
    mean_field: Any | None = None,
) -> CalculationResult:
    result_warnings = list(warnings or [])
    if not converged:
        result_warnings.append("PySCF SCF calculation did not converge.")

    orbital_summary, orbital_metadata = _extract_orbital_summary(mean_field)
    metadata = {
        "converged": converged,
        "n_atoms": n_atoms,
        "pyscf_spin": spin,
        "scf_class": scf_class,
    }
    if orbital_metadata:
        metadata["orbital_energies_ev"] = orbital_metadata

    return CalculationResult(
        species_name=species.name,
        backend="pyscf",
        method=spec.method,
        basis=spec.basis,
        task=spec.task,
        success=converged,
        electronic_energy_hartree=electronic_energy,
        homo_ev=orbital_summary["homo_ev"],
        lumo_ev=orbital_summary["lumo_ev"],
        gap_ev=orbital_summary["gap_ev"],
        warnings=result_warnings,
        metadata=metadata,
        source_path=species.geometry_path,
    )


def _failure_result(
    species: Species,
    spec: CalculationSpec,
    warning: str,
    metadata: dict[str, Any] | None = None,
) -> CalculationResult:
    return CalculationResult(
        species_name=species.name,
        backend="pyscf",
        method=spec.method,
        basis=spec.basis,
        task=spec.task,
        success=False,
        warnings=[warning],
        metadata=dict(metadata or {}),
        source_path=species.geometry_path,
    )


def _extract_orbital_summary(
    mean_field: Any | None,
) -> tuple[dict[str, float | None], dict[str, dict[str, float | None]]]:
    empty = {"homo_ev": None, "lumo_ev": None, "gap_ev": None}
    if mean_field is None:
        return empty, {}

    mo_energy = getattr(mean_field, "mo_energy", None)
    mo_occ = getattr(mean_field, "mo_occ", None)
    if mo_energy is None or mo_occ is None:
        return empty, {}

    if _is_spin_resolved(mo_energy) and _is_spin_resolved(mo_occ):
        alpha = _orbital_summary_from_arrays(mo_energy[0], mo_occ[0])
        beta = _orbital_summary_from_arrays(mo_energy[1], mo_occ[1])
        return _combined_unrestricted_summary(alpha, beta), {
            "alpha": alpha,
            "beta": beta,
        }

    return _orbital_summary_from_arrays(mo_energy, mo_occ), {}


def _orbital_summary_from_arrays(
    energies_hartree: Iterable[Any], occupations: Iterable[Any]
) -> dict[str, float | None]:
    occupied: list[float] = []
    unoccupied: list[float] = []
    for energy, occupation in zip(energies_hartree, occupations):
        if float(occupation) > 0.0:
            occupied.append(float(energy))
        else:
            unoccupied.append(float(energy))

    homo_hartree = max(occupied) if occupied else None
    lumo_hartree = min(unoccupied) if unoccupied else None
    homo_ev = hartree_to_ev(homo_hartree)
    lumo_ev = hartree_to_ev(lumo_hartree)
    gap_ev = None if homo_ev is None or lumo_ev is None else lumo_ev - homo_ev
    return {"homo_ev": homo_ev, "lumo_ev": lumo_ev, "gap_ev": gap_ev}


def _combined_unrestricted_summary(
    alpha: dict[str, float | None], beta: dict[str, float | None]
) -> dict[str, float | None]:
    homo_values = [
        value for value in (alpha["homo_ev"], beta["homo_ev"]) if value is not None
    ]
    lumo_values = [
        value for value in (alpha["lumo_ev"], beta["lumo_ev"]) if value is not None
    ]
    homo_ev = max(homo_values) if homo_values else None
    lumo_ev = min(lumo_values) if lumo_values else None
    gap_ev = None if homo_ev is None or lumo_ev is None else lumo_ev - homo_ev
    return {"homo_ev": homo_ev, "lumo_ev": lumo_ev, "gap_ev": gap_ev}


def _is_spin_resolved(values: Any) -> bool:
    try:
        return (
            len(values) == 2
            and _is_iterable(values[0])
            and _is_iterable(values[1])
        )
    except TypeError:
        return False


def _is_iterable(value: Any) -> bool:
    return isinstance(value, Iterable) and not isinstance(value, (str, bytes))
