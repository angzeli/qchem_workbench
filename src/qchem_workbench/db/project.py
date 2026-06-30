"""SQLite project database skeleton."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qchem_workbench import __version__


PROJECT_DATABASE_SCHEMA_VERSION = 1


class ProjectDatabaseError(RuntimeError):
    """Base error for project database operations."""


class ProjectDatabaseSchemaError(ProjectDatabaseError, ValueError):
    """Raised when a database is missing or has an unsupported schema."""


@dataclass(frozen=True)
class ProjectDatabaseStatus:
    path: Path
    exists: bool
    initialised: bool
    schema_version: int | None
    supported: bool
    problems: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return self.exists and self.initialised and self.supported and not self.problems

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "exists": self.exists,
            "initialised": self.initialised,
            "schema_version": self.schema_version,
            "supported": self.supported,
            "valid": self.valid,
            "problems": list(self.problems),
        }


@dataclass(frozen=True)
class ProjectDatabaseInfo:
    path: Path
    schema_version: int
    metadata: dict[str, str]
    project_info: dict[str, str]
    schema_migrations: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "schema_version": self.schema_version,
            "metadata": dict(self.metadata),
            "project_info": dict(self.project_info),
            "schema_migrations": list(self.schema_migrations),
        }


class ProjectDatabase:
    """Small wrapper around a local qchem-workbench SQLite database."""

    def __init__(self, path: Path, connection: sqlite3.Connection) -> None:
        self.path = Path(path)
        self.connection = connection

    @classmethod
    def connect(cls, path: Path, *, create: bool = False) -> ProjectDatabase:
        database_path = Path(path)
        if not create and not database_path.exists():
            raise FileNotFoundError(f"project database does not exist: {database_path}")
        if create:
            database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return cls(database_path, connection)

    @classmethod
    def check(cls, path: Path) -> ProjectDatabaseStatus:
        database_path = Path(path)
        if not database_path.exists():
            return ProjectDatabaseStatus(
                path=database_path,
                exists=False,
                initialised=False,
                schema_version=None,
                supported=False,
                problems=(f"project database does not exist: {database_path}",),
            )

        try:
            with cls.connect(database_path) as database:
                schema_version = database.schema_version()
        except (OSError, sqlite3.Error, ProjectDatabaseSchemaError) as exc:
            return ProjectDatabaseStatus(
                path=database_path,
                exists=True,
                initialised=False,
                schema_version=None,
                supported=False,
                problems=(str(exc),),
            )

        problems: list[str] = []
        supported = schema_version == PROJECT_DATABASE_SCHEMA_VERSION
        if not supported:
            problems.append(
                f"unsupported database schema_version {schema_version}; "
                f"expected {PROJECT_DATABASE_SCHEMA_VERSION}"
            )
        return ProjectDatabaseStatus(
            path=database_path,
            exists=True,
            initialised=True,
            schema_version=schema_version,
            supported=supported,
            problems=tuple(problems),
        )

    def initialise(self) -> None:
        now = _utc_timestamp()
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS project_info (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self._set_metadata("schema_version", str(PROJECT_DATABASE_SCHEMA_VERSION), now)
        self._set_metadata("qchem_workbench_version", __version__, now)
        self.connection.execute(
            """
            INSERT OR IGNORE INTO schema_migrations
                (version, applied_at, description)
            VALUES (?, ?, ?)
            """,
            (
                PROJECT_DATABASE_SCHEMA_VERSION,
                now,
                "Initial project database metadata schema.",
            ),
        )
        self.connection.commit()

    def schema_version(self) -> int:
        try:
            row = self.connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
        except sqlite3.Error as exc:
            raise ProjectDatabaseSchemaError(
                f"{self.path}: database is not initialised"
            ) from exc
        if row is None:
            raise ProjectDatabaseSchemaError(
                f"{self.path}: database is missing metadata.schema_version"
            )
        try:
            return int(row["value"])
        except (TypeError, ValueError) as exc:
            raise ProjectDatabaseSchemaError(
                f"{self.path}: invalid metadata.schema_version {row['value']!r}"
            ) from exc

    def ensure_supported_schema(self) -> None:
        schema_version = self.schema_version()
        if schema_version != PROJECT_DATABASE_SCHEMA_VERSION:
            raise ProjectDatabaseSchemaError(
                f"{self.path}: unsupported database schema_version {schema_version}; "
                f"expected {PROJECT_DATABASE_SCHEMA_VERSION}"
            )

    def info(self) -> ProjectDatabaseInfo:
        self.ensure_supported_schema()
        return ProjectDatabaseInfo(
            path=self.path,
            schema_version=self.schema_version(),
            metadata=_key_value_rows(self.connection, "metadata"),
            project_info=_key_value_rows(self.connection, "project_info"),
            schema_migrations=_migration_rows(self.connection),
        )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> ProjectDatabase:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _set_metadata(self, key: str, value: str, updated_at: str) -> None:
        self.connection.execute(
            """
            INSERT INTO metadata (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, updated_at),
        )


def _key_value_rows(connection: sqlite3.Connection, table: str) -> dict[str, str]:
    rows = connection.execute(f"SELECT key, value FROM {table} ORDER BY key").fetchall()
    return {str(row["key"]): str(row["value"]) for row in rows}


def _migration_rows(connection: sqlite3.Connection) -> tuple[dict[str, Any], ...]:
    rows = connection.execute(
        """
        SELECT version, applied_at, description
        FROM schema_migrations
        ORDER BY version
        """
    ).fetchall()
    return tuple(
        {
            "version": int(row["version"]),
            "applied_at": str(row["applied_at"]),
            "description": str(row["description"]),
        }
        for row in rows
    )


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
