"""Database path, connection, and migration management."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from yoyo import get_backend, read_migrations

DATABASE_ENVIRONMENT_VARIABLE = "DAILY_TASK_MANAGER_DB"
ROOT_ENVIRONMENT_VARIABLE = "DAILY_TASK_MANAGER_ROOT"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_runtime_root() -> Path:
    """Return the configured runtime root or source-project root.

    :return: Directory containing migrations and application data.
    """
    configured_path = os.getenv(ROOT_ENVIRONMENT_VARIABLE)
    return Path(configured_path).expanduser() if configured_path else PROJECT_ROOT


def get_database_path() -> Path:
    """Return the configured database path.

    :return: Path from the environment, or the project-local default.
    """
    configured_path = os.getenv(DATABASE_ENVIRONMENT_VARIABLE)
    return (
        Path(configured_path).expanduser()
        if configured_path
        else get_runtime_root() / "data" / "taskmanager.db"
    )


def get_migrations_path() -> Path:
    """Return the runtime migration directory.

    :return: Migrations below the configured runtime root.
    """
    return get_runtime_root() / "migrations"


def migrate_database(database_path: Path | None = None) -> Path:
    """Create the database directory and apply pending yoyo migrations.

    :param database_path: Optional database path override.
    :return: The migrated database path.
    """
    path = database_path or get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    backend = get_backend(f"sqlite:///{path}")
    migrations_path = get_migrations_path()
    if not migrations_path.is_dir():
        raise FileNotFoundError(f"Migration directory not found: {migrations_path}")
    migrations = read_migrations(str(migrations_path))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
    return path


@contextmanager
def connect(database_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a foreign-key-enabled SQLite connection and manage its transaction.

    :param database_path: Optional database path override.
    :return: Context manager yielding a SQLite connection.
    """
    path = migrate_database(database_path)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
