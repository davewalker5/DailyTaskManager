"""Business operations for tasks, classifications, libraries, and templates."""

import sqlite3
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path

from daily_task_manager.database import connect
from daily_task_manager.models import TaskFilter, TaskStatus


class TaskManager:
    """Provide validated application operations backed by SQLite."""

    def __init__(self, database_path: Path | None = None) -> None:
        """Initialise the service and ensure its schema is current.

        :param database_path: Optional path used instead of the configured default.
        """
        self.database_path = database_path
        with connect(self.database_path):
            pass

    @staticmethod
    def _required_text(value: str, field_name: str) -> str:
        """Normalise and validate a required text field.

        :param value: User-supplied value.
        :param field_name: Name used in validation messages.
        :return: Stripped text.
        :raises ValueError: If the value is blank.
        """
        normalised = value.strip()
        if not normalised:
            raise ValueError(f"{field_name} is required")
        return normalised

    @staticmethod
    def _validate_dates(start_date: date, end_date: date | None) -> None:
        """Validate that a completion does not predate its task.

        :param start_date: Task start date.
        :param end_date: Optional completion date.
        :raises ValueError: If the dates are inconsistent.
        """
        if end_date is not None and end_date < start_date:
            raise ValueError("End date cannot be before start date")

    def list_categories(self) -> list[sqlite3.Row]:
        """List categories alphabetically.

        :return: Category rows.
        """
        with connect(self.database_path) as connection:
            return list(
                connection.execute("SELECT * FROM task_categories ORDER BY name COLLATE NOCASE")
            )

    def save_category(self, name: str, category_id: int | None = None) -> int:
        """Create or update a category.

        :param name: Unique category name.
        :param category_id: Existing record ID, or none to create.
        :return: Saved category ID.
        """
        name = self._required_text(name, "Category name")
        with connect(self.database_path) as connection:
            if category_id is None:
                cursor = connection.execute("INSERT INTO task_categories(name) VALUES (?)", (name,))
                return int(cursor.lastrowid)
            cursor = connection.execute(
                "UPDATE task_categories SET name = ? WHERE category_id = ?",
                (name, category_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Category not found")
            return category_id

    def ensure_category(self, name: str) -> bool:
        """Create a category unless its name already exists.

        :param name: Category name.
        :return: True when a new category was created.
        """
        name = self._required_text(name, "Category")
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO task_categories(name) VALUES (?)", (name,)
            )
            return cursor.rowcount == 1

    def delete_category(self, category_id: int) -> None:
        """Delete an unused category.

        :param category_id: Category to delete.
        :raises ValueError: If the category is in use or does not exist.
        """
        with connect(self.database_path) as connection:
            in_use = connection.execute(
                "SELECT 1 FROM task_types WHERE category_id = ? LIMIT 1", (category_id,)
            ).fetchone()
            if in_use is not None:
                raise ValueError("Category is in use and cannot be deleted")
            cursor = connection.execute(
                "DELETE FROM task_categories WHERE category_id = ?", (category_id,)
            )
            if cursor.rowcount != 1:
                raise ValueError("Category not found")

    def list_types(self) -> list[sqlite3.Row]:
        """List task types with their category names.

        :return: Task type rows.
        """
        query = """
            SELECT tt.*, tc.name AS category_name
            FROM task_types tt JOIN task_categories tc USING (category_id)
        """
        query += " ORDER BY tc.name COLLATE NOCASE, tt.name COLLATE NOCASE"
        with connect(self.database_path) as connection:
            return list(connection.execute(query))

    def list_locations(self) -> list[sqlite3.Row]:
        """List locations alphabetically.

        :return: Location rows.
        """
        with connect(self.database_path) as connection:
            return list(
                connection.execute("SELECT * FROM locations ORDER BY name COLLATE NOCASE")
            )

    def save_location(self, name: str, location_id: int | None = None) -> int:
        """Create or update a location.

        :param name: Unique location name.
        :param location_id: Existing record ID, or none to create.
        :return: Saved location ID.
        """
        name = self._required_text(name, "Location name")
        with connect(self.database_path) as connection:
            if location_id is None:
                cursor = connection.execute("INSERT INTO locations(name) VALUES (?)", (name,))
                return int(cursor.lastrowid)
            cursor = connection.execute(
                "UPDATE locations SET name = ? WHERE location_id = ?", (name, location_id)
            )
            if cursor.rowcount != 1:
                raise ValueError("Location not found")
            return location_id

    def ensure_location(self, name: str) -> bool:
        """Create a location unless its name already exists.

        :param name: Location name.
        :return: True when a new location was created.
        """
        name = self._required_text(name, "Location")
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO locations(name) VALUES (?)", (name,)
            )
            return cursor.rowcount == 1

    def delete_location(self, location_id: int) -> None:
        """Delete a location that is not assigned to any task.

        :param location_id: Location to delete.
        :raises ValueError: If the location is in use or does not exist.
        """
        with connect(self.database_path) as connection:
            in_use = connection.execute(
                """SELECT 1 FROM predefined_tasks WHERE location_id = ?
                   UNION ALL
                   SELECT 1 FROM tasks WHERE location_id = ?
                   LIMIT 1""",
                (location_id, location_id),
            ).fetchone()
            if in_use is not None:
                raise ValueError("Location is in use and cannot be deleted")
            cursor = connection.execute(
                "DELETE FROM locations WHERE location_id = ?", (location_id,)
            )
            if cursor.rowcount != 1:
                raise ValueError("Location not found")

    def resolve_location(self, name: str) -> int | None:
        """Find or create an optional location from user or import text.

        :param name: Location name, or blank for no location.
        :return: Resolved location ID, or none.
        """
        name = name.strip()
        if not name:
            return None
        with connect(self.database_path) as connection:
            connection.execute("INSERT OR IGNORE INTO locations(name) VALUES (?)", (name,))
            location = connection.execute(
                "SELECT location_id FROM locations WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            assert location is not None
            return int(location["location_id"])

    def save_type(self, name: str, category_id: int, type_id: int | None = None) -> int:
        """Create or update a task type.

        :param name: Type name, unique within its category.
        :param category_id: Parent category ID.
        :param type_id: Existing record ID, or none to create.
        :return: Saved task type ID.
        """
        name = self._required_text(name, "Task type name")
        with connect(self.database_path) as connection:
            if type_id is None:
                cursor = connection.execute(
                    "INSERT INTO task_types(name, category_id) VALUES (?, ?)",
                    (name, category_id),
                )
                return int(cursor.lastrowid)
            cursor = connection.execute(
                "UPDATE task_types SET name = ?, category_id = ? WHERE type_id = ?",
                (name, category_id, type_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Task type not found")
            return type_id

    def ensure_type(self, name: str, category_name: str) -> bool:
        """Create a task type and resolve its parent category.

        :param name: Task type name.
        :param category_name: Parent category name.
        :return: True when a new task type was created.
        """
        name = self._required_text(name, "Type")
        category_name = self._required_text(category_name, "Category")
        with connect(self.database_path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO task_categories(name) VALUES (?)", (category_name,)
            )
            category = connection.execute(
                "SELECT category_id FROM task_categories WHERE name = ? COLLATE NOCASE",
                (category_name,),
            ).fetchone()
            assert category is not None
            cursor = connection.execute(
                "INSERT OR IGNORE INTO task_types(name, category_id) VALUES (?, ?)",
                (name, category["category_id"]),
            )
            return cursor.rowcount == 1

    def delete_type(self, type_id: int) -> None:
        """Delete a task type that is not assigned to a task definition or task.

        :param type_id: Task type to delete.
        :raises ValueError: If the task type is in use or does not exist.
        """
        with connect(self.database_path) as connection:
            in_use = connection.execute(
                """SELECT 1 FROM predefined_tasks WHERE type_id = ?
                   UNION ALL
                   SELECT 1 FROM tasks WHERE type_id = ?
                   LIMIT 1""",
                (type_id, type_id),
            ).fetchone()
            if in_use is not None:
                raise ValueError("Task type is in use and cannot be deleted")
            cursor = connection.execute("DELETE FROM task_types WHERE type_id = ?", (type_id,))
            if cursor.rowcount != 1:
                raise ValueError("Task type not found")

    def list_predefined_tasks(self) -> list[sqlite3.Row]:
        """List reusable tasks with their classification.

        :return: Pre-defined task rows.
        """
        query = """
            SELECT p.*, tt.name AS type_name, tc.name AS category_name, l.name AS location_name
            FROM predefined_tasks p
            JOIN task_types tt USING (type_id)
            JOIN task_categories tc USING (category_id)
            LEFT JOIN locations l USING (location_id)
        """
        query += " ORDER BY p.description COLLATE NOCASE"
        with connect(self.database_path) as connection:
            return list(connection.execute(query))

    def save_predefined_task(
        self,
        description: str,
        type_id: int,
        predefined_task_id: int | None = None,
        location_id: int | None = None,
    ) -> int:
        """Create or update a reusable task definition.

        :param description: Reusable task description.
        :param type_id: Task type ID.
        :param predefined_task_id: Existing record ID, or none to create.
        :param location_id: Optional location ID.
        :return: Saved pre-defined task ID.
        """
        description = self._required_text(description, "Description")
        with connect(self.database_path) as connection:
            if predefined_task_id is None:
                cursor = connection.execute(
                    """INSERT INTO predefined_tasks
                       (description, type_id, location_id) VALUES (?, ?, ?)""",
                    (description, type_id, location_id),
                )
                return int(cursor.lastrowid)
            cursor = connection.execute(
                """UPDATE predefined_tasks
                   SET description = ?, type_id = ?, location_id = ?
                   WHERE predefined_task_id = ?""",
                (description, type_id, location_id, predefined_task_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Pre-defined task not found")
            return predefined_task_id

    def delete_predefined_task(self, predefined_task_id: int) -> None:
        """Delete a reusable task that is not referenced elsewhere.

        :param predefined_task_id: Reusable task to delete.
        :raises ValueError: If the task is in use or does not exist.
        """
        with connect(self.database_path) as connection:
            in_use = connection.execute(
                """SELECT 1 FROM daily_template_tasks WHERE predefined_task_id = ?
                   UNION ALL
                   SELECT 1 FROM tasks WHERE predefined_task_id = ?
                   LIMIT 1""",
                (predefined_task_id, predefined_task_id),
            ).fetchone()
            if in_use is not None:
                raise ValueError("Pre-defined task is in use and cannot be deleted")
            cursor = connection.execute(
                "DELETE FROM predefined_tasks WHERE predefined_task_id = ?",
                (predefined_task_id,),
            )
            if cursor.rowcount != 1:
                raise ValueError("Pre-defined task not found")

    def list_templates(self) -> list[sqlite3.Row]:
        """List templates with task counts.

        :return: Template rows.
        """
        query = """
            SELECT t.*, COUNT(dtt.predefined_task_id) AS task_count
            FROM daily_templates t
            LEFT JOIN daily_template_tasks dtt USING (template_id)
        """
        query += " GROUP BY t.template_id ORDER BY t.name COLLATE NOCASE"
        with connect(self.database_path) as connection:
            return list(connection.execute(query))

    def save_template(
        self,
        name: str,
        description: str = "",
        predefined_task_ids: Sequence[int] = (),
        template_id: int | None = None,
    ) -> int:
        """Create or update a template and its ordered membership.

        :param name: Unique template name.
        :param description: Optional explanation.
        :param predefined_task_ids: Ordered reusable task IDs.
        :param template_id: Existing record ID, or none to create.
        :return: Saved template ID.
        """
        name = self._required_text(name, "Template name")
        with connect(self.database_path) as connection:
            if template_id is None:
                cursor = connection.execute(
                    "INSERT INTO daily_templates(name, description) VALUES (?, ?)",
                    (name, description.strip() or None),
                )
                template_id = int(cursor.lastrowid)
            else:
                cursor = connection.execute(
                    """UPDATE daily_templates SET name = ?, description = ?
                       WHERE template_id = ?""",
                    (name, description.strip() or None, template_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("Template not found")
                connection.execute(
                    "DELETE FROM daily_template_tasks WHERE template_id = ?", (template_id,)
                )
            connection.executemany(
                """INSERT INTO daily_template_tasks
                   (template_id, predefined_task_id, display_order) VALUES (?, ?, ?)""",
                (
                    (template_id, task_id, order)
                    for order, task_id in enumerate(predefined_task_ids, 1)
                ),
            )
            return template_id

    def delete_template(self, template_id: int) -> None:
        """Delete a template and its task memberships.

        :param template_id: Template to delete.
        :raises ValueError: If the template does not exist.
        """
        with connect(self.database_path) as connection:
            connection.execute(
                "DELETE FROM daily_template_tasks WHERE template_id = ?", (template_id,)
            )
            cursor = connection.execute(
                "DELETE FROM daily_templates WHERE template_id = ?", (template_id,)
            )
            if cursor.rowcount != 1:
                raise ValueError("Template not found")

    def duplicate_template(self, template_id: int) -> int:
        """Duplicate a template and its ordered task memberships.

        :param template_id: Source template ID.
        :return: New template ID.
        :raises ValueError: If the source template does not exist.
        """
        with connect(self.database_path) as connection:
            source = connection.execute(
                "SELECT name, description FROM daily_templates WHERE template_id = ?",
                (template_id,),
            ).fetchone()
            if source is None:
                raise ValueError("Template not found")
            existing_names = {
                row["name"].casefold()
                for row in connection.execute("SELECT name FROM daily_templates")
            }
            copy_number = 1
            while True:
                suffix = " - Copy" if copy_number == 1 else f" - Copy {copy_number}"
                copy_name = f"{source['name']}{suffix}"
                if copy_name.casefold() not in existing_names:
                    break
                copy_number += 1
            cursor = connection.execute(
                "INSERT INTO daily_templates(name, description) VALUES (?, ?)",
                (copy_name, source["description"]),
            )
            copied_id = int(cursor.lastrowid)
            connection.execute(
                """INSERT INTO daily_template_tasks
                   (template_id, predefined_task_id, display_order)
                   SELECT ?, predefined_task_id, display_order
                   FROM daily_template_tasks WHERE template_id = ?""",
                (copied_id, template_id),
            )
            return copied_id

    def ensure_template_task(
        self,
        template_name: str,
        task_description: str,
        type_id: int,
        location_id: int | None = None,
    ) -> bool:
        """Resolve a template and reusable task, then ensure their association.

        :param template_name: Destination template name.
        :param task_description: Reusable task description.
        :param type_id: Resolved task type ID.
        :param location_id: Optional location ID for a newly created task.
        :return: True when a new template-task association was created.
        """
        template_name = self._required_text(template_name, "Template")
        task_description = self._required_text(task_description, "Description")
        with connect(self.database_path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO daily_templates(name) VALUES (?)", (template_name,)
            )
            template = connection.execute(
                "SELECT template_id FROM daily_templates WHERE name = ? COLLATE NOCASE",
                (template_name,),
            ).fetchone()
            assert template is not None
            connection.execute(
                """INSERT OR IGNORE INTO predefined_tasks
                   (description, type_id, location_id) VALUES (?, ?, ?)""",
                (task_description, type_id, location_id),
            )
            task = connection.execute(
                """SELECT predefined_task_id FROM predefined_tasks
                   WHERE description = ? COLLATE NOCASE AND type_id = ?""",
                (task_description, type_id),
            ).fetchone()
            assert task is not None
            next_order = connection.execute(
                """SELECT COALESCE(MAX(display_order), 0) + 1
                   FROM daily_template_tasks WHERE template_id = ?""",
                (template["template_id"],),
            ).fetchone()[0]
            existing = connection.execute(
                """SELECT 1 FROM daily_template_tasks
                   WHERE template_id = ? AND predefined_task_id = ? LIMIT 1""",
                (template["template_id"], task["predefined_task_id"]),
            ).fetchone()
            if existing is not None:
                return False
            connection.execute(
                """INSERT INTO daily_template_tasks
                   (template_id, predefined_task_id, display_order) VALUES (?, ?, ?)""",
                (template["template_id"], task["predefined_task_id"], next_order),
            )
            return True

    def get_template_tasks(self, template_id: int) -> list[sqlite3.Row]:
        """Return reusable tasks belonging to a template.

        :param template_id: Template ID.
        :return: Ordered task rows.
        """
        with connect(self.database_path) as connection:
            return list(
                connection.execute(
                    """
                    SELECT p.*, tt.name AS type_name, tc.name AS category_name,
                           l.name AS location_name,
                           dtt.display_order
                    FROM daily_template_tasks dtt
                    JOIN predefined_tasks p USING (predefined_task_id)
                    JOIN task_types tt USING (type_id)
                    JOIN task_categories tc USING (category_id)
                    LEFT JOIN locations l USING (location_id)
                    WHERE dtt.template_id = ?
                    ORDER BY dtt.display_order, p.description COLLATE NOCASE
                    """,
                    (template_id,),
                )
            )

    def add_ad_hoc_task(
        self,
        description: str,
        type_id: int,
        start_date: date,
        location_id: int | None = None,
    ) -> int:
        """Create an open task without a library origin.

        :param description: Task description.
        :param type_id: Classification ID.
        :param start_date: Date the task starts.
        :param location_id: Optional location ID.
        :return: New task ID.
        """
        description = self._required_text(description, "Description")
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                """INSERT INTO tasks(description, start_date, type_id, location_id)
                   VALUES (?, ?, ?, ?)""",
                (description, start_date.isoformat(), type_id, location_id),
            )
            return int(cursor.lastrowid)

    def instantiate_template_tasks(
        self, start_date: date, predefined_task_ids: Sequence[int]
    ) -> int:
        """Copy selected library definitions into historical task records.

        :param start_date: Date assigned to each new task.
        :param predefined_task_ids: IDs selected by the user.
        :return: Number of tasks created.
        :raises ValueError: If any selected definition is unavailable.
        """
        if not predefined_task_ids:
            return 0
        placeholders = ",".join("?" for _ in predefined_task_ids)
        with connect(self.database_path) as connection:
            rows = list(
                connection.execute(
                    f"""SELECT predefined_task_id, description, type_id, location_id
                        FROM predefined_tasks
                        WHERE predefined_task_id IN ({placeholders})""",
                    tuple(predefined_task_ids),
                )
            )
            rows_by_id = {row["predefined_task_id"]: row for row in rows}
            if len(rows_by_id) != len(set(predefined_task_ids)):
                raise ValueError("One or more selected pre-defined tasks are unavailable")
            ordered_rows = [rows_by_id[task_id] for task_id in predefined_task_ids]
            connection.executemany(
                """INSERT INTO tasks
                   (description, start_date, type_id, predefined_task_id, location_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    (
                        row["description"],
                        start_date.isoformat(),
                        row["type_id"],
                        row["predefined_task_id"],
                        row["location_id"],
                    )
                    for row in ordered_rows
                ),
            )
            return len(ordered_rows)

    def set_task_completion(self, task_id: int, end_date: date | None) -> None:
        """Complete or reopen a task.

        :param task_id: Historical task ID.
        :param end_date: Completion date, or none to reopen.
        """
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT start_date FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Task not found")
            self._validate_dates(date.fromisoformat(row["start_date"]), end_date)
            connection.execute(
                "UPDATE tasks SET end_date = ? WHERE task_id = ?",
                (end_date.isoformat() if end_date else None, task_id),
            )

    def delete_task(self, task_id: int) -> None:
        """Delete a task.

        :param task_id: Task to delete.
        :raises ValueError: If the task does not exist.
        """
        with connect(self.database_path) as connection:
            cursor = connection.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            if cursor.rowcount != 1:
                raise ValueError("Task not found")

    def list_tasks(self, filters: TaskFilter | None = None) -> list[sqlite3.Row]:
        """List historical tasks with optional browser filters.

        :param filters: Filter values combined with AND semantics.
        :return: Task rows with derived category and status.
        """
        filters = filters or TaskFilter()
        clauses: list[str] = []
        parameters: list[str | int] = []
        if filters.start_from:
            clauses.append("t.start_date >= ?")
            parameters.append(filters.start_from.isoformat())
        if filters.start_to:
            clauses.append("t.start_date <= ?")
            parameters.append(filters.start_to.isoformat())
        if filters.description.strip():
            clauses.append("instr(lower(t.description), lower(?)) > 0")
            parameters.append(filters.description.strip())
        if filters.status is TaskStatus.OPEN:
            clauses.append("t.end_date IS NULL")
        elif filters.status is TaskStatus.COMPLETED:
            clauses.append("t.end_date IS NOT NULL")
        if filters.type_id:
            clauses.append("t.type_id = ?")
            parameters.append(filters.type_id)
        if filters.category_id:
            clauses.append("tt.category_id = ?")
            parameters.append(filters.category_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with connect(self.database_path) as connection:
            return list(
                connection.execute(
                    f"""
                    SELECT t.*, tt.name AS type_name, tc.name AS category_name,
                           l.name AS location_name,
                           CASE WHEN t.end_date IS NULL THEN 'Open' ELSE 'Completed' END AS status
                    FROM tasks t
                    JOIN task_types tt USING (type_id)
                    JOIN task_categories tc USING (category_id)
                    LEFT JOIN locations l USING (location_id)
                    {where}
                    ORDER BY t.start_date DESC,
                             t.description COLLATE NOCASE,
                             t.task_id DESC
                    """,
                    parameters,
                )
            )

    def resolve_category_and_type(self, category_name: str, type_name: str) -> int:
        """Find or create a category and child type, returning the type ID.

        :param category_name: Category name from an import.
        :param type_name: Type name from an import.
        :return: Resolved type ID.
        """
        category_name = self._required_text(category_name, "Category")
        type_name = self._required_text(type_name, "Type")
        with connect(self.database_path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO task_categories(name) VALUES (?)", (category_name,)
            )
            category = connection.execute(
                "SELECT category_id FROM task_categories WHERE name = ? COLLATE NOCASE",
                (category_name,),
            ).fetchone()
            assert category is not None
            connection.execute(
                "INSERT OR IGNORE INTO task_types(name, category_id) VALUES (?, ?)",
                (type_name, category["category_id"]),
            )
            task_type = connection.execute(
                """SELECT type_id FROM task_types
                   WHERE name = ? COLLATE NOCASE AND category_id = ?""",
                (type_name, category["category_id"]),
            ).fetchone()
            assert task_type is not None
            return int(task_type["type_id"])

    def ensure_predefined_task(
        self, description: str, type_id: int, location_id: int | None = None
    ) -> bool:
        """Create a reusable task unless the same definition already exists.

        :param description: Reusable task description.
        :param type_id: Resolved task type ID.
        :param location_id: Optional location ID.
        :return: True when a new row was created.
        """
        description = self._required_text(description, "Task description")
        with connect(self.database_path) as connection:
            existing = connection.execute(
                """SELECT predefined_task_id FROM predefined_tasks
                   WHERE description = ? COLLATE NOCASE AND type_id = ?""",
                (description, type_id),
            ).fetchone()
            if existing is not None:
                connection.execute(
                    "UPDATE predefined_tasks SET location_id = ? WHERE predefined_task_id = ?",
                    (location_id, existing["predefined_task_id"]),
                )
                return False
            connection.execute(
                """INSERT INTO predefined_tasks(description, type_id, location_id)
                   VALUES (?, ?, ?)""",
                (description, type_id, location_id),
            )
            return True

    def add_imported_tasks(
        self, records: Iterable[tuple[str, date, date | None, int, int | None]]
    ) -> int:
        """Insert already validated historical task records atomically.

        :param records: Description, start, end, type, and optional location tuples.
        :return: Number of inserted records.
        """
        rows = list(records)
        for _, start_date, end_date, _, _ in rows:
            self._validate_dates(start_date, end_date)
        with connect(self.database_path) as connection:
            connection.executemany(
                """INSERT INTO tasks(description, start_date, end_date, type_id, location_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    (
                        description,
                        start.isoformat(),
                        end.isoformat() if end else None,
                        type_id,
                        location_id,
                    )
                    for description, start, end, type_id, location_id in rows
                ),
            )
        return len(rows)
