"""Remove active flags using SQLite's portable table-rebuild pattern."""

from yoyo import step

steps = [
    step(
        """CREATE TABLE task_categories_new (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE
        )"""
    ),
    step(
        """INSERT INTO task_categories_new(category_id, name)
           SELECT category_id, name FROM task_categories"""
    ),
    step("DROP TABLE task_categories"),
    step("ALTER TABLE task_categories_new RENAME TO task_categories"),
    step(
        """CREATE TABLE task_types_new (
            type_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE,
            category_id INTEGER NOT NULL REFERENCES task_categories(category_id),
            UNIQUE (name, category_id)
        )"""
    ),
    step(
        """INSERT INTO task_types_new(type_id, name, category_id)
           SELECT type_id, name, category_id FROM task_types"""
    ),
    step("DROP TABLE task_types"),
    step("ALTER TABLE task_types_new RENAME TO task_types"),
    step(
        """CREATE TABLE predefined_tasks_new (
            predefined_task_id INTEGER PRIMARY KEY,
            description TEXT NOT NULL COLLATE NOCASE,
            type_id INTEGER NOT NULL REFERENCES task_types(type_id),
            location_id INTEGER REFERENCES locations(location_id) ON DELETE SET NULL,
            UNIQUE (description, type_id)
        )"""
    ),
    step(
        """INSERT INTO predefined_tasks_new
           (predefined_task_id, description, type_id, location_id)
           SELECT predefined_task_id, description, type_id, location_id FROM predefined_tasks"""
    ),
    step("DROP TABLE predefined_tasks"),
    step("ALTER TABLE predefined_tasks_new RENAME TO predefined_tasks"),
    step(
        "CREATE INDEX predefined_tasks_location_id_idx ON predefined_tasks(location_id)"
    ),
    step(
        """CREATE TABLE daily_templates_new (
            template_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            description TEXT
        )"""
    ),
    step(
        """INSERT INTO daily_templates_new(template_id, name, description)
           SELECT template_id, name, description FROM daily_templates"""
    ),
    step("DROP TABLE daily_templates"),
    step("ALTER TABLE daily_templates_new RENAME TO daily_templates"),
]
