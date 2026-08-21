"""Create the initial Daily Task Manager schema."""

from yoyo import step

steps = [
    step(
        """CREATE TABLE task_categories (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
        )""",
        "DROP TABLE task_categories",
    ),
    step(
        """CREATE TABLE task_types (
            type_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE,
            category_id INTEGER NOT NULL REFERENCES task_categories(category_id),
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            UNIQUE (name, category_id)
        )""",
        "DROP TABLE task_types",
    ),
    step(
        """CREATE TABLE predefined_tasks (
            predefined_task_id INTEGER PRIMARY KEY,
            description TEXT NOT NULL COLLATE NOCASE,
            type_id INTEGER NOT NULL REFERENCES task_types(type_id),
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            UNIQUE (description, type_id)
        )""",
        "DROP TABLE predefined_tasks",
    ),
    step(
        """CREATE TABLE daily_templates (
            template_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            description TEXT,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
        )""",
        "DROP TABLE daily_templates",
    ),
    step(
        """CREATE TABLE daily_template_tasks (
            template_id INTEGER NOT NULL REFERENCES daily_templates(template_id),
            predefined_task_id INTEGER NOT NULL REFERENCES predefined_tasks(predefined_task_id),
            display_order INTEGER,
            PRIMARY KEY (template_id, predefined_task_id)
        )""",
        "DROP TABLE daily_template_tasks",
    ),
    step(
        """CREATE TABLE tasks (
            task_id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            type_id INTEGER NOT NULL REFERENCES task_types(type_id),
            predefined_task_id INTEGER REFERENCES predefined_tasks(predefined_task_id),
            CHECK (date(start_date) = start_date),
            CHECK (end_date IS NULL OR date(end_date) = end_date),
            CHECK (end_date IS NULL OR end_date >= start_date)
        )""",
        "DROP TABLE tasks",
    ),
    step(
        "CREATE INDEX tasks_start_date_idx ON tasks(start_date)", "DROP INDEX tasks_start_date_idx"
    ),
    step("CREATE INDEX tasks_end_date_idx ON tasks(end_date)", "DROP INDEX tasks_end_date_idx"),
    step("CREATE INDEX tasks_type_id_idx ON tasks(type_id)", "DROP INDEX tasks_type_id_idx"),
]
