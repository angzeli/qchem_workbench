from __future__ import annotations

import qchem_workbench
import qchem_workbench.analysis as analysis
import qchem_workbench.backends as backends
import qchem_workbench.campaigns as campaigns
import qchem_workbench.core as core
import qchem_workbench.geometry as geometry
import qchem_workbench.projects as projects
import qchem_workbench.reports as reports
import qchem_workbench.results as results
import qchem_workbench.schema as schema
import qchem_workbench.templates as templates


def test_public_packages_define_importable_all_exports():
    packages = [
        qchem_workbench,
        analysis,
        backends,
        campaigns,
        core,
        geometry,
        projects,
        reports,
        results,
        schema,
        templates,
    ]

    for package in packages:
        assert package.__all__
        for name in package.__all__:
            assert hasattr(package, name), f"{package.__name__}.{name} is missing"


def test_schema_versions_are_consistent():
    assert schema.SCHEMA_FILE_TYPES == {
        "species_registry": core.SUPPORTED_SCHEMA_VERSION,
        "result_store": results.RESULT_COLLECTION_SCHEMA_VERSION,
        "pathway": analysis.PATHWAY_SCHEMA_VERSION,
        "project_manifest": projects.PROJECT_MANIFEST_SCHEMA_VERSION,
        "campaign": campaigns.CAMPAIGN_SCHEMA_VERSION,
    }
    assert set(schema.SCHEMA_FILE_TYPES.values()) == {1}
