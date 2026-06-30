from __future__ import annotations

import sqlite3

import pytest

from qchem_workbench.cli import main
from qchem_workbench.db import PROJECT_DATABASE_SCHEMA_VERSION, ProjectDatabase


def test_initialise_database_and_read_schema_version(tmp_path):
    db_path = tmp_path / "project.db"

    with ProjectDatabase.connect(db_path, create=True) as database:
        database.initialise()
        info = database.info()

    assert db_path.exists()
    assert info.schema_version == PROJECT_DATABASE_SCHEMA_VERSION
    assert info.metadata["schema_version"] == str(PROJECT_DATABASE_SCHEMA_VERSION)
    assert info.metadata["qchem_workbench_version"]
    assert info.schema_migrations[0]["version"] == PROJECT_DATABASE_SCHEMA_VERSION


def test_connect_missing_database_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        ProjectDatabase.connect(tmp_path / "missing.db")


def test_check_detects_missing_database(tmp_path):
    status = ProjectDatabase.check(tmp_path / "missing.db")

    assert status.valid is False
    assert status.exists is False
    assert status.initialised is False
    assert "does not exist" in status.problems[0]


def test_check_detects_unsupported_schema_version(tmp_path):
    db_path = tmp_path / "project.db"
    with ProjectDatabase.connect(db_path, create=True) as database:
        database.initialise()
        database.connection.execute(
            "UPDATE metadata SET value = '999' WHERE key = 'schema_version'"
        )
        database.connection.commit()

    status = ProjectDatabase.check(db_path)

    assert status.valid is False
    assert status.exists is True
    assert status.initialised is True
    assert status.schema_version == 999
    assert "unsupported database schema_version 999" in status.problems[0]


def test_check_detects_uninitialised_sqlite_database(tmp_path):
    db_path = tmp_path / "empty.db"
    sqlite3.connect(db_path).close()

    status = ProjectDatabase.check(db_path)

    assert status.valid is False
    assert status.exists is True
    assert status.initialised is False
    assert "not initialised" in status.problems[0]


def test_db_cli_init_info_and_check(tmp_path, capsys):
    db_path = tmp_path / "project.db"

    init_exit = main(["db", "init", str(db_path)])
    init_output = capsys.readouterr()
    info_exit = main(["db", "info", str(db_path)])
    info_output = capsys.readouterr()
    check_exit = main(["db", "check", str(db_path)])
    check_output = capsys.readouterr()

    assert init_exit == 0
    assert "Initialized project database" in init_output.out
    assert f"schema_version\t{PROJECT_DATABASE_SCHEMA_VERSION}" in init_output.out
    assert info_exit == 0
    assert f"schema_version\t{PROJECT_DATABASE_SCHEMA_VERSION}" in info_output.out
    assert "schema_migration_count\t1" in info_output.out
    assert check_exit == 0
    assert "valid\tTrue" in check_output.out


def test_db_cli_missing_database_fails(tmp_path, capsys):
    exit_code = main(["db", "check", str(tmp_path / "missing.db")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "exists\tFalse" in captured.out
    assert "valid\tFalse" in captured.out
    assert "does not exist" in captured.out


def test_db_cli_info_rejects_unsupported_schema(tmp_path, capsys):
    db_path = tmp_path / "project.db"
    with ProjectDatabase.connect(db_path, create=True) as database:
        database.initialise()
        database.connection.execute(
            "UPDATE metadata SET value = '999' WHERE key = 'schema_version'"
        )
        database.connection.commit()

    exit_code = main(["db", "info", str(db_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "unsupported database schema_version 999" in captured.err
