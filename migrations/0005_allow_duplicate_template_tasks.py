"""Allow repeated pre-defined tasks within a daily template."""

from yoyo import step

steps = [
    step(
        """CREATE TABLE daily_template_tasks_new (
            template_task_id INTEGER PRIMARY KEY,
            template_id INTEGER NOT NULL REFERENCES daily_templates(template_id),
            predefined_task_id INTEGER NOT NULL REFERENCES predefined_tasks(predefined_task_id),
            display_order INTEGER NOT NULL
        )"""
    ),
    step(
        """INSERT INTO daily_template_tasks_new
           (template_id, predefined_task_id, display_order)
           SELECT template_id, predefined_task_id, display_order FROM daily_template_tasks"""
    ),
    step("DROP TABLE daily_template_tasks"),
    step("ALTER TABLE daily_template_tasks_new RENAME TO daily_template_tasks"),
    step(
        "CREATE INDEX daily_template_tasks_template_id_idx ON daily_template_tasks(template_id)"
    ),
    step(
        """CREATE INDEX daily_template_tasks_predefined_task_id_idx
           ON daily_template_tasks(predefined_task_id)"""
    ),
]
