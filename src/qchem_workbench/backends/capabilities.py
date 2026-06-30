"""Backend capability models for registry and plugin metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


BackendStability = Literal["stable", "experimental", "internal"]
_VALID_STABILITIES = {"stable", "experimental", "internal"}

__all__ = [
    "BackendCapabilities",
    "BackendCapability",
    "BackendMetadata",
    "BackendStability",
    "normalize_backend_id",
]


@dataclass(frozen=True)
class BackendCapability:
    """Machine-readable backend support metadata.

    Capability flags describe qchem-workbench integration support. They do not
    certify that a particular calculation output contains every property, and
    they do not imply that external engines are bundled or executed.
    """

    backend_id: str
    display_name: str
    description: str | None = None
    can_execute: bool = False
    can_render_input: bool = False
    can_parse_output: bool = False
    supports_molecular: bool = False
    supports_periodic: bool = False
    supports_geometry_optimisation: bool = False
    supports_frequency: bool = False
    supports_thermochemistry: bool = False
    supports_orbitals: bool = False
    supports_population_analysis: bool = False
    supports_excited_states: bool = False
    supports_forces: bool = False
    supports_stress: bool = False
    supports_microkinetics: bool = False
    requires_external_executable: bool = False
    required_optional_extra: str | None = None
    notes: tuple[str, ...] = ()
    stability: BackendStability = "stable"
    properties_supported: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "backend_id", normalize_backend_id(self.backend_id))
        if not self.display_name.strip():
            raise ValueError("backend display_name must be nonempty")
        if self.stability not in _VALID_STABILITIES:
            allowed = ", ".join(sorted(_VALID_STABILITIES))
            raise ValueError(f"backend stability must be one of: {allowed}")
        object.__setattr__(self, "notes", tuple(str(note) for note in self.notes))
        object.__setattr__(
            self,
            "properties_supported",
            tuple(str(prop) for prop in self.properties_supported),
        )

    @property
    def name(self) -> str:
        """Compatibility alias for older backend metadata callers."""

        return self.backend_id

    @property
    def capabilities(self) -> BackendCapabilities:
        """Compatibility view with the previous coarse capability model."""

        return BackendCapabilities.from_capability(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "name": self.backend_id,
            "display_name": self.display_name,
            "description": self.description,
            "can_execute": self.can_execute,
            "can_render_input": self.can_render_input,
            "can_parse_output": self.can_parse_output,
            "supports_molecular": self.supports_molecular,
            "supports_periodic": self.supports_periodic,
            "supports_geometry_optimisation": self.supports_geometry_optimisation,
            "supports_frequency": self.supports_frequency,
            "supports_thermochemistry": self.supports_thermochemistry,
            "supports_orbitals": self.supports_orbitals,
            "supports_population_analysis": self.supports_population_analysis,
            "supports_excited_states": self.supports_excited_states,
            "supports_forces": self.supports_forces,
            "supports_stress": self.supports_stress,
            "supports_microkinetics": self.supports_microkinetics,
            "requires_external_executable": self.requires_external_executable,
            "required_optional_extra": self.required_optional_extra,
            "notes": list(self.notes),
            "stability": self.stability,
            "properties_supported": list(self.properties_supported),
            "capabilities": self.capabilities.to_dict(),
        }


@dataclass(frozen=True)
class BackendCapabilities:
    """Previous coarse backend capability model kept for compatibility."""

    input_rendering: bool = False
    output_parsing: bool = False
    execution: bool = False
    molecular_support: bool = False
    periodic_support: bool = False
    properties_supported: tuple[str, ...] = ()

    @classmethod
    def from_capability(cls, capability: BackendCapability) -> BackendCapabilities:
        return cls(
            input_rendering=capability.can_render_input,
            output_parsing=capability.can_parse_output,
            execution=capability.can_execute,
            molecular_support=capability.supports_molecular,
            periodic_support=capability.supports_periodic,
            properties_supported=tuple(capability.properties_supported),
        )

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
    """Previous backend metadata model kept for compatibility."""

    name: str
    display_name: str
    capabilities: BackendCapabilities
    description: str | None = None

    @classmethod
    def from_capability(cls, capability: BackendCapability) -> BackendMetadata:
        return cls(
            name=capability.backend_id,
            display_name=capability.display_name,
            capabilities=capability.capabilities,
            description=capability.description,
        )

    def to_capability(self) -> BackendCapability:
        properties = set(self.capabilities.properties_supported)
        return BackendCapability(
            backend_id=self.name,
            display_name=self.display_name,
            description=self.description,
            can_execute=self.capabilities.execution,
            can_render_input=self.capabilities.input_rendering,
            can_parse_output=self.capabilities.output_parsing,
            supports_molecular=self.capabilities.molecular_support,
            supports_periodic=self.capabilities.periodic_support,
            supports_thermochemistry="thermochemistry" in properties,
            supports_orbitals="orbital_energies" in properties,
            supports_population_analysis="population_analysis" in properties,
            supports_excited_states="electronic_excitations" in properties,
            supports_forces="forces" in properties,
            supports_stress="stress" in properties,
            properties_supported=self.capabilities.properties_supported,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": normalize_backend_id(self.name),
            "display_name": self.display_name,
            "description": self.description,
            "capabilities": self.capabilities.to_dict(),
        }


def normalize_backend_id(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("backend ID must be nonempty")
    return normalized
