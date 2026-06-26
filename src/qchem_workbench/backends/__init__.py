"""Backend interfaces and implementations."""

from qchem_workbench.backends.ase_adapter import (
    ASEUnavailableError,
    from_ase_atoms,
    to_ase_atoms,
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
    validate_pseudopotentials_for_elements,
)

__all__ = [
    "ASEUnavailableError",
    "Backend",
    "GAUSSIAN_TASK_PRESETS",
    "GaussianInputOptions",
    "MissingOptionalDependencyError",
    "ORCAInputOptions",
    "ORCA_TASK_PRESETS",
    "PySCFBackend",
    "QEInputSpec",
    "QEKPoints",
    "SCHEDULER_NAMES",
    "STARTING_STRUCTURE_WARNING",
    "SUPPORTED_FCC_FACETS",
    "add_vacuum",
    "build_fcc_surface",
    "gaussian_route_from_spec",
    "from_ase_atoms",
    "orca_route_from_spec",
    "parse_gaussian_output",
    "parse_orca_output",
    "render_gaussian_input",
    "render_gaussian_scheduler_script",
    "render_orca_input",
    "repeat_slab_from_bulk",
    "to_ase_atoms",
    "validate_pseudopotentials_for_elements",
    "write_structure",
]
