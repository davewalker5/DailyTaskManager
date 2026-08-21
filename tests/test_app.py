"""Smoke tests for the Streamlit application shell."""

from datetime import date, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

from daily_task_manager.service import TaskManager


def test_main_navigation_is_below_versioned_title(tmp_path: Path, monkeypatch: object) -> None:
    """The main page contains the title and horizontal navigation without a sidebar.

    :param tmp_path: Pytest temporary directory.
    :param monkeypatch: Pytest environment-patching fixture.
    """
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAILY_TASK_MANAGER_DB", str(database_path))
    manager = TaskManager(database_path)
    category_id = manager.save_category("Practical")
    type_id = manager.save_type("Cleaning", category_id)
    manager.add_ad_hoc_task("Clean", type_id, date.today())
    app_path = Path(__file__).resolve().parents[1] / "src" / "streamlit_app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "📋 Daily Task Manager v1.0.0"
    assert app.radio[0].options == list(
        (
            "Today",
            "Browse Tasks",
            "Task Library",
            "Templates",
            "Reference Data",
            "Import",
            "Export",
        )
    )
    assert not app.sidebar.title
    assert app.header[0].value == "Today"

    app.radio[0].set_value("Browse Tasks").run(timeout=10)

    assert not app.exception
    assert app.header[0].value == "Browse Tasks"
    assert [field.label for field in app.date_input] == ["From", "To"]
    assert [field.value for field in app.date_input] == [
        date.today() - timedelta(days=7),
        date.today(),
    ]
    assert "Filter by start date" not in [checkbox.label for checkbox in app.checkbox]

    app.radio[0].set_value("Reference Data").run(timeout=10)

    assert not app.exception
    assert app.header[0].value == "Reference Data"
    assert [tab.label for tab in app.tabs] == ["Categories", "Task Types", "Locations"]
    assert [selectbox.label for selectbox in app.selectbox] == ["Category"]

    app.radio[0].set_value("Templates").run(timeout=10)

    assert not app.exception
    assert app.header[0].value == "Templates"

    app.radio[0].set_value("Import").run(timeout=10)

    assert not app.exception
    assert app.header[0].value == "Import"
    assert app.selectbox[0].label == "Import type"
    assert app.selectbox[0].options == [
        "Historical Tasks",
        "Pre-Defined Tasks",
        "Templates",
        "Categories",
        "Task Types",
        "Locations",
    ]
    assert not app.tabs

    app.radio[0].set_value("Export").run(timeout=10)

    assert not app.exception
    assert app.header[0].value == "Export"
    assert app.selectbox[0].label == "Export type"
    assert app.checkbox[0].label == "Filter by date"
    assert not app.checkbox[0].disabled
    assert [field.label for field in app.date_input] == ["Start date", "End date"]
    assert [field.value for field in app.date_input] == [
        date(date.today().year, 1, 1),
        date.today(),
    ]
    assert all(field.disabled for field in app.date_input)
    assert app.text_input[0].value == "historical-tasks"

    app.checkbox[0].check().run(timeout=10)

    assert not any(field.disabled for field in app.date_input)

    app.text_input[0].set_value("my-custom-name").run(timeout=10)
    app.selectbox[0].set_value("Task Types").run(timeout=10)

    assert not app.exception
    assert app.checkbox[0].disabled
    assert all(field.disabled for field in app.date_input)
    assert app.text_input[0].value == "task-types"
