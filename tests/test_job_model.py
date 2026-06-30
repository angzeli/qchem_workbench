from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.jobs import Job, JobStatus


def _spec() -> CalculationSpec:
    return CalculationSpec(
        backend="gaussian",
        method="b3lyp",
        basis="sto-3g",
        task="single_point",
    )


def test_job_creation_defaults():
    job = Job(
        job_id="water_sp",
        backend_id="gaussian",
        calculation_spec=_spec(),
        species_id="water",
    )

    assert job.status is JobStatus.PLANNED
    assert job.created_at is not None
    assert job.warnings == []


def test_job_serialisation_round_trip():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    job = Job(
        job_id="water_sp",
        backend_id="gaussian",
        calculation_spec=_spec(),
        species_id="water",
        input_files=(Path("jobs/water/water.gjf"),),
        output_files=("jobs/water/water.log",),
        working_directory="jobs/water",
        scheduler="slurm",
        submission_script="jobs/water/run.sh",
        created_at=created_at,
        warnings=["synthetic fixture warning"],
        provenance={"source": Path("examples/jobs.yaml")},
    )

    payload = job.to_dict()
    json.dumps(payload)
    restored = Job.from_dict(payload)

    assert payload["status"] == "planned"
    assert payload["input_files"] == ["jobs/water/water.gjf"]
    assert payload["provenance"] == {"source": "examples/jobs.yaml"}
    assert restored.job_id == job.job_id
    assert restored.calculation_spec.to_dict() == job.calculation_spec.to_dict()
    assert restored.working_directory == Path("jobs/water")


def test_job_can_target_structure_instead_of_species():
    job = Job(
        job_id="slab_relax",
        backend_id="qe",
        calculation_spec={
            "backend": "qe",
            "method": "pbe",
            "basis": None,
            "task": "relax",
        },
        structure_id="cu_slab",
    )

    assert job.structure_id == "cu_slab"
    assert job.calculation_spec.backend == "qe"


def test_invalid_status_is_rejected():
    with pytest.raises(ValueError, match="unsupported job status"):
        Job(
            job_id="bad_status",
            backend_id="gaussian",
            calculation_spec=_spec(),
            species_id="water",
            status="unknown",
        )


def test_missing_required_fields_are_rejected():
    with pytest.raises(ValueError, match="job_id is required"):
        Job(
            job_id="",
            backend_id="gaussian",
            calculation_spec=_spec(),
            species_id="water",
        )

    with pytest.raises(ValueError, match="backend_id is required"):
        Job(
            job_id="water_sp",
            backend_id="",
            calculation_spec=_spec(),
            species_id="water",
        )

    with pytest.raises(ValueError, match="species_id or structure_id is required"):
        Job(
            job_id="water_sp",
            backend_id="gaussian",
            calculation_spec=_spec(),
        )


def test_status_transitions_are_validated():
    job = Job(
        job_id="water_sp",
        backend_id="gaussian",
        calculation_spec=_spec(),
        species_id="water",
    )

    with pytest.raises(ValueError, match="invalid job status transition"):
        job.transition_to(JobStatus.RUNNING)

    job.transition_to(JobStatus.RENDERED)
    job.transition_to("submitted", timestamp="2026-01-01T00:00:00+00:00")

    assert job.status is JobStatus.SUBMITTED
    assert job.submitted_at == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_failed_status_requires_reason():
    job = Job(
        job_id="water_sp",
        backend_id="gaussian",
        calculation_spec=_spec(),
        species_id="water",
    )

    with pytest.raises(ValueError, match="failure_reason is required"):
        job.transition_to(JobStatus.FAILED)

    job.transition_to(JobStatus.FAILED, failure_reason="scheduler exited nonzero")

    assert job.status is JobStatus.FAILED
    assert job.failure_reason == "scheduler exited nonzero"
