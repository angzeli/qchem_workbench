"""Generic pathway plotting utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PathwayPlotData:
    labels: tuple[str, ...]
    relative_energies: tuple[float, ...]
    unit: str
    omitted_rows: int = 0


def plot_pathway_from_csv(
    csv_path: Path,
    out_path: Path,
    *,
    title: str | None = None,
) -> Path:
    """Plot a generic cumulative pathway from a reaction-energy CSV."""

    rows = _read_csv_rows(csv_path)
    data = pathway_plot_data(rows)
    _write_pathway_plot(data, out_path, title=title)
    return out_path


def pathway_plot_data(rows: Iterable[dict[str, str]]) -> PathwayPlotData:
    """Build cumulative pathway data from reaction-energy table rows."""

    row_list = list(rows)
    energy_column, unit = _select_energy_column(row_list)
    labels = ["Start"]
    energies = [0.0]
    current = 0.0
    omitted_rows = 0

    for index, row in enumerate(row_list, start=1):
        value = _float_or_none(row.get(energy_column, ""))
        if value is None:
            omitted_rows += 1
            continue
        current += value
        labels.append(_row_label(row, index))
        energies.append(current)

    return PathwayPlotData(
        labels=tuple(labels),
        relative_energies=tuple(energies),
        unit=unit,
        omitted_rows=omitted_rows,
    )


def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with Path(csv_path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_pathway_plot(
    data: PathwayPlotData,
    out_path: Path,
    *,
    title: str | None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    x_values = list(range(len(data.labels)))

    if len(data.relative_energies) > 1:
        ax.plot(x_values, data.relative_energies, marker="o")
    else:
        ax.text(
            0.5,
            0.5,
            "No complete reaction energy rows",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    if data.omitted_rows:
        ax.text(
            0.02,
            0.98,
            f"{data.omitted_rows} incomplete row(s) omitted",
            ha="left",
            va="top",
            transform=ax.transAxes,
            fontsize="small",
        )

    ax.set_xlabel("Reaction step")
    ax.set_ylabel(f"Relative energy ({data.unit})")
    if title:
        ax.set_title(title)
    ax.set_xticks(x_values)
    ax.set_xticklabels(data.labels, rotation=30, ha="right")
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def _select_energy_column(rows: list[dict[str, str]]) -> tuple[str, str]:
    candidates = [
        ("delta_ev", "eV"),
        ("Delta (eV)", "eV"),
        ("delta_kj_mol", "kJ/mol"),
        ("Delta (kJ/mol)", "kJ/mol"),
    ]
    for column, unit in candidates:
        if any(_float_or_none(row.get(column, "")) is not None for row in rows):
            return column, unit
    return "delta_ev", "eV"


def _row_label(row: dict[str, str], index: int) -> str:
    for key in ("label", "Label", "reaction_id", "Reaction ID"):
        value = row.get(key, "").strip()
        if value:
            return value
    return f"Step {index}"


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None
