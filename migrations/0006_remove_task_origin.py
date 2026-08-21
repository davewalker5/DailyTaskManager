"""Remove the redundant pre-defined task origin from historical tasks."""

from yoyo import step

steps = [
    step(
        """CREATE TABLE tasks_new (
            task_id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            type_id INTEGER NOT NULL REFERENCES task_types(type_id),
            location_id INTEGER REFERENCES locations(location_id) ON DELETE SET NULL,
            CHECK (date(start_date) = start_date),
            CHECK (end_date IS NULL OR date(end_date) = end_date),
            CHECK (end_date IS NULL OR end_date >= start_date)
        )"""
    ),
    step(
        """INSERT INTO tasks_new
           (task_id, description, start_date, end_date, type_id, location_id)
           SELECT task_id, description, start_date, end_date, type_id, location_id
           FROM tasks"""
    ),
    step("DROP TABLE tasks"),
    step("ALTER TABLE tasks_new RENAME TO tasks"),
    step("CREATE INDEX tasks_start_date_idx ON tasks(start_date)"),
    step("CREATE INDEX tasks_end_date_idx ON tasks(end_date)"),
    step("CREATE INDEX tasks_type_id_idx ON tasks(type_id)"),
    step("CREATE INDEX tasks_location_id_idx ON tasks(location_id)"),
]
