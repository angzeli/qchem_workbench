from __future__ import annotations

import csv

import pytest

from qchem_workbench.cli import main
from qchem_workbench.microkinetics.schema import load_microkinetic_model
from qchem_workbench.microkinetics.uncertainty import (
    UncertaintySampleRow,
    load_parameter_distributions,
    microkinetic_uncertainty_sample,
    sample_rate_parameter_sets,
    uncertainty_summary,
)


def test_deterministic_sampling_with_seed(tmp_path):
    distributions = load_parameter_distributions(_write_distributions(tmp_path))

    first = sample_rate_parameter_sets(distributions, n_samples=3, seed=1)
    second = sample_rate_parameter_sets(distributions, n_samples=3, seed=1)

    assert [
        sample.rate_constants["k_form"].value for sample in first
    ] == pytest.approx([
        sample.rate_constants["k_form"].value for sample in second
    ])


def test_fixed_parameter_sampling(tmp_path):
    distributions = load_parameter_distributions(
        _write_distributions(
            tmp_path,
            body=(
                "  k_fixed:\n"
                "    distribution: fixed\n"
                "    value: 2.5\n"
                "    unit: s^-1\n"
                "    source: synthetic uncertainty range\n"
            ),
        )
    )

    samples = sample_rate_parameter_sets(distributions, n_samples=3, seed=5)

    assert [sample.rate_constants["k_fixed"].value for sample in samples] == [2.5] * 3


def test_failed_sample_tracking(tmp_path):
    pytest.importorskip("scipy")
    model = load_microkinetic_model(_write_two_step_model(tmp_path))
    distributions = load_parameter_distributions(
        _write_distributions(
            tmp_path,
            body=(
                "  k_form:\n"
                "    distribution: fixed\n"
                "    value: 1.0\n"
                "    unit: s^-1\n"
                "    source: synthetic uncertainty range\n"
            ),
        )
    )

    result = microkinetic_uncertainty_sample(
        model,
        distributions,
        {"A_star": 0.2, "star": 0.8},
        {},
        observable="product_rate:P_g",
        n_samples=2,
        seed=1,
    )

    assert result.summary.failure_count == 2
    assert result.summary.success_count == 0


def test_summary_statistic_calculation():
    rows = [
        UncertaintySampleRow(0, "product_rate:P_g", 1.0, True),
        UncertaintySampleRow(1, "product_rate:P_g", 3.0, True),
        UncertaintySampleRow(2, "product_rate:P_g", None, False),
    ]

    summary = uncertainty_summary(rows, observable="product_rate:P_g", seed=7)

    assert summary.mean == pytest.approx(2.0)
    assert summary.median == pytest.approx(2.0)
    assert summary.failure_count == 1
    assert summary.seed == 7


def test_microkinetics_sample_cli(tmp_path, capsys):
    pytest.importorskip("scipy")
    model_path = _write_two_step_model(tmp_path)
    distributions_path = _write_distributions(tmp_path)
    conditions_path = _write_conditions_file(tmp_path, distributions_path.name)
    out_path = tmp_path / "results" / "uncertainty.csv"

    exit_code = main(
        [
            "microkinetics",
            "sample",
            str(model_path),
            "--conditions",
            str(conditions_path),
            "--n",
            "3",
            "--seed",
            "1",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "product_rate:P_g" in captured.out
    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["failure_count"] == "0"


def _write_distributions(tmp_path, *, body: str | None = None):
    path = tmp_path / "distributions.yaml"
    path.write_text(
        "schema_version: 1\n"
        "parameter_distributions:\n"
        + (
            body
            if body is not None
            else (
                "  k_form:\n"
                "    distribution: uniform\n"
                "    low: 0.8\n"
                "    high: 1.2\n"
                "    unit: s^-1\n"
                "    source: synthetic uncertainty range\n"
                "  k_product:\n"
                "    distribution: loguniform\n"
                "    low: 0.8\n"
                "    high: 1.2\n"
                "    unit: s^-1\n"
                "    source: synthetic uncertainty range\n"
            )
        ),
        encoding="utf-8",
    )
    return path


def _write_conditions_file(tmp_path, distributions_file_name):
    path = tmp_path / "conditions.yaml"
    path.write_text(
        "schema_version: 1\n"
        "conditions:\n"
        f"  parameter_distributions_path: {distributions_file_name}\n"
        "  observable: product_rate:P_g\n"
        "  variables: {}\n"
        "  initial_coverages:\n"
        "    A_star: 0.2\n"
        "    star: 0.8\n"
        "  time_grid: [0.0, 1.0]\n",
        encoding="utf-8",
    )
    return path


def _write_two_step_model(tmp_path):
    path = tmp_path / "two_step_model.yaml"
    path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic two-step uncertainty model\n"
        "  site_types:\n"
        "    - id: star\n"
        "      total_sites: 1.0\n"
        "      unit: fraction\n"
        "  species:\n"
        "    gas:\n"
        "      P_g:\n"
        "        phase: gas\n"
        "    surface:\n"
        "      A_star:\n"
        "        phase: surface\n"
        "        site_type: star\n"
        "  steps:\n"
        "    - id: formation\n"
        "      reversible: false\n"
        "      reactants:\n"
        "        star: 1\n"
        "      products:\n"
        "        A_star: 1\n"
        "      rate_constant_forward: k_form\n"
        "    - id: product_formation\n"
        "      reversible: false\n"
        "      reactants:\n"
        "        A_star: 1\n"
        "      products:\n"
        "        P_g: 1\n"
        "        star: 1\n"
        "      rate_constant_forward: k_product\n",
        encoding="utf-8",
    )
    return path
