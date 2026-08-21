"""Add locations."""

from yoyo import step

steps = [
    step(
        """CREATE TABLE locations (
            location_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE
        )""",
        "DROP TABLE locations",
    )
]
