"""Tests for the location entity and database table."""

import sqlite3

import pytest

from daily_task_manager.database import connect, get_migrations_path, get_runtime_root
from daily_task_manager.models import Location
from daily_task_manager.service import TaskManager


def test_location_entity() -> None:
    """Locations expose their database identity and name."""
    location = Location(location_id=1, name="Home")

    assert location.location_id == 1
    assert location.name == "Home"


def test_locations_table_has_unique_case_insensitive_names(tmp_path) -> None:
    """The migrated table stores distinct named locations."""
    database_path = tmp_path / "locations.db"
    with connect(database_path) as connection:
        location_id = connection.execute(
            "INSERT INTO locations(name) VALUES (?)", ("Home",)
        ).lastrowid

        assert location_id == 1
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO locations(name) VALUES (?)", ("home",))


def test_locations_can_be_created_and_renamed(tmp_path) -> None:
    """Location maintenance validates names and updates existing records."""
    manager = TaskManager(tmp_path / "location-maintenance.db")
    location_id = manager.save_location("Home")

    assert manager.save_location("Office", location_id) == location_id
    assert [(row["location_id"], row["name"]) for row in manager.list_locations()] == [
        (location_id, "Office")
    ]
    with pytest.raises(ValueError, match="Location name is required"):
        manager.save_location("  ")


def test_schema_has_no_active_flags(tmp_path) -> None:
    """Migrated reference and reusable tables do not expose active flags."""
    database_path = tmp_path / "no-active-flags.db"
    with connect(database_path) as connection:
        for table in (
            "task_categories",
            "task_types",
            "predefined_tasks",
            "daily_templates",
        ):
            columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            assert "active" not in columns


def test_runtime_root_controls_migration_location(tmp_path, monkeypatch: object) -> None:
    """Container deployments can resolve root-level migrations outside the wheel."""
    monkeypatch.setenv("DAILY_TASK_MANAGER_ROOT", str(tmp_path))

    assert get_runtime_root() == tmp_path
    assert get_migrations_path() == tmp_path / "migrations"
