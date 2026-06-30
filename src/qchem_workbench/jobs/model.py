"""Backend-independent external job metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from qchem_workbench.core.calculation import CalculationSpec


class JobStatus(str, Enum):
    """Lifecycle states for externally executed calculation jobs."""

    PLANNED = "planned"
    RENDERED = "rendered"
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARSED = "parsed"
    VALIDATED = "validated"
    ARCHIVED = "archived"

    @classmethod
    def from_value(cls, value: "JobStatus | str") -> "JobStatus":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value))
        except ValueError as exc:
            allowed = ", ".join(status.value for status in cls)
            raise ValueError(
                f"unsupported job status {value!r}; expected {allowed}"
            ) from exc


ALLOWED_JOB_STATUS_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.PLANNED: frozenset(
        {JobStatus.RENDERED, JobStatus.FAILED, JobStatus.ARCHIVED}
    ),
    JobStatus.RENDERED: frozenset(
        {JobStatus.SUBMITTED, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.ARCHIVED}
    ),
    JobStatus.SUBMITTED: frozenset(
        {JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.ARCHIVED}
    ),
    JobStatus.RUNNING: frozenset({JobStatus.COMPLETED, JobStatus.FAILED}),
    JobStatus.COMPLETED: frozenset(
        {JobStatus.PARSED, JobStatus.FAILED, JobStatus.ARCHIVED}
    ),
    JobStatus.FAILED: frozenset({JobStatus.ARCHIVED}),
    JobStatus.PARSED: frozenset({JobStatus.VALIDATED, JobStatus.ARCHIVED}),
    JobStatus.VALIDATED: frozenset({JobStatus.ARCHIVED}),
    JobStatus.ARCHIVED: frozenset(),
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Job:
    """Portable lifecycle metadata for an external calculation job.

    The model records what should be run or has been run elsewhere. It does not
    execute scientific engines, submit scheduler commands, or require a project
    database.
    """

    job_id: str
    backend_id: str
    calculation_spec: CalculationSpec | dict[str, Any]
    species_id: str | None = None
    structure_id: str | None = None
    input_files: tuple[Path | str, ...] = field(default_factory=tuple)
    output_files: tuple[Path | str, ...] = field(default_factory=tuple)
    working_directory: Path | str | None = None
    status: JobStatus | str = JobStatus.PLANNED
    scheduler: str | None = None
    submission_script: Path | str | None = None
    created_at: datetime | str | None = field(default_factory=_now_utc)
    submitted_at: datetime | str | None = None
    started_at: datetime | str | None = None
    completed_at: datetime | str | None = None
    parsed_at: datetime | str | None = None
    failure_reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.job_id = _required_text(self.job_id, "job_id")
        self.backend_id = _required_text(self.backend_id, "backend_id")
        if not self.species_id and not self.structure_id:
            raise ValueError("species_id or structure_id is required")
        if isinstance(self.calculation_spec, dict):
            self.calculation_spec = CalculationSpec(**self.calculation_spec)
        if not isinstance(self.calculation_spec, CalculationSpec):
            raise TypeError("calculation_spec must be a CalculationSpec")
        self.status = JobStatus.from_value(self.status)
        if self.status is JobStatus.FAILED and not _has_text(self.failure_reason):
            raise ValueError("failure_reason is required for failed jobs")
        self.input_files = tuple(Path(path) for path in self.input_files)
        self.output_files = tuple(Path(path) for path in self.output_files)
        self.working_directory = _optional_path(self.working_directory)
        self.submission_script = _optional_path(self.submission_script)
        self.created_at = _normalise_datetime(self.created_at)
        self.submitted_at = _normalise_datetime(self.submitted_at)
        self.started_at = _normalise_datetime(self.started_at)
        self.completed_at = _normalise_datetime(self.completed_at)
        self.parsed_at = _normalise_datetime(self.parsed_at)
        self.warnings = list(self.warnings)
        self.provenance = dict(self.provenance)

    def transition_to(
        self,
        status: JobStatus | str,
        *,
        timestamp: datetime | str | None = None,
        failure_reason: str | None = None,
        force: bool = False,
    ) -> "Job":
        """Move the job to another status with conservative validation."""

        next_status = JobStatus.from_value(status)
        if not force and next_status not in ALLOWED_JOB_STATUS_TRANSITIONS[self.status]:
            raise ValueError(
                f"invalid job status transition {self.status.value!r} -> "
                f"{next_status.value!r}"
            )

        when = _normalise_datetime(timestamp) or _now_utc()
        if next_status is JobStatus.FAILED:
            reason = failure_reason or self.failure_reason
            if not _has_text(reason):
                raise ValueError("failure_reason is required for failed jobs")
            self.failure_reason = str(reason)
            self.completed_at = self.completed_at or when
        elif failure_reason is not None:
            raise ValueError("failure_reason is only valid when marking a job failed")

        if next_status is JobStatus.SUBMITTED:
            self.submitted_at = when
        elif next_status is JobStatus.RUNNING:
            self.started_at = when
        elif next_status is JobStatus.COMPLETED:
            self.completed_at = when
        elif next_status is JobStatus.PARSED:
            self.parsed_at = when

        self.status = next_status
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "backend_id": self.backend_id,
            "calculation_spec": self.calculation_spec.to_dict(),
            "species_id": self.species_id,
            "structure_id": self.structure_id,
            "input_files": [str(path) for path in self.input_files],
            "output_files": [str(path) for path in self.output_files],
            "working_directory": (
                str(self.working_directory) if self.working_directory else None
            ),
            "status": self.status.value,
            "scheduler": self.scheduler,
            "submission_script": (
                str(self.submission_script) if self.submission_script else None
            ),
            "created_at": _datetime_to_string(self.created_at),
            "submitted_at": _datetime_to_string(self.submitted_at),
            "started_at": _datetime_to_string(self.started_at),
            "completed_at": _datetime_to_string(self.completed_at),
            "parsed_at": _datetime_to_string(self.parsed_at),
            "failure_reason": self.failure_reason,
            "warnings": list(self.warnings),
            "provenance": _json_ready(self.provenance),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        try:
            calculation_spec = data["calculation_spec"]
        except KeyError as exc:
            raise ValueError("calculation_spec is required") from exc
        return cls(
            job_id=data.get("job_id", ""),
            backend_id=data.get("backend_id", ""),
            calculation_spec=calculation_spec,
            species_id=data.get("species_id"),
            structure_id=data.get("structure_id"),
            input_files=tuple(data.get("input_files", [])),
            output_files=tuple(data.get("output_files", [])),
            working_directory=data.get("working_directory"),
            status=data.get("status", JobStatus.PLANNED),
            scheduler=data.get("scheduler"),
            submission_script=data.get("submission_script"),
            created_at=data.get("created_at"),
            submitted_at=data.get("submitted_at"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            parsed_at=data.get("parsed_at"),
            failure_reason=data.get("failure_reason"),
            warnings=list(data.get("warnings", [])),
            provenance=dict(data.get("provenance", {})),
        )


def _required_text(value: str, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _has_text(value: str | None) -> bool:
    return value is not None and bool(str(value).strip())


def _optional_path(value: Path | str | None) -> Path | None:
    if value is None:
        return None
    return Path(value)


def _normalise_datetime(value: datetime | str | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _datetime_to_string(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") if value else None


def _json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return _datetime_to_string(value)
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value
