"""JSON result collection storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qchem_workbench.core.result import CalculationResult


RESULT_COLLECTION_SCHEMA_VERSION = 1


def save_result_collection(
    path: Path,
    results: list[CalculationResult],
    metadata: dict[str, Any] | None = None,
) -> None:
    payload = {
        "schema_version": RESULT_COLLECTION_SCHEMA_VERSION,
        "results": [result.to_dict() for result in results],
    }
    if metadata:
        payload["metadata"] = dict(metadata)

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_result_collection(path: Path) -> list[CalculationResult]:
    input_path = Path(path)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{input_path}: result collection must be a JSON object")
    if "schema_version" not in data:
        raise ValueError(f"{input_path}: missing schema_version")
    schema_version = data["schema_version"]
    if schema_version != RESULT_COLLECTION_SCHEMA_VERSION:
        raise ValueError(
            f"{input_path}: unsupported schema_version {schema_version!r}; "
            f"expected {RESULT_COLLECTION_SCHEMA_VERSION}"
        )

    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError(f"{input_path}: results must be a list")
    return [CalculationResult.from_dict(result) for result in results]


def append_results(
    path: Path,
    new_results: list[CalculationResult],
    deduplicate: bool = True,
) -> list[CalculationResult]:
    input_path = Path(path)
    existing = load_result_collection(input_path) if input_path.exists() else []
    combined = [*existing, *new_results]
    if deduplicate:
        combined = deduplicate_results(combined)
    save_result_collection(input_path, combined)
    return combined


def deduplicate_results(results: list[CalculationResult]) -> list[CalculationResult]:
    deduplicated: dict[
        tuple[str, str, str | None, str | None, str | None, str | None],
        CalculationResult,
    ] = {}
    for result in results:
        deduplicated[result_identity(result)] = result
    return list(deduplicated.values())


def result_identity(
    result: CalculationResult,
) -> tuple[str, str, str | None, str | None, str | None, str | None]:
    run_id = result.metadata.get("run_id")
    source_or_run_id = str(result.source_path) if result.source_path else run_id
    return (
        result.species_name,
        result.backend,
        result.method,
        result.basis,
        result.task,
        source_or_run_id,
    )
