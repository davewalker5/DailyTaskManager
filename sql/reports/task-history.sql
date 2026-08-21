SELECT
    t.task_id AS "Task ID",
    t.description AS "Description",
    date(t.start_date) AS "Start Date",
    date(t.end_date) AS "Completion Date",
    CASE WHEN t.end_date IS NULL THEN 'Open' ELSE 'Completed' END AS "Status",
    tt.name AS "Task Type",
    tc.name AS "Category",
    COALESCE(l.name, 'Not recorded') AS "Location",
    CASE WHEN l.location_id IS NULL THEN 0 ELSE 1 END AS "Has Location",
    CASE WHEN t.end_date IS NULL THEN NULL
         ELSE CAST(julianday(t.end_date) - julianday(t.start_date) AS INTEGER)
    END AS "Elapsed Days"
FROM tasks AS t
JOIN task_types AS tt ON tt.type_id = t.type_id
JOIN task_categories AS tc ON tc.category_id = tt.category_id
LEFT JOIN locations AS l ON l.location_id = t.location_id
WHERE date(t.start_date) BETWEEN date('$START-DATE') AND date('$END-DATE')
ORDER BY date(t.start_date), t.task_id;
