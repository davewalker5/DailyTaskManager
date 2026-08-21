UPDATE  TASKS
SET     Location_Id = 0
WHERE   Type_ID IN (
        SELECT  Type_ID
        FROM    TASK_TYPES
        WHERE   Name = ''
);
