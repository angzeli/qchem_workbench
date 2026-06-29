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
from qchem_workbench.active_learning.scoring import (
    ScoredDataset,
    score_dataset_rows,
    write_scored_dataset_csv,
)
from qchem_workbench.active_learning.bo_forge import (
    BO_FORGE_INTERCHANGE_SCHEMA_VERSION,
    BOForgeExportSummary,
    export_bo_forge_interchange,
)
from qchem_workbench.active_learning.bo_forge_adapter import (
    BOForgeUnavailableError,
    from_bo_forge_proposals,
    to_bo_forge_dataset,
)
from qchem_workbench.active_learning.proposals import (
    ProposalImportSummary,
    ProposedCandidate,
    import_proposed_candidates_csv,
    proposal_todo_manifest,
    write_proposal_todo_manifest,
)
from qchem_workbench.active_learning.report import (
    generate_active_learning_report,
    write_active_learning_report,
)
from qchem_workbench.active_learning.state import (
    ACTIVE_LEARNING_STATE_SCHEMA_VERSION,
    CampaignState,
    CandidateStateEntry,
    StateAuditEntry,
    load_campaign_state,
    mark_candidate_state,
    save_campaign_state,
    state_summary,
)
from qchem_workbench.active_learning.datasets import (
    ACTIVE_LEARNING_DATASET_SCHEMA_VERSION,
    DESCRIPTOR_SOURCE_TYPES,
    ActiveLearningCampaign,
    DescriptorDataset,
    DescriptorSource,
    build_active_learning_dataset,
    load_active_learning_campaign,
    write_descriptor_dataset_csv,
)

__all__ = [
    "ACTIVE_LEARNING_CANDIDATE_SCHEMA_VERSION",
    "ACTIVE_LEARNING_DATASET_SCHEMA_VERSION",
    "ACTIVE_LEARNING_OBJECTIVE_SCHEMA_VERSION",
    "ACTIVE_LEARNING_STATE_SCHEMA_VERSION",
    "BO_FORGE_INTERCHANGE_SCHEMA_VERSION",
    "DESCRIPTOR_SOURCE_TYPES",
    "SUPPORTED_CONSTRAINT_OPERATORS",
    "SUPPORTED_CANDIDATE_TYPES",
    "SUPPORTED_OBJECTIVE_DIRECTIONS",
    "ActiveLearningCandidate",
    "ActiveLearningCampaign",
    "CandidateRegistry",
    "CandidateStateEntry",
    "CampaignState",
    "DescriptorDataset",
    "DescriptorSource",
    "ObjectiveConstraint",
    "ObjectiveDefinition",
    "ObjectiveSpec",
    "ScoredDataset",
    "BOForgeExportSummary",
    "BOForgeUnavailableError",
    "ProposalImportSummary",
    "ProposedCandidate",
    "load_candidate_registry",
    "load_active_learning_campaign",
    "load_campaign_state",
    "load_objective_spec",
    "build_active_learning_dataset",
    "score_dataset_rows",
    "export_bo_forge_interchange",
    "from_bo_forge_proposals",
    "generate_active_learning_report",
    "import_proposed_candidates_csv",
    "mark_candidate_state",
    "proposal_todo_manifest",
    "save_campaign_state",
    "state_summary",
    "StateAuditEntry",
    "to_bo_forge_dataset",
    "validate_objective_columns",
    "write_descriptor_dataset_csv",
    "write_active_learning_report",
    "write_proposal_todo_manifest",
    "write_scored_dataset_csv",
]
