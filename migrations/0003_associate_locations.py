"""Associate tasks and pre-defined tasks with optional locations."""

from yoyo import step

steps = [
    step(
        """ALTER TABLE predefined_tasks
           ADD COLUMN location_id INTEGER REFERENCES locations(location_id) ON DELETE SET NULL""",
    ),
    step(
        """ALTER TABLE tasks
           ADD COLUMN location_id INTEGER REFERENCES locations(location_id) ON DELETE SET NULL""",
    ),
    step(
        "CREATE INDEX predefined_tasks_location_id_idx ON predefined_tasks(location_id)",
        "DROP INDEX predefined_tasks_location_id_idx",
    ),
    step(
        "CREATE INDEX tasks_location_id_idx ON tasks(location_id)",
        "DROP INDEX tasks_location_id_idx",
    ),
]
