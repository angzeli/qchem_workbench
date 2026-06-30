from __future__ import annotations

import json

import pytest

from qchem_workbench.analysis.corrections import (
    CorrectionLedger,
    CorrectionLedgerEntry,
    CorrectionTerm,
    apply_correction_ledger,
    apply_corrections,
    attach_corrections,
)


def test_apply_one_correction():
    attachment = attach_corrections(
        "reaction",
        "r1",
        [
            CorrectionTerm(
                label="parsed thermal correction",
                value_eV=0.10,
                sign_convention="added to uncorrected delta G",
                source="synthetic fixture parsed field",
            )
        ],
    )

    corrected = apply_corrections(1.25, attachment)

    assert corrected.corrected_value_eV == pytest.approx(1.35)
    assert corrected.correction_total_eV == pytest.approx(0.10)
    assert corrected.warnings == ()


def test_apply_multiple_corrections():
    attachment = attach_corrections(
        "adsorption_system",
        "co_on_surface",
        [
            CorrectionTerm(
                label="user correction A",
                value_eV=0.20,
                sign_convention="added to adsorption free energy",
                source="synthetic fixture user table",
            ),
            CorrectionTerm(
                label="user correction B",
                value_eV=-0.05,
                sign_convention="added to adsorption free energy",
                source="synthetic fixture user table",
            ),
        ],
    )

    corrected = apply_corrections(-0.40, attachment)

    assert corrected.corrected_value_eV == pytest.approx(-0.25)
    assert corrected.correction_total_eV == pytest.approx(0.15)


def test_missing_correction_source_warning():
    attachment = attach_corrections(
        "species",
        "water",
        [
            CorrectionTerm(
                label="undocumented term",
                value_eV=0.01,
                sign_convention="added to species free energy",
            )
        ],
    )

    corrected = apply_corrections(0.0, attachment)

    assert len(corrected.warnings) == 1
    assert "has no source" in corrected.warnings[0]


def test_total_equals_sum_of_visible_terms():
    attachment = attach_corrections(
        "reaction",
        "r1",
        [
            CorrectionTerm("term 1", 0.10, "added", "synthetic fixture"),
            CorrectionTerm("term 2", 0.30, "added", "synthetic fixture"),
        ],
    )

    corrected = apply_corrections(2.0, attachment)
    visible_sum = sum(row.value_eV for row in corrected.correction_table)

    assert corrected.correction_total_eV == pytest.approx(visible_sum)
    assert corrected.corrected_value_eV == pytest.approx(
        corrected.base_value_eV + visible_sum
    )


def test_correction_ledger_sums_visible_terms():
    ledger = CorrectionLedger(
        (
            CorrectionLedgerEntry(
                term_id="thermal_1",
                label="synthetic thermal term",
                value=0.20,
                unit="eV",
                sign="positive",
                applies_to="reaction:r1",
                source="synthetic fixture",
                category="thermal",
            ),
            CorrectionLedgerEntry(
                term_id="solvation_1",
                label="synthetic solvation term",
                value=0.05,
                unit="eV",
                sign="negative",
                applies_to="reaction:r1",
                source="synthetic fixture",
                category="solvation",
            ),
        )
    )

    corrected = apply_correction_ledger(1.0, "eV", ledger)

    assert corrected.correction_total == pytest.approx(0.15)
    assert corrected.corrected_value == pytest.approx(1.15)
    assert corrected.warnings == ()
    assert corrected.ledger.entries == ledger.entries


def test_correction_ledger_unit_mismatch_errors():
    ledger = CorrectionLedger(
        (
            CorrectionLedgerEntry(
                term_id="term_1",
                label="synthetic term",
                value=1.0,
                unit="eV",
                sign="positive",
                applies_to="reaction:r1",
                source="synthetic fixture",
            ),
            CorrectionLedgerEntry(
                term_id="term_2",
                label="synthetic term",
                value=1.0,
                unit="kJ/mol",
                sign="positive",
                applies_to="reaction:r1",
                source="synthetic fixture",
            ),
        )
    )

    with pytest.raises(ValueError, match="unit mismatch"):
        apply_correction_ledger(1.0, "eV", ledger)


def test_correction_ledger_missing_source_warning():
    ledger = CorrectionLedger(
        (
            CorrectionLedgerEntry(
                term_id="user_1",
                label="undocumented user term",
                value=0.1,
                unit="eV",
                sign="positive",
                applies_to="adsorption:co_on_surface",
                source=None,
                category="user",
            ),
        )
    )

    corrected = apply_correction_ledger(None, "eV", ledger)

    assert corrected.corrected_value is None
    assert corrected.correction_total == pytest.approx(0.1)
    assert len(corrected.warnings) == 1
    assert "has no source" in corrected.warnings[0]


def test_correction_ledger_sign_aliases_and_serialisation():
    ledger = CorrectionLedger(
        (
            CorrectionLedgerEntry(
                term_id="positive",
                label="positive term",
                value=0.4,
                unit="eV",
                sign="+",
                applies_to="che:step_1",
                source="synthetic fixture",
                provenance={"file": "corrections.yaml"},
                notes="example only",
                category="potential",
            ),
            CorrectionLedgerEntry(
                term_id="negative",
                label="negative term",
                value=0.1,
                unit="eV",
                sign="subtract",
                applies_to="che:step_1",
                source="synthetic fixture",
                category="pH",
            ),
        )
    )

    payload = ledger.to_dict()
    json.dumps(payload)
    restored = CorrectionLedger.from_dict(payload)
    corrected = apply_correction_ledger(0.0, "eV", restored)

    assert payload["entries"][0]["sign"] == "positive"
    assert payload["entries"][1]["sign"] == "negative"
    assert corrected.correction_total == pytest.approx(0.3)
    assert corrected.to_dict()["corrected_value"] == pytest.approx(0.3)


def test_correction_ledger_rejects_duplicate_term_ids():
    entry = CorrectionLedgerEntry(
        term_id="duplicate",
        label="synthetic term",
        value=0.1,
        unit="eV",
        sign="positive",
        applies_to="reaction:r1",
        source="synthetic fixture",
    )

    with pytest.raises(ValueError, match="duplicate correction ledger term_id"):
        CorrectionLedger((entry, entry))
