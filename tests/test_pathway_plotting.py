from __future__ import annotations

from qchem_workbench.reports.plotting import pathway_plot_data, plot_pathway_from_csv


def test_pathway_plot_data_uses_ev_and_omits_missing_rows():
    rows = [
        {"reaction_id": "r1", "label": "A to B", "delta_ev": "0.5"},
        {"reaction_id": "r2", "label": "B to C", "delta_ev": ""},
        {"reaction_id": "r3", "label": "C to D", "delta_ev": "1.25"},
    ]

    data = pathway_plot_data(rows)

    assert data.unit == "eV"
    assert data.labels == ("Start", "A to B", "C to D")
    assert data.relative_energies == (0.0, 0.5, 1.75)
    assert data.omitted_rows == 1


def test_pathway_plot_data_falls_back_to_kj_mol():
    rows = [{"reaction_id": "r1", "delta_ev": "", "delta_kj_mol": "12.5"}]

    data = pathway_plot_data(rows)

    assert data.unit == "kJ/mol"
    assert data.relative_energies == (0.0, 12.5)


def test_plot_pathway_creates_png_from_fixture_csv(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "mpl"))
    csv_path = tmp_path / "reaction_table.csv"
    csv_path.write_text(
        "reaction_id,label,quantity,complete,delta_hartree,delta_ev,delta_kj_mol,"
        "missing_species,notes\n"
        "r1,A to B,delta_e_electronic,True,0.1,2.7,262.5,,synthetic fixture\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "pathway.png"

    plot_pathway_from_csv(csv_path, out_path)

    assert out_path.read_bytes().startswith(b"\x89PNG")


def test_plot_pathway_handles_missing_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "mpl"))
    csv_path = tmp_path / "reaction_table.csv"
    csv_path.write_text(
        "reaction_id,label,quantity,complete,delta_hartree,delta_ev,delta_kj_mol,"
        "missing_species,notes\n"
        "r1,A to B,delta_e_electronic,False,,,,B,missing data\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "pathway.png"

    plot_pathway_from_csv(csv_path, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 0
