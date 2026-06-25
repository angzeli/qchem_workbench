from __future__ import annotations

import json

from qchem_workbench.backends.pyscf_backend import MissingOptionalDependencyError
from qchem_workbench.cli import main
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.registry import load_species_registry


def test_cli_help(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "qchemwb" in captured.out


def test_cli_version(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "qchemwb 0.1.0" in captured.out


def test_init_blank(tmp_path):
    project_path = tmp_path / "demo"

    exit_code = main(["init", str(project_path), "--template", "blank"])

    assert exit_code == 0
    assert (project_path / "species.yaml").exists()
    assert (project_path / "xyz").is_dir()
    assert (project_path / "outputs").is_dir()
    assert (project_path / "results").is_dir()
    assert (project_path / "reports").is_dir()
    assert load_species_registry(project_path / "species.yaml") == []


def test_init_basic(tmp_path):
    project_path = tmp_path / "demo"

    exit_code = main(["init", str(project_path), "--template", "basic"])

    species = load_species_registry(project_path / "species.yaml")
    assert exit_code == 0
    assert {item.name for item in species} == {
        "water",
        "carbon_dioxide",
        "carbon_monoxide",
    }


def test_init_co2rr_template_is_explicit_and_synthetic(tmp_path):
    project_path = tmp_path / "demo"

    exit_code = main(["init", str(project_path), "--template", "co2rr"])

    species = load_species_registry(project_path / "species.yaml")
    assert exit_code == 0
    assert {item.name for item in species} == {
        "co2rr_carbon_dioxide",
        "co2rr_carbon_monoxide",
        "co2rr_water",
    }
    assert all("synthetic" in item.tags for item in species)


def test_validate_success(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0

    exit_code = main(["validate", str(project_path / "species.yaml")])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Validated 3 species" in captured.out


def test_validate_failure(tmp_path, capsys):
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text("schema_version: 99\nspecies: []\n", encoding="utf-8")

    exit_code = main(["validate", str(registry_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "unsupported schema_version" in captured.err


def test_init_refuses_to_overwrite_without_force(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "blank"]) == 0
    registry_path = project_path / "species.yaml"
    registry_path.write_text("sentinel\n", encoding="utf-8")

    exit_code = main(["init", str(project_path), "--template", "basic"])

    assert exit_code == 1
    assert registry_path.read_text(encoding="utf-8") == "sentinel\n"


def test_run_pyscf_writes_json_with_mocked_backend(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_path = project_path / "results" / "pyscf_results.json"

    class FakeBackend:
        def run(self, species, spec):
            return CalculationResult(
                species_name=species.name,
                backend="pyscf",
                method=spec.method,
                basis=spec.basis,
                task=spec.task,
                success=True,
                electronic_energy_hartree=-1.0,
            )

    monkeypatch.setattr("qchem_workbench.cli.PySCFBackend", FakeBackend)

    exit_code = main(
        [
            "run-pyscf",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "sto-3g",
            "--out",
            str(out_path),
        ]
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert payload["calculation"]["method"] == "b3lyp"
    assert payload["calculation"]["basis"] == "sto-3g"
    assert len(payload["results"]) == 3
    assert all(result["success"] for result in payload["results"])
    assert "species\tsuccess" in captured.out


def test_run_pyscf_continues_after_species_failure(tmp_path, monkeypatch):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_path = project_path / "results" / "pyscf_results.json"

    class FakeBackend:
        def run(self, species, spec):
            if species.name == "carbon_dioxide":
                raise RuntimeError("synthetic backend failure")
            return CalculationResult(
                species_name=species.name,
                backend="pyscf",
                method=spec.method,
                basis=spec.basis,
                task=spec.task,
                success=True,
            )

    monkeypatch.setattr("qchem_workbench.cli.PySCFBackend", FakeBackend)

    exit_code = main(
        [
            "run-pyscf",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "sto-3g",
            "--out",
            str(out_path),
        ]
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    failed = [result for result in payload["results"] if not result["success"]]
    assert exit_code == 1
    assert len(payload["results"]) == 3
    assert failed[0]["species_name"] == "carbon_dioxide"
    assert "synthetic backend failure" in failed[0]["warnings"][0]


def test_run_pyscf_reports_missing_optional_dependency(
    tmp_path, monkeypatch, capsys
):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_path = project_path / "results" / "pyscf_results.json"

    class MissingBackend:
        def run(self, species, spec):
            raise MissingOptionalDependencyError("install optional PySCF dependency")

    monkeypatch.setattr("qchem_workbench.cli.PySCFBackend", MissingBackend)

    exit_code = main(
        [
            "run-pyscf",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "sto-3g",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "install optional PySCF dependency" in captured.err
    assert not out_path.exists()


def test_render_gaussian_generates_files(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    water_input = (out_dir / "water.gjf").read_text(encoding="utf-8")
    assert exit_code == 0
    assert (out_dir / "carbon_dioxide.gjf").exists()
    assert "# wb97xd/6-31+G(d,p)" in water_input
    assert "\n0 1\n" in water_input
    assert "water\t" in captured.out


def test_render_gaussian_refuses_to_overwrite_without_force(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"
    out_dir.mkdir()
    water_path = out_dir / "water.gjf"
    water_path.write_text("sentinel\n", encoding="utf-8")

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
        ]
    )

    assert exit_code == 1
    assert water_path.read_text(encoding="utf-8") == "sentinel\n"


def test_render_gaussian_uses_task_solvent_and_extra_keywords(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "opt_freq",
            "--solvent",
            "smd,solvent=water",
            "--route-keyword",
            "scf=tight",
            "--out",
            str(out_dir),
        ]
    )

    water_input = (out_dir / "water.gjf").read_text(encoding="utf-8")
    assert exit_code == 0
    assert (
        "# wb97xd/6-31+G(d,p) opt freq scrf=(smd,solvent=water) scf=tight"
        in water_input
    )
