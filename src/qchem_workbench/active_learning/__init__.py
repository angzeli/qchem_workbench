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
from qchem_workbench.active_learning.objectives import (
    ACTIVE_LEARNING_OBJECTIVE_SCHEMA_VERSION,
    SUPPORTED_CONSTRAINT_OPERATORS,
    SUPPORTED_OBJECTIVE_DIRECTIONS,
    ObjectiveConstraint,
    ObjectiveDefinition,
    ObjectiveSpec,
    load_objective_spec,
    validate_objective_columns,
)

__all__ = [
    "ACTIVE_LEARNING_CANDIDATE_SCHEMA_VERSION",
    "ACTIVE_LEARNING_OBJECTIVE_SCHEMA_VERSION",
    "SUPPORTED_CONSTRAINT_OPERATORS",
    "SUPPORTED_CANDIDATE_TYPES",
    "SUPPORTED_OBJECTIVE_DIRECTIONS",
    "ActiveLearningCandidate",
    "CandidateRegistry",
    "ObjectiveConstraint",
    "ObjectiveDefinition",
    "ObjectiveSpec",
    "load_candidate_registry",
    "load_objective_spec",
    "validate_objective_columns",
]
