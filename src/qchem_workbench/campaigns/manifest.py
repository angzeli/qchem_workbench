"""Campaign manifest loading for screening workflows."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from typing import Any

import yaml

from qchem_workbench.core.calculation import CalculationSpec


CAMPAIGN_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CampaignCandidate:
    """Candidate species or structure tracked in a screening campaign."""

    id: str
    species_name: str | None = None
    structure_path: Path | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass(frozen=True)
class CalculationTemplate:
    """Reusable calculation settings for campaign candidates."""

    id: str
    backend: str | None = None
    method: str | None = None
    basis: str | None = None
    task: str | None = None
    solvent: str | None = None
    keywords: dict[str, Any] = dataclass_field(default_factory=dict)

    def to_spec(self, default_backend: str | None = None) -> CalculationSpec:
        backend = self.backend or default_backend
        missing = [
            name
            for name, value in (
                ("backend", backend),
                ("method", self.method),
                ("task", self.task),
            )
            if value is None or value == ""
        ]
        if missing:
            raise ValueError(
                f"calculation template {self.id!r} missing required field(s): "
                + ", ".join(missing)
            )
        return CalculationSpec(
            backend=str(backend),
            method=str(self.method),
            basis=self.basis,
            task=str(self.task),
            solvent=self.solvent,
            keywords=dict(self.keywords),
        )


@dataclass(frozen=True)
class DescriptorDefinition:
    """Named descriptor requested by a campaign."""

    name: str
    source: str
    field: str | None = None
    quantity: str | None = None
    reference: str | None = None
    metadata: dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass(frozen=True)
class RankingRule:
    """Transparent rule used later to rank descriptor rows."""

    descriptor: str
    direction: str | None = None
    weight: float | None = None
    filter: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    allow_missing: bool = False


@dataclass(frozen=True)
class CampaignManifest:
    """Resolved campaign manifest paths and screening settings."""

    path: Path
    name: str
    candidates: tuple[CampaignCandidate, ...]
    calculation_templates: tuple[CalculationTemplate, ...]
    backend_mode: str | None
    result_paths: tuple[Path, ...]
    descriptors: tuple[DescriptorDefinition, ...]
    ranking_rules: tuple[RankingRule, ...] = ()

    @property
    def root(self) -> Path:
        return self.path.parent


def load_campaign_manifest(path: Path) -> CampaignManifest:
    """Load and validate a qchem-workbench screening campaign manifest."""

    manifest_path = Path(path)
    data = _load_yaml_mapping(manifest_path)
    if "schema_version" not in data:
        raise ValueError(f"{manifest_path}: missing schema_version")
    schema_version = data["schema_version"]
    if schema_version != CAMPAIGN_SCHEMA_VERSION:
        raise ValueError(
            f"{manifest_path}: unsupported schema_version {schema_version!r}; "
            f"expected {CAMPAIGN_SCHEMA_VERSION}"
        )

    campaign = data.get("campaign")
    if not isinstance(campaign, dict):
        raise ValueError(f"{manifest_path}: campaign must be a mapping")

    result_paths = _path_list(manifest_path, campaign.get("results"), "campaign.results")
    if not result_paths:
        raise ValueError(f"{manifest_path}: campaign.results must list at least one path")

    name = _optional_string(campaign, "name") or manifest_path.stem
    candidates = _candidates(manifest_path, campaign.get("candidates", []))
    templates = _calculation_templates(
        manifest_path,
        campaign.get("calculation_templates", []),
    )
    descriptors = _descriptors(manifest_path, campaign.get("descriptors", []))
    ranking_rules = _ranking_rules(manifest_path, campaign.get("ranking", {}))

    return CampaignManifest(
        path=manifest_path,
        name=name,
        candidates=candidates,
        calculation_templates=templates,
        backend_mode=_optional_string(campaign, "backend_mode"),
        result_paths=result_paths,
        descriptors=descriptors,
        ranking_rules=ranking_rules,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: campaign manifest must be a mapping")
    return data


def _candidates(path: Path, value: Any) -> tuple[CampaignCandidate, ...]:
    items = _mapping_list(path, value, "campaign.candidates")
    seen: set[str] = set()
    candidates = []
    for index, item in enumerate(items):
        candidate_id = _required_string(path, item, "id", f"campaign.candidates[{index}]")
        if candidate_id in seen:
            raise ValueError(f"{path}: duplicate candidate id {candidate_id!r}")
        seen.add(candidate_id)
        structure_path = _optional_path(path, item, "structure")
        species_name = _optional_string(item, "species")
        if species_name is None and structure_path is None:
            raise ValueError(
                f"{path}: campaign.candidates[{index}] must define species or structure"
            )
        candidates.append(
            CampaignCandidate(
                id=candidate_id,
                species_name=species_name,
                structure_path=structure_path,
                tags=_string_tuple(path, item.get("tags", []), f"campaign.candidates[{index}].tags"),
                metadata=dict(item.get("metadata", {})),
            )
        )
    return tuple(candidates)


def _calculation_templates(path: Path, value: Any) -> tuple[CalculationTemplate, ...]:
    items = _mapping_list(path, value, "campaign.calculation_templates")
    seen: set[str] = set()
    templates = []
    for index, item in enumerate(items):
        template_id = _required_string(
            path,
            item,
            "id",
            f"campaign.calculation_templates[{index}]",
        )
        if template_id in seen:
            raise ValueError(f"{path}: duplicate calculation template id {template_id!r}")
        seen.add(template_id)
        keywords = item.get("keywords", {})
        if keywords in (None, ""):
            keywords = {}
        if not isinstance(keywords, dict):
            raise ValueError(
                f"{path}: campaign.calculation_templates[{index}].keywords "
                "must be a mapping"
            )
        templates.append(
            CalculationTemplate(
                id=template_id,
                backend=_optional_string(item, "backend"),
                method=_optional_string(item, "method"),
                basis=_optional_string(item, "basis"),
                task=_optional_string(item, "task"),
                solvent=_optional_string(item, "solvent"),
                keywords=dict(keywords),
            )
        )
    return tuple(templates)


def _descriptors(path: Path, value: Any) -> tuple[DescriptorDefinition, ...]:
    items = _mapping_list(path, value, "campaign.descriptors")
    seen: set[str] = set()
    descriptors = []
    for index, item in enumerate(items):
        name = _required_string(path, item, "name", f"campaign.descriptors[{index}]")
        if name in seen:
            raise ValueError(f"{path}: duplicate descriptor name {name!r}")
        seen.add(name)
        source = _optional_string(item, "source") or "result"
        metadata = {
            key: value
            for key, value in item.items()
            if key not in {"name", "source", "field", "quantity", "reference"}
        }
        descriptors.append(
            DescriptorDefinition(
                name=name,
                source=source,
                field=_optional_string(item, "field"),
                quantity=_optional_string(item, "quantity"),
                reference=_optional_string(item, "reference"),
                metadata=metadata,
            )
        )
    return tuple(descriptors)


def _ranking_rules(path: Path, value: Any) -> tuple[RankingRule, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, dict):
        raise ValueError(f"{path}: campaign.ranking must be a mapping")
    rules = _mapping_list(path, value.get("rules", []), "campaign.ranking.rules")
    parsed = []
    for index, rule in enumerate(rules):
        label = f"campaign.ranking.rules[{index}]"
        parsed.append(
            RankingRule(
                descriptor=_required_string(path, rule, "descriptor", label),
                direction=_optional_string(rule, "direction"),
                weight=_optional_float(path, rule, "weight", label),
                filter=_optional_string(rule, "filter"),
                minimum=_optional_float(path, rule, "minimum", label),
                maximum=_optional_float(path, rule, "maximum", label),
                allow_missing=bool(rule.get("allow_missing", False)),
            )
        )
    return tuple(parsed)


def _mapping_list(path: Path, value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError(f"{path}: {label} must be a list")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: {label}[{index}] must be a mapping")
    return value


def _path_list(path: Path, value: Any, label: str) -> tuple[Path, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return (_resolve_path(path, value, label),)
    if not isinstance(value, list):
        raise ValueError(f"{path}: {label} must be a path or list")
    return tuple(_resolve_path(path, item, f"{label}[{index}]") for index, item in enumerate(value))


def _resolve_path(path: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {label} must be a nonempty path string")
    resolved = Path(value)
    if not resolved.is_absolute():
        resolved = path.parent / resolved
    return resolved


def _optional_path(path: Path, data: dict[str, Any], key: str) -> Path | None:
    if key not in data or data[key] is None:
        return None
    return _resolve_path(path, data[key], key)


def _required_string(path: Path, data: dict[str, Any], key: str, label: str) -> str:
    value = _optional_string(data, key)
    if value is None or value == "":
        raise ValueError(f"{path}: {label}.{key} must be a nonempty string")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _optional_float(
    path: Path,
    data: dict[str, Any],
    key: str,
    label: str,
) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"{path}: {label}.{key} must be numeric")
    return float(value)


def _string_tuple(path: Path, value: Any, label: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{path}: {label} must be a list")
    strings = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{path}: {label}[{index}] must be a nonempty string")
        strings.append(item)
    return tuple(strings)
