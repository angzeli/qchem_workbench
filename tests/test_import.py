from __future__ import annotations

import qchem_workbench
from qchem_workbench import analysis, backends, core, projects, reports, results


def test_package_imports():
    assert qchem_workbench.__version__ == "1.0.0"


def test_public_package_exports():
    assert "Species" in core.__all__
    assert "CalculationResult" in core.__all__
    assert "run_quality_checks" in analysis.__all__
    assert "Backend" in backends.__all__
    assert "load_project_manifest" in projects.__all__
    assert "generate_markdown_report" in reports.__all__
    assert "load_result_collection" in results.__all__
