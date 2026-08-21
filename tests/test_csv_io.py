"""Tests for validated CSV import and compatible export."""

import csv
import io
from datetime import date

from daily_task_manager.csv_io import (
    export_categories,
    export_locations,
    export_predefined_tasks,
    export_tasks,
    export_templates,
    export_types,
    import_categories,
    import_historical_tasks,
    import_locations,
    import_predefined_tasks,
    import_templates,
    import_types,
)
from daily_task_manager.service import TaskManager


def test_historical_import_reports_bad_rows_and_converts_dates(manager: TaskManager) -> None:
    """Valid legacy rows import while malformed rows are clearly reported."""
    content = (
        b"Start,End,Description,Type,Category\n"
        b"19/08/26,20/08/26,Clean bathroom,Cleaning,Practical\n"
        b"not-a-date,,Bad task,Cleaning,Practical\n"
        b"20/08/26,19/08/26,Time travel,Cleaning,Practical\n"
    )

    result = import_historical_tasks(content, manager)

    assert result.imported == 1
    assert [issue.row_number for issue in result.issues] == [3, 4]
    task = manager.list_tasks()[0]
    assert task["start_date"] == "2026-08-19"
    assert task["end_date"] == "2026-08-20"


def test_predefined_import_reuses_hierarchy_and_avoids_duplicates(manager: TaskManager) -> None:
    """Repeated library rows do not duplicate categories, types, or tasks."""
    content = (
        b"Description,Type,Category\n"
        b"Clean bathroom,Cleaning,Practical\n"
        b"Clean bathroom,Cleaning,Practical\n"
        b"Cook dinner,Cooking,Practical\n"
    )

    result = import_predefined_tasks(content, manager)

    assert result.imported == 2
    assert len(manager.list_categories()) == 1
    assert len(manager.list_types()) == 2
    assert len(manager.list_predefined_tasks()) == 2


def test_imports_create_and_associate_optional_locations(manager: TaskManager) -> None:
    """Both CSV formats resolve locations without requiring a value."""
    historical = (
        b"Start,End,Description,Location,Type,Category\n"
        b"19/08/26,,Clean bathroom,Home,Cleaning,Practical\n"
        b"19/08/26,,Go for a walk,,Exercise,Wellbeing\n"
    )
    predefined = (
        b"Description,Location,Type,Category\n"
        b"Clean kitchen,home,Cleaning,Practical\n"
    )

    assert import_historical_tasks(historical, manager).imported == 2
    assert import_predefined_tasks(predefined, manager).imported == 1

    assert [row["name"] for row in manager.list_locations()] == ["Home"]
    tasks = {row["description"]: row for row in manager.list_tasks()}
    assert tasks["Clean bathroom"]["location_name"] == "Home"
    assert tasks["Go for a walk"]["location_name"] is None
    assert manager.list_predefined_tasks()[0]["location_name"] == "Home"


def test_template_import_resolves_records_and_avoids_duplicate_memberships(
    manager: TaskManager,
) -> None:
    """Template rows create missing records and append each task only once."""
    content = (
        b"Template,Description,Location,Type,Category\n"
        b"Morning,Clean kitchen,Home,Cleaning,Practical\n"
        b"Morning,Clean kitchen,Home,Cleaning,Practical\n"
        b"Morning,Make breakfast,Home,Cooking,Practical\n"
        b"Evening,Clean kitchen,Home,Cleaning,Practical\n"
    )

    result = import_templates(content, manager)

    assert result.imported == 3
    assert result.issues == ()
    assert [row["name"] for row in manager.list_locations()] == ["Home"]
    assert len(manager.list_predefined_tasks()) == 2
    templates = {row["name"]: row for row in manager.list_templates()}
    assert set(templates) == {"Evening", "Morning"}
    morning_tasks = manager.get_template_tasks(templates["Morning"]["template_id"])
    assert [row["description"] for row in morning_tasks] == [
        "Clean kitchen",
        "Make breakfast",
    ]


def test_reference_data_imports_create_only_missing_records(manager: TaskManager) -> None:
    """Category, type, and location imports are idempotent and validate blank rows."""
    category_result = import_categories(
        b"Category\nPractical\npractical\nWellbeing\n   \n", manager
    )
    type_result = import_types(
        b"Type,Category\nCleaning,Practical\ncleaning,practical\nExercise,Wellbeing\n",
        manager,
    )
    location_result = import_locations(b"Location\nHome\nhome\nOffice\n", manager)

    assert category_result.imported == 2
    assert [issue.row_number for issue in category_result.issues] == [5]
    assert type_result.imported == 2
    assert type_result.issues == ()
    assert location_result.imported == 2
    assert location_result.issues == ()
    assert [row["name"] for row in manager.list_categories()] == [
        "Practical",
        "Wellbeing",
    ]
    assert [row["name"] for row in manager.list_types()] == ["Cleaning", "Exercise"]
    assert [row["name"] for row in manager.list_locations()] == ["Home", "Office"]


def test_historical_export_has_import_compatible_headings(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Historical export uses human-readable import-compatible columns."""
    manager, type_id = classified_manager
    manager.add_ad_hoc_task("Open task", type_id, date(2026, 8, 20))
    location_id = manager.resolve_location("Home")
    completed_id = manager.add_ad_hoc_task(
        "Completed task", type_id, date(2026, 8, 19), location_id
    )
    manager.set_task_completion(completed_id, date(2026, 8, 20))

    exported = export_tasks(manager).decode()
    rows = list(csv.DictReader(io.StringIO(exported)))

    assert tuple(rows[0]) == (
        "Start",
        "End",
        "Description",
        "Location",
        "Type",
        "Category",
    )
    assert rows == [
        {
            "Start": "20/08/26",
            "End": "",
            "Description": "Open task",
            "Location": "",
            "Type": "Cleaning",
            "Category": "Practical",
        },
        {
            "Start": "19/08/26",
            "End": "20/08/26",
            "Description": "Completed task",
            "Location": "Home",
            "Type": "Cleaning",
            "Category": "Practical",
        },
    ]


def test_historical_export_can_filter_inclusively_by_start_date(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Both date boundaries are included when historical exports are filtered."""
    manager, type_id = classified_manager
    manager.add_ad_hoc_task("Before", type_id, date(2025, 12, 31))
    manager.add_ad_hoc_task("First", type_id, date(2026, 1, 1))
    manager.add_ad_hoc_task("Last", type_id, date(2026, 8, 21))
    manager.add_ad_hoc_task("After", type_id, date(2026, 8, 22))

    exported = export_tasks(manager, date(2026, 1, 1), date(2026, 8, 21)).decode()
    rows = list(csv.DictReader(io.StringIO(exported)))

    assert [row["Description"] for row in rows] == ["Last", "First"]


def test_all_reference_and_template_exports_use_import_formats(
    classified_manager: tuple[TaskManager, int],
) -> None:
    """Every non-historical export contains its canonical import columns."""
    manager, type_id = classified_manager
    location_id = manager.resolve_location("Home")
    predefined_id = manager.save_predefined_task(
        "Clean bathroom", type_id, location_id=location_id
    )
    manager.save_template("Morning", predefined_task_ids=[predefined_id])

    predefined_rows = list(
        csv.DictReader(io.StringIO(export_predefined_tasks(manager).decode()))
    )
    template_rows = list(csv.DictReader(io.StringIO(export_templates(manager).decode())))
    category_rows = list(csv.DictReader(io.StringIO(export_categories(manager).decode())))
    type_rows = list(csv.DictReader(io.StringIO(export_types(manager).decode())))
    location_rows = list(csv.DictReader(io.StringIO(export_locations(manager).decode())))

    assert predefined_rows == [
        {
            "Description": "Clean bathroom",
            "Location": "Home",
            "Type": "Cleaning",
            "Category": "Practical",
        }
    ]
    assert template_rows == [{"Template": "Morning", **predefined_rows[0]}]
    assert category_rows == [{"Category": "Practical"}]
    assert type_rows == [{"Type": "Cleaning", "Category": "Practical"}]
    assert location_rows == [{"Location": "Home"}]
