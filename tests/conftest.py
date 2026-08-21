"""Shared test fixtures."""

from pathlib import Path

import pytest

from daily_task_manager.service import TaskManager


@pytest.fixture
def manager(tmp_path: Path) -> TaskManager:
    """Return a service backed by an isolated migrated database.

    :param tmp_path: Pytest temporary directory.
    :return: Isolated task service.
    """
    return TaskManager(tmp_path / "tasks.db")


@pytest.fixture
def classified_manager(manager: TaskManager) -> tuple[TaskManager, int]:
    """Return a service containing one category and type.

    :param manager: Isolated task service.
    :return: Service and task type ID.
    """
    category_id = manager.save_category("Practical")
    type_id = manager.save_type("Cleaning", category_id)
    return manager, type_id
