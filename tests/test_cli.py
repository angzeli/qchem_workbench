from __future__ import annotations

import csv
import json

from qchem_workbench.backends.gaussian_parser import parse_gaussian_output
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


def test_render_gaussian_flat_layout_remains_default(tmp_path):
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

    assert exit_code == 0
    assert (out_dir / "water.gjf").exists()
    assert not (out_dir / "water" / "water.gjf").exists()


def test_render_gaussian_job_folder_layout(tmp_path):
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
            "--job-folders",
        ]
    )

    water_input = (out_dir / "water" / "water.gjf").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "%chk=water.chk\n" in water_input
    assert (out_dir / "carbon_dioxide" / "carbon_dioxide.gjf").exists()


def test_render_gaussian_run_script_generation(tmp_path):
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
            "--job-folders",
            "--include-run-script",
        ]
    )

    script = (out_dir / "water" / "run_gaussian.sh").read_text(encoding="utf-8")
    assert exit_code == 0
    assert 'GAUSSIAN_CMD="${GAUSSIAN_CMD:-g16}"' in script
    assert '"$GAUSSIAN_CMD" < "water.gjf" > "water.log"' in script


def test_render_gaussian_run_script_requires_job_folders(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0

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
            str(project_path / "gaussian_inputs"),
            "--include-run-script",
        ]
    )

    assert exit_code == 1


def test_parse_gaussian_scans_recursively_and_writes_json(tmp_path):
    outputs = tmp_path / "outputs"
    nested = outputs / "nested"
    nested.mkdir(parents=True)
    (outputs / "water.log").write_text(
        " # wb97xd/6-31g\n"
        " SCF Done:  E(RB3LYP) =  -76.1000000000     A.U. after 10 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    (nested / "co2.out").write_text(
        " # wb97xd/6-31g\n"
        " SCF Done:  E(RB3LYP) =  -188.2000000000     A.U. after 10 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    (outputs / "ignore.txt").write_text("not a Gaussian output\n", encoding="utf-8")
    out_path = tmp_path / "results" / "gaussian_results.json"

    exit_code = main(["parse-gaussian", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["parser"] == "gaussian"
    assert [result["species_name"] for result in payload["results"]] == [
        "co2",
        "water",
    ]


def test_parse_gaussian_writes_csv(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "freq.log").write_text(
        " # wb97xd/6-31g freq\n"
        " Frequencies --   -10.0   250.0\n"
        " SCF Done:  E(RB3LYP) =  -1.0000000000     A.U. after 3 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "gaussian_results.json"
    csv_path = tmp_path / "results" / "gaussian_results.csv"

    exit_code = main(
        [
            "parse-gaussian",
            str(outputs),
            "--out",
            str(out_path),
            "--csv",
            str(csv_path),
        ]
    )

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert exit_code == 0
    assert rows[0]["species_name"] == "freq"
    assert rows[0]["negative_frequency_count"] == "1"
    assert rows[0]["most_negative_frequency_cm1"] == "-10.0"


def test_parse_gaussian_continues_on_parser_exception(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "bad.log").write_text("synthetic malformed output\n", encoding="utf-8")
    (outputs / "good.log").write_text(
        " # hf/sto-3g\n Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "gaussian_results.json"

    def fake_parse(path):
        if path.name == "bad.log":
            raise ValueError("synthetic parser failure")
        return parse_gaussian_output(path)

    monkeypatch.setattr("qchem_workbench.cli.parse_gaussian_output", fake_parse)

    exit_code = main(["parse-gaussian", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    failed = [result for result in payload["results"] if not result["success"]]
    assert exit_code == 0
    assert len(payload["results"]) == 2
    assert any(
        "synthetic parser failure" in result["warnings"][0] for result in failed
    )
