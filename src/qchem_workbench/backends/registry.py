"""Typed backend capability registry."""

from __future__ import annotations

from qchem_workbench.backends.capabilities import (
    BackendCapabilities,
    BackendCapability,
    BackendMetadata,
    BackendStability,
    normalize_backend_id,
)

__all__ = [
    "DEFAULT_BACKEND_REGISTRY",
    "BackendCapabilities",
    "BackendCapability",
    "BackendMetadata",
    "BackendRegistry",
    "BackendRegistryError",
    "BackendStability",
    "built_in_backend_registry",
    "get_backend",
    "list_backends",
    "register_backend",
]


class BackendRegistryError(KeyError):
    """Raised when backend registry lookup fails."""


class BackendRegistry:
    """Small typed registry for backend capability metadata."""

    def __init__(
        self,
        entries: tuple[BackendCapability | BackendMetadata, ...] = (),
    ) -> None:
        self._entries: dict[str, BackendCapability] = {}
        for entry in entries:
            self.register(entry)

    def register(
        self,
        metadata: BackendCapability | BackendMetadata,
        *,
        replace: bool = False,
    ) -> None:
        capability = _coerce_capability(metadata)
        key = normalize_backend_id(capability.backend_id)
        if key in self._entries and not replace:
            raise ValueError(f"backend {capability.backend_id!r} is already registered")
        self._entries[key] = capability

    def get(self, name: str) -> BackendCapability:
        key = normalize_backend_id(name)
        try:
            return self._entries[key]
        except KeyError as exc:
            available = ", ".join(sorted(self._entries)) or "none"
            raise BackendRegistryError(
                f"backend {name!r} is not registered; available backends: {available}"
            ) from exc

    def list(self) -> tuple[BackendCapability, ...]:
        return tuple(self._entries[name] for name in sorted(self._entries))

    def names(self) -> tuple[str, ...]:
        return tuple(entry.name for entry in self.list())

    def has(self, name: str) -> bool:
        return normalize_backend_id(name) in self._entries


def _coerce_capability(
    metadata: BackendCapability | BackendMetadata,
) -> BackendCapability:
    if isinstance(metadata, BackendCapability):
        return metadata
    if isinstance(metadata, BackendMetadata):
        return metadata.to_capability()
    raise TypeError(
        "backend registry entries must be BackendCapability or BackendMetadata"
    )


def built_in_backend_registry() -> BackendRegistry:
    """Return a registry populated with built-in backend adapters."""

    return BackendRegistry(
        (
            BackendCapability(
                backend_id="gaussian",
                display_name="Gaussian",
                can_render_input=True,
                can_parse_output=True,
                supports_molecular=True,
                supports_geometry_optimisation=True,
                supports_frequency=True,
                supports_thermochemistry=True,
                supports_orbitals=True,
                supports_population_analysis=True,
                supports_excited_states=True,
                requires_external_executable=True,
                properties_supported=(
                    "electronic_energy",
                    "thermochemistry",
                    "dipole_moment",
                    "population_analysis",
                    "vibrational_frequencies",
                    "orbital_energies",
                    "electronic_excitations",
                    "spin",
                ),
                description=(
                    "Gaussian input rendering and output parsing; execution is "
                    "external."
                ),
                notes=(
                    "qchem-workbench does not execute Gaussian or bundle Gaussian.",
                ),
            ),
            BackendCapability(
                backend_id="orca",
                display_name="ORCA",
                can_render_input=True,
                can_parse_output=True,
                supports_molecular=True,
                supports_geometry_optimisation=True,
                supports_frequency=True,
                supports_thermochemistry=True,
                supports_orbitals=True,
                supports_population_analysis=True,
                supports_excited_states=True,
                requires_external_executable=True,
                properties_supported=(
                    "electronic_energy",
                    "thermochemistry",
                    "dipole_moment",
                    "population_analysis",
                    "vibrational_frequencies",
                    "orbital_energies",
                    "electronic_excitations",
                    "spin",
                ),
                description=(
                    "ORCA input rendering and output parsing; execution is external."
                ),
                notes=("qchem-workbench does not execute ORCA or bundle ORCA.",),
            ),
            BackendCapability(
                backend_id="pyscf",
                display_name="PySCF",
                can_execute=True,
                supports_molecular=True,
                supports_orbitals=True,
                required_optional_extra="pyscf",
                properties_supported=("electronic_energy", "orbital_energies"),
                description="Optional PySCF single-point execution backend.",
                notes=("Molecular single-point execution only.",),
            ),
            BackendCapability(
                backend_id="qe",
                display_name="Quantum ESPRESSO pw.x",
                can_render_input=True,
                can_parse_output=True,
                supports_molecular=True,
                supports_periodic=True,
                supports_geometry_optimisation=True,
                supports_forces=True,
                supports_stress=True,
                requires_external_executable=True,
                properties_supported=(
                    "total_energy",
                    "scf_status",
                    "forces",
                    "stress",
                    "cell",
                ),
                description=(
                    "Quantum ESPRESSO pw.x input rendering and output parsing; "
                    "execution is external."
                ),
                notes=(
                    "Capability is limited to pw.x input/output support, not all "
                    "QE tools.",
                    "Pseudopotentials are user-provided.",
                ),
            ),
            BackendCapability(
                backend_id="ase",
                display_name="ASE helpers",
                supports_molecular=True,
                supports_periodic=True,
                required_optional_extra="ase",
                stability="experimental",
                description=(
                    "Optional ASE adapters and starting-structure helpers; no "
                    "calculator execution."
                ),
                notes=(
                    "Generated slabs and adsorbate placements are starting geometries "
                    "requiring human inspection.",
                ),
            ),
        )
    )


DEFAULT_BACKEND_REGISTRY = built_in_backend_registry()


def list_backends() -> tuple[BackendCapability, ...]:
    return DEFAULT_BACKEND_REGISTRY.list()


def get_backend(name: str) -> BackendCapability:
    return DEFAULT_BACKEND_REGISTRY.get(name)


def register_backend(
    metadata: BackendCapability | BackendMetadata,
    *,
    replace: bool = False,
) -> None:
    DEFAULT_BACKEND_REGISTRY.register(metadata, replace=replace)
