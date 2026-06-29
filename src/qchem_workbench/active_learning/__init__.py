"""Active-learning campaign bookkeeping utilities.

This package provides file-based schemas and handoff helpers. It does not
implement a Bayesian optimiser or require BO Forge.
"""

from qchem_workbench.active_learning.candidates import (
    ACTIVE_LEARNING_CANDIDATE_SCHEMA_VERSION,
    SUPPORTED_CANDIDATE_TYPES,
    ActiveLearningCandidate,
    CandidateRegistry,
    load_candidate_registry,
)

__all__ = [
    "ACTIVE_LEARNING_CANDIDATE_SCHEMA_VERSION",
    "SUPPORTED_CANDIDATE_TYPES",
    "ActiveLearningCandidate",
    "CandidateRegistry",
    "load_candidate_registry",
]
