"""Streamlit user interface for the Daily Task Manager."""

import sqlite3
from collections import Counter
from collections.abc import Callable
from datetime import date, timedelta
from importlib.metadata import version

import streamlit as st

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
from daily_task_manager.models import TaskFilter, TaskStatus
from daily_task_manager.service import TaskManager

PAGES = (
    "Today",
    "Browse Tasks",
    "Task Library",
    "Templates",
    "Reference Data",
    "Import",
    "Export",
)


def _row_dicts(rows: list[sqlite3.Row], columns: dict[str, str]) -> list[dict[str, object]]:
    """Convert database rows into display-friendly dictionaries.

    :param rows: SQLite result rows.
    :param columns: Mapping of source keys to displayed headings.
    :return: Dictionaries suitable for a Streamlit dataframe.
    """
    return [{heading: row[key] for key, heading in columns.items()} for row in rows]


def _show_error(error: Exception) -> None:
    """Display a concise user-facing database or validation error.

    :param error: Caught operation error.
    """
    message = str(error)
    if isinstance(error, sqlite3.IntegrityError) and "UNIQUE" in message:
        message = "A record with that name or classification already exists."
    st.error(message)


def _type_options(manager: TaskManager) -> tuple[list[int], dict[int, str]]:
    """Build task-type select options.

    :param manager: Application service.
    :return: IDs and human-readable labels.
    """
    rows = manager.list_types()
    return [row["type_id"] for row in rows], {
        row["type_id"]: f"{row['category_name']} → {row['name']}" for row in rows
    }


def _location_options(manager: TaskManager) -> tuple[list[int], dict[int, str]]:
    """Build optional location select options.

    :param manager: Application service.
    :return: IDs and human-readable labels, including no location.
    """
    rows = manager.list_locations()
    return [0, *[row["location_id"] for row in rows]], {
        0: "No location",
        **{row["location_id"]: row["name"] for row in rows},
    }


def _task_action_table(manager: TaskManager, rows: list[sqlite3.Row], key_prefix: str) -> None:
    """Render tasks with status-aware Close, Reopen, and Delete actions.

    :param manager: Application service.
    :param rows: Tasks that may be changed.
    :param key_prefix: Widget key namespace.
    """
    action_error_key = f"{key_prefix}_task_action_error"
    pending_close_key = f"{key_prefix}_pending_close_id"
    pending_delete_key = f"{key_prefix}_pending_delete_id"
    action_error = st.session_state.pop(action_error_key, None)
    if action_error:
        st.error(action_error)
    if not rows:
        st.info("No tasks match this view.")
        return

    def run_task_action(action: str, click_key: str) -> None:
        """Apply an action to the row reported by a button column."""
        click = st.session_state.get(click_key)
        if click is None:
            return
        task = rows[click["row"]]
        try:
            if action == "close":
                if task["end_date"] is None:
                    st.session_state[pending_close_key] = task["task_id"]
                    st.session_state.pop(pending_delete_key, None)
                    close_generation_key = f"{key_prefix}_close_dialog_generation"
                    st.session_state[close_generation_key] = (
                        st.session_state.get(close_generation_key, 0) + 1
                    )
            elif action == "reopen":
                if task["end_date"] is not None:
                    manager.set_task_completion(task["task_id"], None)
            else:
                st.session_state[pending_delete_key] = task["task_id"]
                st.session_state.pop(pending_close_key, None)
        except ValueError as error:
            st.session_state[action_error_key] = str(error)

    table_rows = _row_dicts(
        rows,
        {
            "status": "Status",
            "start_date": "Start Date",
            "end_date": "End Date",
            "description": "Description",
            "location_name": "Location",
            "type_name": "Type",
            "category_name": "Category",
        },
    )
    for row in table_rows:
        row.update(
            {
                "Close": ":material/check_circle:" if row["End Date"] is None else None,
                "Reopen": ":material/undo:" if row["End Date"] is not None else None,
                "Delete": ":material/delete:",
            }
        )
    column_config: dict[str, object] = {}
    for action, label in (("close", "Close"), ("reopen", "Reopen"), ("delete", "Delete")):
        click_key = f"{key_prefix}_{action}_click"
        column_config[label] = st.column_config.ButtonColumn(
            label,
            type="tertiary",
            key=click_key,
            on_click=lambda selected_action=action, key=click_key: run_task_action(
                selected_action, key
            ),
        )
    st.dataframe(table_rows, hide_index=True, width="stretch", column_config=column_config)
    pending_close_id = st.session_state.get(pending_close_key)
    if pending_close_id is not None:
        pending_task = next((row for row in rows if row["task_id"] == pending_close_id), None)
        if pending_task is None:
            st.session_state.pop(pending_close_key, None)
        else:
            close_generation = st.session_state.get(
                f"{key_prefix}_close_dialog_generation", 0
            )

            @st.dialog("Close task?", dismissible=False)
            def confirm_task_close() -> None:
                """Choose and confirm the selected task's close date."""
                st.write(f"Close **{pending_task['description']}**?")
                close_date = st.date_input(
                    "Close date",
                    value=date.today(),
                    key=f"{key_prefix}_close_date_{close_generation}",
                )
                close_column, cancel_column = st.columns(2)
                if close_column.button(
                    "Close",
                    type="primary",
                    use_container_width=True,
                    key=f"{key_prefix}_confirm_close_{close_generation}",
                ):
                    try:
                        manager.set_task_completion(pending_close_id, close_date)
                    except ValueError as error:
                        st.session_state[action_error_key] = str(error)
                    st.session_state.pop(pending_close_key, None)
                    st.rerun()
                if cancel_column.button(
                    "Cancel",
                    use_container_width=True,
                    key=f"{key_prefix}_cancel_close_{close_generation}",
                ):
                    st.session_state.pop(pending_close_key, None)
                    st.rerun()

            confirm_task_close()
            return
    pending_delete_id = st.session_state.get(pending_delete_key)
    if pending_delete_id is None:
        return
    pending_task = next((row for row in rows if row["task_id"] == pending_delete_id), None)
    if pending_task is None:
        st.session_state.pop(pending_delete_key, None)
        return

    @st.dialog("Delete task?", dismissible=False)
    def confirm_task_deletion() -> None:
        """Confirm or cancel deletion of the selected task row."""
        st.write(f"Delete **{pending_task['description']}**? This cannot be undone.")
        delete_column, cancel_column = st.columns(2)
        if delete_column.button(
            "Delete", type="primary", use_container_width=True, key=f"{key_prefix}_confirm_delete"
        ):
            try:
                manager.delete_task(pending_delete_id)
            except ValueError as error:
                st.session_state[action_error_key] = str(error)
            st.session_state.pop(pending_delete_key, None)
            st.rerun()
        if cancel_column.button(
            "Cancel", use_container_width=True, key=f"{key_prefix}_cancel_delete"
        ):
            st.session_state.pop(pending_delete_key, None)
            st.rerun()

    confirm_task_deletion()


def _add_task_form(manager: TaskManager, selected_date: date, key_prefix: str) -> None:
    """Render an ad-hoc task form.

    :param manager: Application service.
    :param selected_date: Default task date.
    :param key_prefix: Widget key namespace.
    """
    type_ids, labels = _type_options(manager)
    if not type_ids:
        st.info("Add a category and task type before creating tasks.")
        return
    with st.form(f"{key_prefix}_adhoc", clear_on_submit=True):
        description = st.text_input("Description")
        location_ids, location_labels = _location_options(manager)
        location_id = st.selectbox(
            "Location", location_ids, format_func=location_labels.get
        ) or None
        type_id = st.selectbox("Task type", type_ids, format_func=labels.get)
        start_date = st.date_input("Start date", selected_date)
        submitted = st.form_submit_button("Add task", type="primary")
    if submitted:
        try:
            manager.add_ad_hoc_task(description, type_id, start_date, location_id)
            st.success("Task added.")
            st.rerun()
        except (ValueError, sqlite3.IntegrityError) as error:
            _show_error(error)


def _template_picker(manager: TaskManager, default_date: date, key_prefix: str) -> None:
    """Render template selection and task instantiation controls.

    :param manager: Application service.
    :param default_date: Initial date for new tasks.
    :param key_prefix: Widget key namespace.
    """
    templates = manager.list_templates()
    if not templates:
        st.info("Create a template before adding tasks from one.")
        return
    names = {row["template_id"]: row["name"] for row in templates}
    selected_date = st.date_input("Task date", default_date, key=f"{key_prefix}_date")
    template_id = st.selectbox(
        "Template", list(names), format_func=names.get, key=f"{key_prefix}_template"
    )
    tasks = manager.get_template_tasks(template_id)
    if not tasks:
        st.info("This template has no tasks.")
        return
    if st.button("Add template tasks", key=f"{key_prefix}_add", type="primary"):
        try:
            count = manager.instantiate_template_tasks(
                selected_date, [row["predefined_task_id"] for row in tasks]
            )
            st.session_state[f"{key_prefix}_added_count"] = count
            st.rerun()
        except ValueError as error:
            _show_error(error)


def _library_task_picker(manager: TaskManager, default_date: date, key_prefix: str) -> None:
    """Render controls for adding one task from the reusable-task library.

    :param manager: Application service.
    :param default_date: Initial date for the new task.
    :param key_prefix: Widget key namespace.
    """
    tasks = manager.list_predefined_tasks()
    if not tasks:
        st.info("Add a pre-defined task to the Task Library first.")
        return
    task_labels = {
        row["predefined_task_id"]: (
            f"{row['description']} — {row['category_name']} / {row['type_name']}"
        )
        for row in tasks
    }
    selected_date = st.date_input("Task date", default_date, key=f"{key_prefix}_date")
    predefined_task_id = st.selectbox(
        "Pre-defined task",
        list(task_labels),
        format_func=task_labels.get,
        key=f"{key_prefix}_task",
    )
    if st.button("Add task", key=f"{key_prefix}_add", type="primary"):
        try:
            count = manager.instantiate_template_tasks(selected_date, [predefined_task_id])
            st.session_state[f"{key_prefix}_added_count"] = count
            st.rerun()
        except ValueError as error:
            _show_error(error)


def show_today(manager: TaskManager) -> None:
    """Render today's workflow.

    :param manager: Application service.
    """
    st.header("Today")
    added_count = st.session_state.pop("today_template_added_count", None)
    if added_count is not None:
        st.success(f"Added {added_count} task{'s' if added_count != 1 else ''}.")
    library_added_count = st.session_state.pop("today_library_added_count", None)
    if library_added_count is not None:
        st.success(
            f"Added {library_added_count} task{'s' if library_added_count != 1 else ''}."
        )
    today = date.today()
    rows = manager.list_tasks(
        TaskFilter(
            start_from=today,
            start_to=today,
            include_open_outside_date_range=True,
        )
    )
    _task_action_table(manager, rows, "today")
    with st.expander("Add an ad-hoc task", expanded=not rows):
        _add_task_form(manager, today, "today")
    with st.expander("Add tasks from a template"):
        _template_picker(manager, today, "today_template")
    with st.expander("Add task from library"):
        _library_task_picker(manager, today, "today_library")


def _browser_filters(manager: TaskManager) -> TaskFilter:
    """Render task-browser filters and return their values.

    :param manager: Application service.
    :return: Selected filters.
    """
    with st.expander("Filters", expanded=True):
        column_one, column_two = st.columns(2)
        today = date.today()
        start_from = column_one.date_input("From", today - timedelta(days=7))
        start_to = column_two.date_input("To", today)
        description = st.text_input("Description contains")
        status_label = st.selectbox("Status", ("All", "Open", "Completed"))
        status = TaskStatus(status_label) if status_label != "All" else None
        types = manager.list_types()
        type_labels = {0: "All", **{row["type_id"]: row["name"] for row in types}}
        type_id = st.selectbox("Task type", list(type_labels), format_func=type_labels.get) or None
        categories = manager.list_categories()
        category_labels = {0: "All", **{row["category_id"]: row["name"] for row in categories}}
        category_id = (
            st.selectbox("Category", list(category_labels), format_func=category_labels.get) or None
        )
    return TaskFilter(start_from, start_to, description, status, type_id, category_id)


def show_browser(manager: TaskManager) -> None:
    """Render searchable history with row-level task actions.

    :param manager: Application service.
    """
    st.header("Browse Tasks")
    filters = _browser_filters(manager)
    rows = manager.list_tasks(filters)
    st.caption(f"{len(rows)} task{'s' if len(rows) != 1 else ''}")
    _task_action_table(manager, rows, "browse")


def show_task_library(manager: TaskManager) -> None:
    """Render reusable-task maintenance.

    :param manager: Application service.
    """
    st.header("Task Library")
    rows = manager.list_predefined_tasks()
    selected_id = _reference_table(
        rows,
        "predefined_task_id",
        {
            "description": "Description",
            "location_name": "Location",
            "type_name": "Type",
            "category_name": "Category",
        },
        "predefined_task",
    )
    selected = next((row for row in rows if row["predefined_task_id"] == selected_id), None)
    type_ids, type_labels = _type_options(manager)
    if not type_ids:
        st.info("Add a category and task type first.")
        return
    with st.form(_reference_form_key("predefined_task", selected_id)):
        description = st.text_input("Description", selected["description"] if selected else "")
        location_ids, location_labels = _location_options(manager)
        current_location = selected["location_id"] if selected else 0
        location_id = st.selectbox(
            "Location",
            location_ids,
            index=location_ids.index(current_location or 0),
            format_func=location_labels.get,
        ) or None
        current_type = (
            selected["type_id"] if selected and selected["type_id"] in type_ids else type_ids[0]
        )
        type_id = st.selectbox(
            "Task type", type_ids, index=type_ids.index(current_type), format_func=type_labels.get
        )
        save, delete, clear = _reference_form_buttons(selected is not None)
    try:
        if save:
            manager.save_predefined_task(description, type_id, selected_id, location_id)
            _refresh_reference_table("predefined_task")
        if delete and selected_id is not None:
            manager.delete_predefined_task(selected_id)
            _refresh_reference_table("predefined_task")
        if clear:
            _refresh_reference_table("predefined_task")
    except (ValueError, sqlite3.IntegrityError) as error:
        _show_error(error)


def _reference_table(
    rows: list[sqlite3.Row],
    id_column: str,
    display_columns: dict[str, str],
    key: str,
    duplicate: Callable[[int], None] | None = None,
) -> int | None:
    """Render a single-selection reference-data table.

    :param rows: Reference rows to display.
    :param id_column: Primary-key column name.
    :param display_columns: Source columns and displayed headings.
    :param key: Session-state namespace.
    :return: Selected record ID, if any.
    """
    selection_key = f"{key}_selected_id"
    generation_key = f"{key}_table_generation"
    selected_id = st.session_state.get(selection_key)
    table_rows = [
        {
            "Selected": row[id_column] == selected_id,
            id_column: row[id_column],
            **{heading: row[column] for column, heading in display_columns.items()},
            **({"Duplicate": ":material/content_copy:"} if duplicate else {}),
        }
        for row in rows
    ]
    generation = st.session_state.get(generation_key, 0)
    column_config: dict[str, object] = {
        "Selected": st.column_config.CheckboxColumn(""),
        id_column: None,
    }
    if duplicate:
        click_key = f"{key}_duplicate_click_{generation}"

        def duplicate_clicked() -> None:
            """Duplicate the row reported by the table button callback."""
            click = st.session_state.get(click_key)
            if click is not None:
                duplicate(int(rows[click["row"]][id_column]))

        column_config["Duplicate"] = st.column_config.ButtonColumn(
            "",
            type="tertiary",
            on_click=duplicate_clicked,
            key=click_key,
        )
    disabled_columns = [id_column, *display_columns.values()]
    if duplicate:
        disabled_columns.append("Duplicate")
    edited_rows = st.data_editor(
        table_rows,
        key=f"{key}_table_{generation}",
        hide_index=True,
        width="stretch",
        disabled=disabled_columns,
        column_config=column_config,
    )
    checked_ids = [row[id_column] for row in edited_rows if row["Selected"]]
    if set(checked_ids) != ({selected_id} if selected_id is not None else set()):
        newly_checked = [record_id for record_id in checked_ids if record_id != selected_id]
        st.session_state[selection_key] = newly_checked[-1] if newly_checked else None
        st.session_state[generation_key] = generation + 1
        st.rerun()
    return selected_id


def _refresh_reference_table(key: str, selected_id: int | None = None) -> None:
    """Set a reference selection and redraw its table.

    :param key: Session-state namespace.
    :param selected_id: Record to select, or none to clear.
    """
    st.session_state[f"{key}_selected_id"] = selected_id
    generation_key = f"{key}_table_generation"
    st.session_state[generation_key] = st.session_state.get(generation_key, 0) + 1
    form_generation_key = f"{key}_form_generation"
    st.session_state[form_generation_key] = st.session_state.get(form_generation_key, 0) + 1
    st.rerun()


def _reference_form_key(key: str, selected_id: int | None) -> str:
    """Return a form key that changes whenever the form must be reset."""
    generation = st.session_state.get(f"{key}_form_generation", 0)
    return f"{key}_form_{selected_id}_{generation}"


def _reference_form_buttons(editing: bool) -> tuple[bool, bool, bool]:
    """Render full-width Save, Delete, and Clear form actions.

    :param editing: Whether an existing record is selected.
    :return: Submitted state for each action.
    """
    save_column, delete_column, clear_column = st.columns(3)
    save = save_column.form_submit_button("Save", type="primary", use_container_width=True)
    delete = delete_column.form_submit_button(
        "Delete", disabled=not editing, use_container_width=True
    )
    clear = clear_column.form_submit_button("Clear", use_container_width=True)
    return save, delete, clear


def show_templates(manager: TaskManager) -> None:
    """Render template and ordered-membership maintenance.

    :param manager: Application service.
    """
    st.header("Templates")
    templates = manager.list_templates()

    def duplicate_template(template_id: int) -> None:
        """Duplicate a template selected through its row action."""
        copied_id = manager.duplicate_template(template_id)
        st.session_state["template_selected_id"] = copied_id
        st.session_state["template_table_generation"] = (
            st.session_state.get("template_table_generation", 0) + 1
        )

    selected_id = _reference_table(
        templates,
        "template_id",
        {"name": "Name", "description": "Description", "task_count": "Tasks"},
        "template",
        duplicate=duplicate_template,
    )
    selected = next(
        (row for row in templates if row["template_id"] == selected_id), None
    )
    library = manager.list_predefined_tasks()
    task_labels = {
        row["predefined_task_id"]: f"{row['description']} — {row['type_name']}" for row in library
    }
    current = (
        [row["predefined_task_id"] for row in manager.get_template_tasks(selected_id)]
        if selected_id is not None
        else []
    )
    task_counts = Counter(current)
    task_order = sorted(task_labels, key=lambda task_id: task_labels[task_id].casefold())
    with st.form(_reference_form_key("template", selected_id)):
        name = st.text_input("Name", selected["name"] if selected else "")
        description = st.text_area(
            "Description", selected["description"] or "" if selected else ""
        )
        task_quantities = st.data_editor(
            [
                {
                    "predefined_task_id": task_id,
                    "Task": task_labels[task_id],
                    "Quantity": task_counts[task_id],
                }
                for task_id in task_order
            ],
            hide_index=True,
            width="stretch",
            disabled=["predefined_task_id", "Task"],
            column_config={
                "predefined_task_id": None,
                "Quantity": st.column_config.NumberColumn(
                    "Quantity", min_value=0, step=1, required=True
                ),
            },
        )
        save, delete, clear = _reference_form_buttons(selected is not None)
    tasks = [
        row["predefined_task_id"]
        for row in task_quantities
        for _ in range(int(row["Quantity"] or 0))
    ]
    try:
        if save:
            manager.save_template(name, description, tasks, selected_id)
            _refresh_reference_table("template")
        if delete and selected_id is not None:
            manager.delete_template(selected_id)
            _refresh_reference_table("template")
        if clear:
            _refresh_reference_table("template")
    except (ValueError, sqlite3.IntegrityError) as error:
        _show_error(error)


def show_reference_data(manager: TaskManager) -> None:
    """Render category, task-type, and location maintenance forms.

    :param manager: Application service.
    """
    st.header("Reference Data")
    category_tab, type_tab, location_tab = st.tabs(
        ("Categories", "Task Types", "Locations")
    )
    categories = sorted(manager.list_categories(), key=lambda row: row["name"].casefold())
    with category_tab:
        selected_id = _reference_table(
            categories, "category_id", {"name": "Name"}, "category"
        )
        selected = next(
            (row for row in categories if row["category_id"] == selected_id), None
        )
        with st.form(_reference_form_key("category", selected_id)):
            name = st.text_input("Name", selected["name"] if selected else "")
            save, delete, clear = _reference_form_buttons(selected is not None)
        try:
            if save:
                manager.save_category(name, selected_id)
                _refresh_reference_table("category")
            if delete and selected_id is not None:
                manager.delete_category(selected_id)
                _refresh_reference_table("category")
            if clear:
                _refresh_reference_table("category")
        except (ValueError, sqlite3.IntegrityError) as error:
            _show_error(error)
    with type_tab:
        rows = sorted(manager.list_types(), key=lambda row: row["name"].casefold())
        selected_id = _reference_table(
            rows,
            "type_id",
            {"name": "Name", "category_name": "Category"},
            "task_type",
        )
        selected = next((row for row in rows if row["type_id"] == selected_id), None)
        if not categories:
            st.info("Create a category first.")
        else:
            category_labels = {row["category_id"]: row["name"] for row in categories}
            category_ids = list(category_labels)
            current_category = selected["category_id"] if selected else category_ids[0]
            with st.form(_reference_form_key("task_type", selected_id)):
                name = st.text_input("Name", selected["name"] if selected else "")
                category_id = st.selectbox(
                    "Category",
                    category_ids,
                    index=category_ids.index(current_category),
                    format_func=category_labels.get,
                )
                save, delete, clear = _reference_form_buttons(selected is not None)
            try:
                if save:
                    manager.save_type(name, category_id, selected_id)
                    _refresh_reference_table("task_type")
                if delete and selected_id is not None:
                    manager.delete_type(selected_id)
                    _refresh_reference_table("task_type")
                if clear:
                    _refresh_reference_table("task_type")
            except (ValueError, sqlite3.IntegrityError) as error:
                _show_error(error)
    with location_tab:
        locations = sorted(manager.list_locations(), key=lambda row: row["name"].casefold())
        selected_id = _reference_table(
            locations, "location_id", {"name": "Name"}, "location"
        )
        selected = next(
            (row for row in locations if row["location_id"] == selected_id), None
        )
        with st.form(_reference_form_key("location", selected_id)):
            name = st.text_input("Name", selected["name"] if selected else "")
            save, delete, clear = _reference_form_buttons(selected is not None)
        try:
            if save:
                manager.save_location(name, selected_id)
                _refresh_reference_table("location")
            if delete and selected_id is not None:
                manager.delete_location(selected_id)
                _refresh_reference_table("location")
            if clear:
                _refresh_reference_table("location")
        except (ValueError, sqlite3.IntegrityError) as error:
            _show_error(error)


def _show_import_result(imported: int, issues: tuple[object, ...]) -> None:
    """Display a CSV import result.

    :param imported: Number of records imported.
    :param issues: ImportIssue-like objects.
    """
    st.success(f"Imported {imported} new record{'s' if imported != 1 else ''}.")
    if issues:
        st.warning(f"{len(issues)} row{'s' if len(issues) != 1 else ''} could not be imported.")
        st.dataframe(
            [{"Row": issue.row_number, "Problem": issue.message} for issue in issues],
            hide_index=True,
            use_container_width=True,
        )


def show_import(manager: TaskManager) -> None:
    """Render the selected CSV import workflow.

    :param manager: Application service.
    """
    st.header("Import")
    import_type = st.selectbox(
        "Import type",
        (
            "Historical Tasks",
            "Pre-Defined Tasks",
            "Templates",
            "Categories",
            "Task Types",
            "Locations",
        ),
    )
    configurations = {
        "Historical Tasks": (
            "historical",
            "Required headings: Start, End, Description, Type, Category. "
            "Location is optional. Dates use DD/MM/YY.",
            import_historical_tasks,
        ),
        "Pre-Defined Tasks": (
            "library",
            "Required headings: Description, Type, and Category. Location is optional.",
            import_predefined_tasks,
        ),
        "Templates": (
            "template",
            "Required headings: Template, Description, Location, Type, and Category.",
            import_templates,
        ),
        "Categories": (
            "category",
            "Required heading: Category.",
            import_categories,
        ),
        "Task Types": (
            "type",
            "Required headings: Type and Category.",
            import_types,
        ),
        "Locations": (
            "location",
            "Required heading: Location.",
            import_locations,
        ),
    }
    state_prefix, caption, importer = configurations[import_type]
    st.caption(caption)
    generation_key = f"{state_prefix}_csv_generation"
    result_key = f"{state_prefix}_import_result"
    generation = st.session_state.get(generation_key, 0)
    uploader = st.empty()
    uploaded = uploader.file_uploader(
        f"{import_type} CSV",
        type="csv",
        key=f"{state_prefix}_csv_{generation}",
    )
    if uploaded and st.button(f"Import {import_type}", type="primary"):
        try:
            with st.spinner(f"Importing {import_type.lower()}…"):
                result = importer(uploaded.getvalue(), manager)
            st.session_state[result_key] = result
            st.session_state[generation_key] = generation + 1
            uploader.empty()
        except ValueError as error:
            _show_error(error)
    saved_result = st.session_state.get(result_key)
    if saved_result is not None:
        _show_import_result(saved_result.imported, saved_result.issues)


def show_export(manager: TaskManager) -> None:
    """Render selectable CSV exports.

    :param manager: Application service.
    """
    st.header("Export")
    filenames = {
        "Historical Tasks": "historical-tasks",
        "Pre-Defined Tasks": "pre-defined-tasks",
        "Templates": "templates",
        "Categories": "categories",
        "Task Types": "task-types",
        "Locations": "locations",
    }
    exporters = {
        "Historical Tasks": export_tasks,
        "Pre-Defined Tasks": export_predefined_tasks,
        "Templates": export_templates,
        "Categories": export_categories,
        "Task Types": export_types,
        "Locations": export_locations,
    }
    if "export_type" not in st.session_state:
        st.session_state["export_type"] = "Historical Tasks"
    if "export_file_name" not in st.session_state:
        st.session_state["export_file_name"] = filenames[st.session_state["export_type"]]

    def reset_export_filename() -> None:
        """Reset the filename whenever the selected export type changes."""
        st.session_state["export_file_name"] = filenames[st.session_state["export_type"]]

    export_type = st.selectbox(
        "Export type",
        tuple(exporters),
        key="export_type",
        on_change=reset_export_filename,
    )
    historical_selected = export_type == "Historical Tasks"
    filter_by_date = st.checkbox(
        "Filter by date",
        disabled=not historical_selected,
    )
    today = date.today()
    date_columns = st.columns(2)
    start_date = date_columns[0].date_input(
        "Start date",
        date(today.year, 1, 1),
        disabled=not historical_selected or not filter_by_date,
    )
    end_date = date_columns[1].date_input(
        "End date",
        today,
        disabled=not historical_selected or not filter_by_date,
    )
    file_name = st.text_input("File name", key="export_file_name").strip()
    if not file_name:
        file_name = filenames[export_type]
    if not file_name.casefold().endswith(".csv"):
        file_name += ".csv"
    export_data = (
        export_tasks(manager, start_date, end_date)
        if historical_selected and filter_by_date
        else exporters[export_type](manager)
    )
    st.download_button(
        "Export",
        export_data,
        file_name=file_name,
        mime="text/csv",
        type="primary",
    )


def main() -> None:
    """Configure Streamlit and dispatch the selected application page."""
    st.set_page_config(page_title="Daily Task Manager", page_icon="✓", layout="wide")
    manager = TaskManager()
    application_version = version("daily-task-manager")
    st.title(f"📋 Daily Task Manager v{application_version}")
    st.markdown(
        """
        <style>
        .stMainBlockContainer {
            padding-top: 2.75rem;
        }
        h1 {
            padding-bottom: 0;
        }
        .st-key-main_navigation {
            margin-top: -0.4rem;
            margin-bottom: -0.65rem;
        }
        .st-key-page_content h2 {
            padding-top: 0.35rem;
        }
        div[role="radiogroup"] {
            gap: 0;
            border-bottom: 1px solid rgba(128, 128, 128, 0.35);
            margin-bottom: 0.35rem;
        }
        div[role="radiogroup"] > label {
            padding: 0.55rem 0.9rem 0.65rem;
            border-radius: 0.45rem 0.45rem 0 0;
        }
        div[role="radiogroup"] > label[data-selected="true"] {
            background: rgba(128, 128, 128, 0.13);
            border-bottom: 3px solid #ff4b4b;
            margin-bottom: -1px;
        }
        label[data-testid="stRadioOption"] > div > div > div:first-child {
            display: none;
        }
        div[data-testid="stAppViewContainer"]:has(div[data-testid="stSpinner"]),
        div[data-testid="stAppViewContainer"]:has(div[data-testid="stSpinner"]) * {
            cursor: wait !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Navigation",
        PAGES,
        horizontal=True,
        label_visibility="collapsed",
        key="main_navigation",
    )
    routes = {
        "Today": show_today,
        "Browse Tasks": show_browser,
        "Task Library": show_task_library,
        "Templates": show_templates,
        "Reference Data": show_reference_data,
        "Import": show_import,
        "Export": show_export,
    }
    with st.container(key="page_content"):
        routes[page](manager)


if __name__ == "__main__":
    main()
