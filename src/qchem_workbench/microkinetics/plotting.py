"""Plot microkinetic CSV outputs with matplotlib."""

from __future__ import annotations

import csv
from pathlib import Path


def plot_trajectory_csv(csv_path: Path, out_path: Path) -> Path:
    rows = _read_rows(csv_path)
    if not rows or "time" not in rows[0]:
        raise ValueError("trajectory CSV must include a time column")
    species = [column for column in rows[0] if column != "time"]
    if not species:
        raise ValueError("trajectory CSV must include at least one coverage column")
    x_values = [_float(row["time"], "time") for row in rows]

    def draw(ax):
        for species_id in species:
            y_values = [_float(row[species_id], species_id) for row in rows]
            ax.plot(x_values, y_values, marker="o", label=species_id)
        ax.set_xlabel("Time")
        ax.set_ylabel("Coverage (fraction)")
        ax.legend()

    return _write_plot(out_path, draw)


def plot_steady_state_csv(csv_path: Path, out_path: Path) -> Path:
    rows = _read_rows(csv_path)
    _require_columns(rows, {"species", "coverage"}, "steady-state CSV")
    labels = [row["species"] for row in rows]
    values = [_float(row["coverage"], "coverage") for row in rows]

    def draw(ax):
        ax.bar(labels, values)
        ax.set_xlabel("Surface species/site")
        ax.set_ylabel("Steady-state coverage (fraction)")
        ax.tick_params(axis="x", rotation=30)

    return _write_plot(out_path, draw)


def plot_rates_csv(csv_path: Path, out_path: Path) -> Path:
    rows = [
        row
        for row in _read_rows(csv_path)
        if row.get("row_type") == "species" and row.get("rate", "").strip()
    ]
    if not rows:
        raise ValueError("rates CSV must contain species rows with numeric rates")
    labels = [row["id"] for row in rows]
    values = [_float(row["rate"], "rate") for row in rows]
    unit = rows[0].get("unit") or "rate"

    def draw(ax):
        ax.bar(labels, values)
        ax.set_xlabel("Species")
        ax.set_ylabel(f"Net production rate ({unit})")
        ax.tick_params(axis="x", rotation=30)

    return _write_plot(out_path, draw)


def plot_sensitivity_csv(csv_path: Path, out_path: Path) -> Path:
    rows = [
        row
        for row in _read_rows(csv_path)
        if row.get("sensitivity", "").strip()
    ]
    if not rows:
        raise ValueError("sensitivity CSV must contain numeric sensitivity rows")
    labels = [row["parameter_id"] for row in rows]
    values = [_float(row["sensitivity"], "sensitivity") for row in rows]

    def draw(ax):
        ax.bar(labels, values)
        ax.set_xlabel("Rate parameter")
        ax.set_ylabel("Finite-difference sensitivity")
        ax.tick_params(axis="x", rotation=30)

    return _write_plot(out_path, draw)


def plot_uncertainty_csv(csv_path: Path, out_path: Path) -> Path:
    rows = _read_rows(csv_path)
    _require_columns(rows, {"observable", "mean", "q05", "q95"}, "uncertainty CSV")
    row = rows[0]
    mean = _float(row["mean"], "mean")
    q05 = _float(row["q05"], "q05")
    q95 = _float(row["q95"], "q95")

    def draw(ax):
        ax.errorbar(
            [row["observable"]],
            [mean],
            yerr=[[mean - q05], [q95 - mean]],
            fmt="o",
            capsize=4,
        )
        ax.set_xlabel("Observable")
        ax.set_ylabel("Sampled value")
        ax.tick_params(axis="x", rotation=20)

    return _write_plot(out_path, draw)


def _write_plot(out_path: Path, draw) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    draw(ax)
    fig.tight_layout()
    output_path = Path(out_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with Path(csv_path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _require_columns(rows: list[dict[str, str]], columns: set[str], label: str) -> None:
    if not rows:
        raise ValueError(f"{label} is empty")
    missing = columns - set(rows[0])
    if missing:
        raise ValueError(f"{label} missing required column(s): {', '.join(sorted(missing))}")


def _float(value: str, label: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
