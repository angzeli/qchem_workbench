from __future__ import annotations

import pytest

from qchem_workbench.active_learning.candidates import load_candidate_registry


def test_valid_candidate_file(tmp_path):
    path = _write_candidates(tmp_path)

    registry = load_candidate_registry(path)

    assert len(registry.candidates) == 2
    assert registry.candidates[0].id == "cand_001"
    assert registry.candidates[0].type == "molecule"
    assert registry.candidates[0].features["descriptor_source"] == "parsed_results"


def test_duplicate_candidate_id_is_error(tmp_path):
    path = _write_candidates(
        tmp_path,
        candidates=(
            "  - id: cand_001\n"
            "    type: molecule\n"
            "    species: CO\n"
            "  - id: cand_001\n"
            "    type: surface\n"
            "    structure: slab.xyz\n"
        ),
    )

    with pytest.raises(ValueError, match="duplicate candidate ID"):
        load_candidate_registry(path)


def test_unsupported_candidate_type_is_error(tmp_path):
    path = _write_candidates(
        tmp_path,
        candidates=(
            "  - id: cand_bad\n"
            "    type: catalyst_prediction\n"
            "    species: CO\n"
        ),
    )

    with pytest.raises(ValueError, match="unsupported candidate type"):
        load_candidate_registry(path)


def test_custom_metadata_is_preserved(tmp_path):
    path = _write_candidates(
        tmp_path,
        candidates=(
            "  - id: custom_001\n"
            "    type: custom\n"
            "    features:\n"
            "      descriptor_source: external_table\n"
            "    metadata:\n"
            "      notes: Synthetic custom candidate\n"
            "      batch: 3\n"
        ),
    )

    registry = load_candidate_registry(path)

    candidate = registry.candidates[0]
    assert candidate.type == "custom"
    assert candidate.features == {"descriptor_source": "external_table"}
    assert candidate.metadata == {"notes": "Synthetic custom candidate", "batch": 3}


def _write_candidates(
    tmp_path,
    *,
    candidates: str = (
        "  - id: cand_001\n"
        "    type: molecule\n"
        "    species: CO\n"
        "    features:\n"
        "      descriptor_source: parsed_results\n"
        "    metadata:\n"
        "      notes: Synthetic example candidate\n"
        "  - id: cand_002\n"
        "    type: surface\n"
        "    structure: slabs/cu111.xyz\n"
        "    metadata:\n"
        "      notes: Synthetic surface candidate\n"
    ),
):
    path = tmp_path / "candidates.yaml"
    path.write_text(
        "schema_version: 1\n"
        "candidates:\n"
        f"{candidates}",
        encoding="utf-8",
    )
    return path
