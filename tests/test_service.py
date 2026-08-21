"""Tests for core task-management business rules."""

from datetime import date

import pytest

from daily_task_manager.models import TaskFilter, TaskStatus
from daily_task_manager.service import TaskManager


def test_ad_hoc_completion_and_reopening(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """A task derives status from its nullable end date."""
    manager, type_id = classified_manager
    task_id = manager.add_ad_hoc_task("Unload the dishwasher", type_id, date(2026, 8, 19))

    assert manager.list_tasks()[0]["status"] == "Open"
    manager.set_task_completion(task_id, date(2026, 8, 20))
    assert manager.list_tasks()[0]["status"] == "Completed"
    manager.set_task_completion(task_id, None)
    assert manager.list_tasks()[0]["status"] == "Open"


def test_task_can_be_deleted(classified_manager: tuple[TaskManager, int]) -> None:
    """A task row can be removed directly."""
    manager, type_id = classified_manager
    task_id = manager.add_ad_hoc_task("Delete me", type_id, date(2026, 8, 20))

    manager.delete_task(task_id)

    assert manager.list_tasks() == []
    with pytest.raises(ValueError, match="Task not found"):
        manager.delete_task(task_id)


def test_completion_cannot_predate_start(classified_manager: tuple[TaskManager, int]) -> None:
    """Invalid completion chronology is rejected."""
    manager, type_id = classified_manager
    task_id = manager.add_ad_hoc_task("Clean", type_id, date(2026, 8, 20))

    with pytest.raises(ValueError, match="before start"):
        manager.set_task_completion(task_id, date(2026, 8, 19))


def test_template_copies_historical_values(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Editing a definition does not alter an instantiated task."""
    manager, type_id = classified_manager
    predefined_id = manager.save_predefined_task("Clean bathroom", type_id)
    template_id = manager.save_template("Daily", predefined_task_ids=[predefined_id])

    manager.instantiate_template_tasks(
        date(2026, 8, 20),
        [row["predefined_task_id"] for row in manager.get_template_tasks(template_id)],
    )
    manager.save_predefined_task("Clean kitchen", type_id, predefined_id)

    task = manager.list_tasks()[0]
    assert task["description"] == "Clean bathroom"
    assert task["predefined_task_id"] == predefined_id


def test_template_copies_predefined_location(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """An instantiated task preserves its definition's current location."""
    manager, type_id = classified_manager
    home_id = manager.resolve_location("Home")
    office_id = manager.resolve_location("Office")
    predefined_id = manager.save_predefined_task(
        "Read", type_id, location_id=home_id
    )

    manager.instantiate_template_tasks(date(2026, 8, 20), [predefined_id])
    manager.save_predefined_task(
        "Read", type_id, predefined_id, location_id=office_id
    )

    assert manager.list_tasks()[0]["location_name"] == "Home"
    assert manager.list_predefined_tasks()[0]["location_name"] == "Office"


def test_template_instantiation_allows_duplicate_daily_tasks(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """The same template task may be added repeatedly on one date."""
    manager, type_id = classified_manager
    predefined_id = manager.save_predefined_task("Clean", type_id)
    task_date = date(2026, 8, 20)

    assert manager.instantiate_template_tasks(task_date, [predefined_id]) == 1
    assert manager.instantiate_template_tasks(task_date, [predefined_id]) == 1
    assert [row["description"] for row in manager.list_tasks()] == ["Clean", "Clean"]


def test_template_can_contain_repeated_predefined_tasks(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Repeated template memberships create repeated tasks on instantiation."""
    manager, type_id = classified_manager
    laundry_id = manager.save_predefined_task("Laundry", type_id)
    template_id = manager.save_template(
        "Laundry day", predefined_task_ids=[laundry_id, laundry_id, laundry_id]
    )

    template_tasks = manager.get_template_tasks(template_id)
    assert [row["predefined_task_id"] for row in template_tasks] == [
        laundry_id,
        laundry_id,
        laundry_id,
    ]
    assert manager.instantiate_template_tasks(
        date(2026, 8, 20), [row["predefined_task_id"] for row in template_tasks]
    ) == 3
    assert [row["description"] for row in manager.list_tasks()] == [
        "Laundry",
        "Laundry",
        "Laundry",
    ]


def test_browser_filters_use_case_insensitive_substring(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Description, date, status, type, and category filters combine correctly."""
    manager, type_id = classified_manager
    manager.add_ad_hoc_task("Unload the DISHWASHER", type_id, date(2026, 8, 20))
    other_id = manager.add_ad_hoc_task("Cook dinner", type_id, date(2026, 8, 19))
    manager.set_task_completion(other_id, date(2026, 8, 19))
    category_id = manager.list_categories()[0]["category_id"]

    rows = manager.list_tasks(
        TaskFilter(
            start_from=date(2026, 8, 20),
            start_to=date(2026, 8, 20),
            description="dish",
            status=TaskStatus.OPEN,
            type_id=type_id,
            category_id=category_id,
        )
    )

    assert [row["description"] for row in rows] == ["Unload the DISHWASHER"]


def test_tasks_are_sorted_by_start_date_then_description(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Task tables show newest dates first and descriptions alphabetically."""
    manager, type_id = classified_manager
    manager.add_ad_hoc_task("Zebra", type_id, date(2026, 8, 19))
    manager.add_ad_hoc_task("beta", type_id, date(2026, 8, 20))
    manager.add_ad_hoc_task("Alpha", type_id, date(2026, 8, 20))

    assert [row["description"] for row in manager.list_tasks()] == [
        "Alpha",
        "beta",
        "Zebra",
    ]


def test_reference_data_deletion_rejects_items_in_use(manager: TaskManager) -> None:
    """Reference data can only be deleted while unreferenced."""
    category_id = manager.save_category("Practical")
    type_id = manager.save_type("Cleaning", category_id)
    location_id = manager.save_location("Home")
    manager.add_ad_hoc_task("Clean", type_id, date(2026, 8, 20), location_id)

    with pytest.raises(ValueError, match="Category is in use"):
        manager.delete_category(category_id)
    with pytest.raises(ValueError, match="Task type is in use"):
        manager.delete_type(type_id)
    with pytest.raises(ValueError, match="Location is in use"):
        manager.delete_location(location_id)

    unused_category_id = manager.save_category("Unused")
    unused_type_id = manager.save_type("Unused", category_id)
    unused_location_id = manager.save_location("Unused")
    manager.delete_type(unused_type_id)
    manager.delete_category(unused_category_id)
    manager.delete_location(unused_location_id)

    assert [row["name"] for row in manager.list_categories()] == ["Practical"]
    assert [row["name"] for row in manager.list_types()] == ["Cleaning"]
    assert [row["name"] for row in manager.list_locations()] == ["Home"]


def test_deleting_template_removes_its_memberships(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Template deletion removes owned membership rows without deleting tasks."""
    manager, type_id = classified_manager
    predefined_id = manager.save_predefined_task("Clean", type_id)
    template_id = manager.save_template("Daily", predefined_task_ids=[predefined_id])

    manager.delete_template(template_id)

    assert manager.list_templates() == []
    assert manager.list_predefined_tasks()[0]["predefined_task_id"] == predefined_id


def test_duplicate_template_copies_memberships_and_numbers_names(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Template copies retain ordered tasks and receive unique copy suffixes."""
    manager, type_id = classified_manager
    first_id = manager.save_predefined_task("First", type_id)
    second_id = manager.save_predefined_task("Second", type_id)
    template_id = manager.save_template(
        "Daily", "Routine", [second_id, first_id]
    )

    first_copy_id = manager.duplicate_template(template_id)
    second_copy_id = manager.duplicate_template(template_id)

    templates = {row["template_id"]: row for row in manager.list_templates()}
    assert templates[first_copy_id]["name"] == "Daily - Copy"
    assert templates[second_copy_id]["name"] == "Daily - Copy 2"
    assert templates[first_copy_id]["description"] == "Routine"
    assert [
        row["predefined_task_id"] for row in manager.get_template_tasks(first_copy_id)
    ] == [second_id, first_id]


def test_predefined_task_deletion_rejects_items_in_use(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Reusable tasks can only be deleted while unreferenced."""
    manager, type_id = classified_manager
    template_task_id = manager.save_predefined_task("Templated", type_id)
    historical_task_id = manager.save_predefined_task("Historical", type_id)
    unused_task_id = manager.save_predefined_task("Unused", type_id)
    manager.save_template("Daily", predefined_task_ids=[template_task_id])
    manager.instantiate_template_tasks(date(2026, 8, 20), [historical_task_id])

    with pytest.raises(ValueError, match="Pre-defined task is in use"):
        manager.delete_predefined_task(template_task_id)
    with pytest.raises(ValueError, match="Pre-defined task is in use"):
        manager.delete_predefined_task(historical_task_id)

    manager.delete_predefined_task(unused_task_id)
    assert {row["description"] for row in manager.list_predefined_tasks()} == {
        "Historical",
        "Templated",
    }
