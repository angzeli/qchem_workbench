from __future__ import annotations

import csv
import json

from qchem_workbench.backends.gaussian_parser import parse_gaussian_output
from qchem_workbench.backends.orca_parser import parse_orca_output
from qchem_workbench.backends.pyscf_backend import MissingOptionalDependencyError
from qchem_workbench.cli import main
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.registry import load_species_registry
from qchem_workbench.results.store import save_result_collection


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
    assert "qchemwb 1.0.0" in captured.out


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


def test_render_gaussian_slurm_scheduler_template(tmp_path):
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
            "--scheduler",
            "slurm",
        ]
    )

    script = (out_dir / "water" / "run_gaussian.sh").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "#SBATCH --job-name=water" in script
    assert "Template only" in script
    assert not (out_dir / "water" / "water.log").exists()


def test_render_gaussian_scheduler_requires_job_folders(tmp_path):
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
            "--scheduler",
            "slurm",
        ]
    )

    assert exit_code == 1


def test_render_orca_generates_files(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "orca_inputs"

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    water_input = (out_dir / "water.inp").read_text(encoding="utf-8")
    assert exit_code == 0
    assert (out_dir / "carbon_dioxide.inp").exists()
    assert "! b3lyp def2-svp SP" in water_input
    assert "\n* xyz 0 1\n" in water_input
    assert "water\t" in captured.out


def test_render_orca_job_folder_layout(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "orca_inputs"

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "opt_freq",
            "--out",
            str(out_dir),
            "--job-folders",
        ]
    )

    water_input = (out_dir / "water" / "water.inp").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "! b3lyp def2-svp Opt Freq" in water_input
    assert (out_dir / "carbon_dioxide" / "carbon_dioxide.inp").exists()


def test_render_orca_refuses_to_overwrite_without_force(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "orca_inputs"
    out_dir.mkdir()
    water_path = out_dir / "water.inp"
    water_path.write_text("sentinel\n", encoding="utf-8")

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
        ]
    )

    assert exit_code == 1
    assert water_path.read_text(encoding="utf-8") == "sentinel\n"


def test_render_orca_run_script_generation(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "orca_inputs"

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
            "--job-folders",
            "--include-run-script",
        ]
    )

    script = (out_dir / "water" / "run_orca.sh").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Template only" in script
    assert 'ORCA_CMD="${ORCA_CMD:-orca}"' in script
    assert '"$ORCA_CMD" "water.inp" > "water.out"' in script


def test_render_orca_run_script_requires_job_folders(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "single_point",
            "--out",
            str(project_path / "orca_inputs"),
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


def test_parse_orca_scans_recursively_and_writes_json(tmp_path):
    outputs = tmp_path / "outputs"
    nested = outputs / "nested"
    nested.mkdir(parents=True)
    (outputs / "water.out").write_text(
        "! B3LYP def2-SVP SP\n"
        "FINAL SINGLE POINT ENERGY     -76.1000000000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )
    (nested / "co2.out").write_text(
        "! B3LYP def2-SVP SP\n"
        "FINAL SINGLE POINT ENERGY     -188.2000000000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )
    (outputs / "ignore.log").write_text("not scanned by parse-orca\n", encoding="utf-8")
    out_path = tmp_path / "results" / "orca_results.json"

    exit_code = main(["parse-orca", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["parser"] == "orca"
    assert [result["species_name"] for result in payload["results"]] == [
        "co2",
        "water",
    ]
    assert all(result["backend"] == "orca" for result in payload["results"])


def test_parse_orca_writes_csv(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "freq.out").write_text(
        "! B3LYP def2-SVP Freq\n"
        "Frequencies --   -10.0   250.0\n"
        "FINAL SINGLE POINT ENERGY     -1.0000000000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "orca_results.json"
    csv_path = tmp_path / "results" / "orca_results.csv"

    exit_code = main(
        [
            "parse-orca",
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


def test_parse_orca_continues_on_parser_exception(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "bad.out").write_text("synthetic malformed output\n", encoding="utf-8")
    (outputs / "good.out").write_text(
        "! B3LYP def2-SVP SP\n****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "orca_results.json"

    def fake_parse(path):
        if path.name == "bad.out":
            raise ValueError("synthetic ORCA parser failure")
        return parse_orca_output(path)

    monkeypatch.setattr("qchem_workbench.cli.parse_orca_output", fake_parse)

    exit_code = main(["parse-orca", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    failed = [result for result in payload["results"] if not result["success"]]
    assert exit_code == 0
    assert len(payload["results"]) == 2
    assert any(
        "synthetic ORCA parser failure" in result["warnings"][0]
        for result in failed
    )


def test_check_results_clean_result_set(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-76.0,
            )
        ],
    )

    exit_code = main(["check-results", str(results_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No quality checks reported." in captured.out


def test_check_results_reports_warnings(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=None,
            )
        ],
    )

    exit_code = main(["check-results", str(results_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "WARNING" in captured.out
    assert "missing_electronic_energy" in captured.out


def test_check_results_errors_exit_nonzero(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=False,
                electronic_energy_hartree=-76.0,
            )
        ],
    )

    exit_code = main(["check-results", str(results_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR" in captured.out
    assert "unsuccessful_calculation" in captured.out


def test_check_results_json_output(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=None,
            )
        ],
    )

    exit_code = main(["check-results", str(results_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["summary"]["warning"] == 1
    assert payload["checks"][0]["code"] == "missing_electronic_energy"


def test_check_results_uses_species_registry(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-76.0,
            )
        ],
    )

    exit_code = main(
        [
            "check-results",
            str(results_path),
            "--species",
            str(project_path / "species.yaml"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "unmatched_species" in captured.out


def test_reaction_table_electronic_mode(tmp_path, capsys):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    label: A to B\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="A",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-2.0,
            ),
            CalculationResult(
                species_name="B",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-1.5,
            ),
        ],
    )
    out_path = tmp_path / "reaction_table.csv"

    exit_code = main(
        [
            "reaction-table",
            str(pathway_path),
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert "delta_e_electronic" in captured.out
    assert rows[0]["quantity"] == "delta_e_electronic"
    assert float(rows[0]["delta_hartree"]) == 0.5


def test_reaction_table_gibbs_mode(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="A",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="freq",
                success=True,
                gibbs_free_energy_hartree=-2.0,
            ),
            CalculationResult(
                species_name="B",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="freq",
                success=True,
                gibbs_free_energy_hartree=-1.25,
            ),
        ],
    )
    out_path = tmp_path / "reaction_table.csv"

    exit_code = main(
        [
            "reaction-table",
            str(pathway_path),
            str(results_path),
            "--quantity",
            "gibbs",
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert rows[0]["quantity"] == "delta_g_gibbs"
    assert float(rows[0]["delta_hartree"]) == 0.75


def test_reaction_table_missing_data(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="A",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-2.0,
            )
        ],
    )
    out_path = tmp_path / "reaction_table.csv"

    exit_code = main(
        [
            "reaction-table",
            str(pathway_path),
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert rows[0]["complete"] == "False"
    assert rows[0]["missing_species"] == "B"
    assert rows[0]["delta_hartree"] == ""


def test_select_conformers_writes_json(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    out_path = tmp_path / "selected_conformers.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="ethanol",
                conformer_id="conf_001",
                backend="gaussian",
                method="b3lyp",
                basis="def2-svp",
                task="single_point",
                success=True,
                electronic_energy_hartree=-10.0,
            ),
            CalculationResult(
                species_name="ethanol",
                conformer_id="conf_002",
                backend="gaussian",
                method="b3lyp",
                basis="def2-svp",
                task="single_point",
                success=True,
                electronic_energy_hartree=-10.2,
            ),
        ],
    )

    exit_code = main(
        [
            "select-conformers",
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(out_path),
        ]
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert payload["selections"][0]["selected_conformer_id"] == "conf_002"
    assert "ethanol\tconf_002" in captured.out


def test_report_command_writes_markdown(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    results_path = project_path / "results" / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-76.0,
            )
        ],
    )
    out_path = project_path / "reports" / "report.md"

    exit_code = main(
        [
            "report",
            str(results_path),
            "--species",
            str(project_path / "species.yaml"),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    report = out_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Wrote Markdown report" in captured.out
    assert "# qchem-workbench report" in report
    assert "## Quality-check summary" in report
    assert "unmatched_species" in report


def test_plot_pathway_command_writes_png(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "mpl"))
    table_path = tmp_path / "reaction_table.csv"
    table_path.write_text(
        "reaction_id,label,quantity,complete,delta_hartree,delta_ev,delta_kj_mol,"
        "missing_species,notes\n"
        "r1,A to B,delta_e_electronic,True,0.1,2.7,262.5,,synthetic fixture\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "pathway.png"

    exit_code = main(["plot-pathway", str(table_path), "--out", str(out_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Wrote pathway plot" in captured.out
    assert out_path.read_bytes().startswith(b"\x89PNG")


def test_run_project_renders_gaussian_inputs(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    manifest_path = project_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n"
        "  inputs: gaussian_inputs\n"
        "  backend_mode: gaussian\n"
        "  calculation:\n"
        "    method: wb97xd\n"
        "    basis: 6-31g\n"
        "    task: single_point\n"
        "  steps: [render_gaussian]\n",
        encoding="utf-8",
    )

    exit_code = main(["run-project", str(manifest_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "STEP render_gaussian" in captured.out
    assert (project_path / "gaussian_inputs" / "water.gjf").exists()


def test_run_project_runs_mocked_pyscf_and_report(
    tmp_path, monkeypatch, capsys
):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    manifest_path = project_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n"
        "  results: results/results.json\n"
        "  reports: reports/report.md\n"
        "  backend_mode: pyscf\n"
        "  calculation:\n"
        "    method: b3lyp\n"
        "    basis: sto-3g\n"
        "    task: single_point\n"
        "  steps: [run_pyscf, quality_checks, report]\n",
        encoding="utf-8",
    )

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

    exit_code = main(["run-project", str(manifest_path)])

    captured = capsys.readouterr()
    payload = json.loads(
        (project_path / "results" / "results.json").read_text(encoding="utf-8")
    )
    report = (project_path / "reports" / "report.md").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "STEP run_pyscf" in captured.out
    assert "STEP report" in captured.out
    assert len(payload["results"]) == 3
    assert "# qchem-workbench report" in report


def test_run_project_parses_gaussian_fixture_and_generates_report(
    tmp_path, capsys
):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    outputs = project_path / "outputs"
    (outputs / "water.log").write_text(
        " # wb97xd/6-31g\n"
        " SCF Done:  E(RB3LYP) =  -76.1000000000     A.U. after 10 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    manifest_path = project_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n"
        "  outputs: outputs\n"
        "  results: results/gaussian_results.json\n"
        "  reports: reports/report.md\n"
        "  steps: [parse_gaussian, quality_checks, report]\n",
        encoding="utf-8",
    )

    exit_code = main(["run-project", str(manifest_path)])

    captured = capsys.readouterr()
    payload = json.loads(
        (project_path / "results" / "gaussian_results.json").read_text(
            encoding="utf-8"
        )
    )
    report = (project_path / "reports" / "report.md").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "STEP parse_gaussian" in captured.out
    assert payload["results"][0]["species_name"] == "water"
    assert payload["results"][0]["electronic_energy_hartree"] == -76.1
    assert "unmatched_species" in report


def test_triage_command_writes_failed_jobs_markdown(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="missing-energy",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                warnings=["SCF electronic energy was not parsed."],
            )
        ],
    )
    out_path = tmp_path / "failed_jobs.md"

    exit_code = main(["triage", str(results_path), "--out", str(out_path)])

    captured = capsys.readouterr()
    report = out_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "missing_energy" in captured.out
    assert "# Failed job triage" in report
    assert "missing-energy" in report
