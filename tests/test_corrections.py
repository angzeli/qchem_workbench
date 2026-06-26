from __future__ import annotations

import pytest

from qchem_workbench.analysis.corrections import (
    CorrectionTerm,
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
