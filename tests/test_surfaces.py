from __future__ import annotations

import pytest

from qchem_workbench.analysis.surfaces import (
    AdsorptionSite,
    CoverageSpec,
    SurfaceModel,
    validate_adsorption_sites,
)


def test_valid_surface_site():
    surface = SurfaceModel(
        structure_id="synthetic_cu111",
        miller_index=(1, 1, 1),
        slab_layers=4,
        vacuum_thickness_angstrom=15.0,
        surface_area_angstrom2=25.0,
        fixed_atom_indices=(0, 1),
    )
    site = AdsorptionSite(
        site_id="site_top_1",
        site_type_label="top",
        coordinates_angstrom=(1.0, 2.0, 3.0),
        involved_atom_indices=(4,),
        notes="Synthetic fixture site label; user-defined only.",
    )

    assert surface.surface_area_unit == "angstrom^2"
    assert surface.vacuum_thickness_unit == "angstrom"
    assert site.coordinate_unit == "angstrom"
    assert site.coordinates_angstrom == (1.0, 2.0, 3.0)


def test_duplicate_site_ids_are_error():
    site = AdsorptionSite(
        site_id="site_1",
        site_type_label="custom",
        coordinates_angstrom=(0.0, 0.0, 0.0),
    )

    with pytest.raises(ValueError, match="duplicate adsorption site"):
        validate_adsorption_sites((site, site))


def test_coverage_calculation_if_surface_area_exists():
    coverage = CoverageSpec(
        adsorbate_count=2,
        surface_area_angstrom2=50.0,
        coverage_label="synthetic 2 per cell",
        monolayer_definition_note="Synthetic fixture note.",
    )

    assert coverage.coverage_adsorbates_per_angstrom2 == pytest.approx(0.04)
    assert coverage.coverage_unit == "adsorbates/angstrom^2"
    assert coverage.warnings() == ()


def test_missing_area_produces_warning():
    coverage = CoverageSpec(adsorbate_count=1, coverage_label="one adsorbate")

    assert coverage.coverage_adsorbates_per_angstrom2 is None
    assert "surface area is missing" in coverage.warnings()[0]
