SELECT DISTINCT tt.Name
FROM            TASKS t
INNER JOIN      TASK_TYPES tt ON tt.Type_Id = t.Type_Id
WHERE           t.Location_Id IS NULL
ORDER BY        t.Description ASC;