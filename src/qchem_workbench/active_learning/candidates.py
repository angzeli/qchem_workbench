"""Generic active-learning candidate registry schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


ACTIVE_LEARNING_CANDIDATE_SCHEMA_VERSION = 1
SUPPORTED_CANDIDATE_TYPES = {
    "molecule",
    "conformer",
    "surface",
    "adsorbate_system",
    "reaction_pathway",
    "custom",
}


@dataclass(frozen=True)
class ActiveLearningCandidate:
    id: str
    type: str
    species: str | None = None
    structure: str | None = None
    system: str | None = None
    pathway: str | None = None
    features: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateRegistry:
    candidates: tuple[ActiveLearningCandidate, ...]
    source_path: Path | None = None

    def by_id(self) -> dict[str, ActiveLearningCandidate]:
        return {candidate.id: candidate for candidate in self.candidates}


def load_candidate_registry(path: Path) -> CandidateRegistry:
    registry_path = Path(path)
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{registry_path}: candidate registry must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != ACTIVE_LEARNING_CANDIDATE_SCHEMA_VERSION:
        raise ValueError(
            f"{registry_path}: unsupported schema_version {schema_version!r}; "
            f"expected {ACTIVE_LEARNING_CANDIDATE_SCHEMA_VERSION}"
        )
    raw_candidates = data.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError(f"{registry_path}: candidates must be a list")
    candidates = _candidates(registry_path, raw_candidates)
    return CandidateRegistry(candidates=tuple(candidates), source_path=registry_path)


def _candidates(path: Path, raw_candidates: list[Any]) -> list[ActiveLearningCandidate]:
    seen: set[str] = set()
    parsed = []
    for index, raw in enumerate(raw_candidates):
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: candidates[{index}] must be a mapping")
        candidate_id = _required_string(path, raw, "id", f"candidates[{index}]")
        if candidate_id in seen:
            raise ValueError(f"{path}: duplicate candidate ID {candidate_id!r}")
        seen.add(candidate_id)
        candidate_type = _required_string(path, raw, "type", f"candidates[{index}]")
        if candidate_type not in SUPPORTED_CANDIDATE_TYPES:
            allowed = ", ".join(sorted(SUPPORTED_CANDIDATE_TYPES))
            raise ValueError(
                f"{path}: unsupported candidate type {candidate_type!r}; "
                f"expected one of {allowed}"
            )
        features = raw.get("features", {})
        metadata = raw.get("metadata", {})
        if not isinstance(features, dict):
            raise ValueError(f"{path}: candidates[{index}].features must be a mapping")
        if not isinstance(metadata, dict):
            raise ValueError(f"{path}: candidates[{index}].metadata must be a mapping")
        parsed.append(
            ActiveLearningCandidate(
                id=candidate_id,
                type=candidate_type,
                species=_optional_string(raw, "species"),
                structure=_optional_string(raw, "structure"),
                system=_optional_string(raw, "system"),
                pathway=_optional_string(raw, "pathway"),
                features=dict(features),
                metadata=dict(metadata),
            )
        )
    return parsed


def _required_string(path: Path, data: dict[str, Any], key: str, label: str) -> str:
    value = _optional_string(data, key)
    if value is None:
        raise ValueError(f"{path}: {label}.{key} must be a non-empty string")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string when provided")
    return value.strip()
