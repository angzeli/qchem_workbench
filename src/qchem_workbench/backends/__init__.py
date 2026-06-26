"""Backend interfaces and implementations."""

from qchem_workbench.backends.ase_adapter import (
    ASEUnavailableError,
    from_ase_atoms,
    to_ase_atoms,
)
from qchem_workbench.backends.ase_adsorption import (
    STARTING_ADSORBATE_PLACEMENT_WARNING,
    AdsorbatePlacementConfig,
    load_adsorbate_placement_config,
    place_adsorbate,
    place_adsorbate_from_yaml,
)
from qchem_workbench.backends.ase_surface import (
    STARTING_STRUCTURE_WARNING,
    SUPPORTED_FCC_FACETS,
    add_vacuum,
    build_fcc_surface,
    repeat_slab_from_bulk,
    write_structure,
)
from qchem_workbench.backends.base import Backend
from qchem_workbench.backends.gaussian_input import (
    GAUSSIAN_TASK_PRESETS,
    GaussianInputOptions,
    gaussian_route_from_spec,
    render_gaussian_input,
)
from qchem_workbench.backends.gaussian_parser import parse_gaussian_output
from qchem_workbench.backends.gaussian_scheduler import (
    SCHEDULER_NAMES,
    render_gaussian_scheduler_script,
)
from qchem_workbench.backends.orca_input import (
    ORCA_TASK_PRESETS,
    ORCAInputOptions,
    orca_route_from_spec,
    render_orca_input,
)
from qchem_workbench.backends.orca_parser import parse_orca_output
from qchem_workbench.backends.pyscf_backend import (
    MissingOptionalDependencyError,
    PySCFBackend,
)
from qchem_workbench.backends.qe_input import (
    QEKPoints,
    QEInputSpec,
    render_qe_pw_input,
    validate_pseudopotentials_for_elements,
)
from qchem_workbench.backends.qe_parser import parse_qe_output
from qchem_workbench.backends.registry import (
    DEFAULT_BACKEND_REGISTRY,
    BackendCapabilities,
    BackendMetadata,
    BackendRegistry,
    BackendRegistryError,
    built_in_backend_registry,
    get_backend,
    list_backends,
    register_backend,
)

__all__ = [
    "ASEUnavailableError",
    "AdsorbatePlacementConfig",
    "Backend",
    "BackendCapabilities",
    "BackendMetadata",
    "BackendRegistry",
    "BackendRegistryError",
    "DEFAULT_BACKEND_REGISTRY",
    "GAUSSIAN_TASK_PRESETS",
    "GaussianInputOptions",
    "MissingOptionalDependencyError",
    "ORCAInputOptions",
    "ORCA_TASK_PRESETS",
    "PySCFBackend",
    "QEInputSpec",
    "QEKPoints",
    "SCHEDULER_NAMES",
    "STARTING_ADSORBATE_PLACEMENT_WARNING",
    "STARTING_STRUCTURE_WARNING",
    "SUPPORTED_FCC_FACETS",
    "add_vacuum",
    "build_fcc_surface",
    "built_in_backend_registry",
    "gaussian_route_from_spec",
    "get_backend",
    "from_ase_atoms",
    "list_backends",
    "load_adsorbate_placement_config",
    "orca_route_from_spec",
    "parse_gaussian_output",
    "parse_orca_output",
    "parse_qe_output",
    "place_adsorbate",
    "place_adsorbate_from_yaml",
    "render_gaussian_input",
    "render_gaussian_scheduler_script",
    "render_orca_input",
    "render_qe_pw_input",
    "repeat_slab_from_bulk",
    "register_backend",
    "to_ase_atoms",
    "validate_pseudopotentials_for_elements",
    "write_structure",
]
