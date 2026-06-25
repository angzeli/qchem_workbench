"""Result storage utilities."""

from qchem_workbench.results.store import (
    RESULT_COLLECTION_SCHEMA_VERSION,
    append_results,
    deduplicate_results,
    load_result_collection,
    result_identity,
    save_result_collection,
)

__all__ = [
    "RESULT_COLLECTION_SCHEMA_VERSION",
    "append_results",
    "deduplicate_results",
    "load_result_collection",
    "result_identity",
    "save_result_collection",
]
