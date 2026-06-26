"""Optional geometry setup helpers."""

from qchem_workbench.geometry.rdkit_tools import (
    RDKitUnavailableError,
    generate_conformer_xyz_files,
)

__all__ = [
    "RDKitUnavailableError",
    "generate_conformer_xyz_files",
]
