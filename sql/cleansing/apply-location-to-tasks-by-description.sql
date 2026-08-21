UPDATE  TASKS
SET     Location_Id = 0
WHERE   Description LIKE '%'
AND     Location_ID IS NULL;
