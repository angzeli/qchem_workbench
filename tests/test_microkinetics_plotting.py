from __future__ import annotations

import pytest

from qchem_workbench.cli import main
from qchem_workbench.microkinetics.plotting import (
    plot_rates_csv,
    plot_sensitivity_csv,
    plot_steady_state_csv,
    plot_trajectory_csv,
    plot_uncertainty_csv,
)


def test_plot_trajectory_file_created(tmp_path):
    csv_path = tmp_path / "trajectory.csv"
    csv_path.write_text(
        "time,A_star,star\n0.0,1.0,0.0\n1.0,0.4,0.6\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "coverage.png"

    plot_trajectory_csv(csv_path, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_plot_steady_state_file_created(tmp_path):
    csv_path = tmp_path / "steady.csv"
    csv_path.write_text("species,coverage\nA_star,0.4\nstar,0.6\n", encoding="utf-8")
    out_path = tmp_path / "steady.png"

    plot_steady_state_csv(csv_path, out_path)

    assert out_path.exists()


def test_plot_rates_file_created(tmp_path):
    csv_path = tmp_path / "rates.csv"
    csv_path.write_text(
        "row_type,id,phase,rate,forward_rate,reverse_rate,unit,active_site_count,notes\n"
        "species,P_g,gas,0.5,,,s^-1,,\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "rates.png"

    plot_rates_csv(csv_path, out_path)

    assert out_path.exists()


def test_plot_sensitivity_file_created(tmp_path):
    csv_path = tmp_path / "sensitivity.csv"
    csv_path.write_text(
        "parameter_id,observable,perturbation_ln,baseline_value,perturbed_value,"
        "sensitivity,baseline_converged,perturbed_converged,warnings\n"
        "k1,product_rate:P_g,0.01,0.5,0.51,1.0,True,True,\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "sensitivity.png"

    plot_sensitivity_csv(csv_path, out_path)

    assert out_path.exists()


def test_plot_uncertainty_file_created(tmp_path):
    csv_path = tmp_path / "uncertainty.csv"
    csv_path.write_text(
        "observable,n_samples,success_count,failure_count,mean,median,q05,q95,seed\n"
        "product_rate:P_g,5,5,0,0.5,0.5,0.4,0.6,1\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "uncertainty.png"

    plot_uncertainty_csv(csv_path, out_path)

    assert out_path.exists()


def test_missing_columns_are_clear_errors(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("A_star\n0.5\n", encoding="utf-8")

    with pytest.raises(ValueError, match="time column"):
        plot_trajectory_csv(csv_path, tmp_path / "bad.png")


def test_microkinetics_plot_cli(tmp_path, capsys):
    csv_path = tmp_path / "trajectory.csv"
    csv_path.write_text(
        "time,A_star,star\n0.0,1.0,0.0\n1.0,0.4,0.6\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "coverage.png"

    exit_code = main(
        [
            "microkinetics",
            "plot-trajectory",
            str(csv_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "trajectory plot" in captured.out
    assert out_path.exists()
