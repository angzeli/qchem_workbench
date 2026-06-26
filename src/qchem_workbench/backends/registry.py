"""Typed backend capability registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackendCapabilities:
    """Backend workflow capabilities advertised to qchem-workbench."""

    input_rendering: bool = False
    output_parsing: bool = False
    execution: bool = False
    molecular_support: bool = False
    periodic_support: bool = False
    properties_supported: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "input_rendering": self.input_rendering,
            "output_parsing": self.output_parsing,
            "execution": self.execution,
            "molecular_support": self.molecular_support,
            "periodic_support": self.periodic_support,
            "properties_supported": list(self.properties_supported),
        }


@dataclass(frozen=True)
class BackendMetadata:
    """Discoverable metadata for a backend adapter."""

    name: str
    display_name: str
    capabilities: BackendCapabilities
    description: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "capabilities": self.capabilities.to_dict(),
        }


class BackendRegistryError(KeyError):
    """Raised when backend registry lookup fails."""


class BackendRegistry:
    """Small typed registry for backend capability metadata."""

    def __init__(self, entries: tuple[BackendMetadata, ...] = ()) -> None:
        self._entries: dict[str, BackendMetadata] = {}
        for entry in entries:
            self.register(entry)

    def register(self, metadata: BackendMetadata, *, replace: bool = False) -> None:
        key = _normalize_backend_name(metadata.name)
        if key in self._entries and not replace:
            raise ValueError(f"backend {metadata.name!r} is already registered")
        self._entries[key] = BackendMetadata(
            name=key,
            display_name=metadata.display_name,
            capabilities=metadata.capabilities,
            description=metadata.description,
        )

    def get(self, name: str) -> BackendMetadata:
        key = _normalize_backend_name(name)
        try:
            return self._entries[key]
        except KeyError as exc:
            available = ", ".join(sorted(self._entries)) or "none"
            raise BackendRegistryError(
                f"backend {name!r} is not registered; available backends: {available}"
            ) from exc

    def list(self) -> tuple[BackendMetadata, ...]:
        return tuple(self._entries[name] for name in sorted(self._entries))

    def names(self) -> tuple[str, ...]:
        return tuple(entry.name for entry in self.list())

    def has(self, name: str) -> bool:
        return _normalize_backend_name(name) in self._entries


def _normalize_backend_name(name: str) -> str:
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("backend name must be nonempty")
    return normalized


def built_in_backend_registry() -> BackendRegistry:
    """Return a registry populated with built-in backend adapters."""

    return BackendRegistry(
        (
            BackendMetadata(
                name="gaussian",
                display_name="Gaussian",
                capabilities=BackendCapabilities(
                    input_rendering=True,
                    output_parsing=True,
                    execution=False,
                    molecular_support=True,
                    periodic_support=False,
                    properties_supported=(
                        "electronic_energy",
                        "thermochemistry",
                        "vibrational_frequencies",
                        "orbital_energies",
                        "electronic_excitations",
                        "spin",
                    ),
                ),
                description=(
                    "Gaussian input rendering and output parsing; execution is external."
                ),
            ),
            BackendMetadata(
                name="orca",
                display_name="ORCA",
                capabilities=BackendCapabilities(
                    input_rendering=True,
                    output_parsing=True,
                    execution=False,
                    molecular_support=True,
                    periodic_support=False,
                    properties_supported=(
                        "electronic_energy",
                        "thermochemistry",
                        "vibrational_frequencies",
                        "orbital_energies",
                        "electronic_excitations",
                        "spin",
                    ),
                ),
                description="ORCA input rendering and output parsing; execution is external.",
            ),
            BackendMetadata(
                name="pyscf",
                display_name="PySCF",
                capabilities=BackendCapabilities(
                    input_rendering=False,
                    output_parsing=False,
                    execution=True,
                    molecular_support=True,
                    periodic_support=False,
                    properties_supported=("electronic_energy", "orbital_energies"),
                ),
                description="Optional PySCF single-point execution backend.",
            ),
            BackendMetadata(
                name="qe",
                display_name="Quantum ESPRESSO pw.x",
                capabilities=BackendCapabilities(
                    input_rendering=True,
                    output_parsing=True,
                    execution=False,
                    molecular_support=True,
                    periodic_support=True,
                    properties_supported=(
                        "total_energy",
                        "scf_status",
                        "forces",
                        "cell",
                    ),
                ),
                description=(
                    "Quantum ESPRESSO pw.x input rendering and output parsing; "
                    "execution is external."
                ),
            ),
        )
    )


DEFAULT_BACKEND_REGISTRY = built_in_backend_registry()


def list_backends() -> tuple[BackendMetadata, ...]:
    return DEFAULT_BACKEND_REGISTRY.list()


def get_backend(name: str) -> BackendMetadata:
    return DEFAULT_BACKEND_REGISTRY.get(name)


def register_backend(metadata: BackendMetadata, *, replace: bool = False) -> None:
    DEFAULT_BACKEND_REGISTRY.register(metadata, replace=replace)
