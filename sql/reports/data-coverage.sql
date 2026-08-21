SELECT
    COUNT(*) AS "Total Tasks",
    MIN(date(t.start_date)) AS "Earliest Start Date",
    MAX(date(t.start_date)) AS "Latest Start Date",
    SUM(CASE WHEN t.location_id IS NULL THEN 1 ELSE 0 END) AS "Tasks Without Location",
    COUNT(DISTINCT t.type_id) AS "Task Types",
    COUNT(DISTINCT tt.category_id) AS "Categories"
FROM tasks AS t
LEFT JOIN task_types AS tt ON tt.type_id = t.type_id;
