# Task Reporting and Analysis

The six numbered notebooks in `reports/notebooks` implement the initial reporting brief. They read the
application's SQLite database, filter tasks by **start date**, show both exact tables and complementary
charts, and export each notebook's report datasets to an XLSX workbook in `data/reports`.

## Running the reports

Set `DAILY_TASK_MANAGER_DB` to the database to analyse and `PROJECT_ROOT` to this repository, then run a
notebook interactively or use `reports/scripts/run-all.sh`. Each notebook contains `START_DATE`,
`END_DATE`, and `REPORT_DATE` parameters near the top. Defaults cover all SQLite dates and use today's
date for open-task ages. `REPORT_OUTPUT_FOLDER` can override the export destination.

The reporting period is inclusive and applies to task start date. Completion activity can therefore
include completion dates outside that period for tasks which started within it. Open-task age is status
analysis, not an overdue or performance measure. Missing locations are displayed as `Not recorded`.

## Reports

1. **Overview** — reporting-period context and headline task, completion, and coverage measures.
2. **Categories and Task Types** — ranked activity and completion summaries.
3. **Activity Over Time** — monthly starts, completions, status composition, and category trends.
4. **Completion and Open Tasks** — completion rates, elapsed completion time, and open-task age.
5. **Patterns** — Monday-to-Sunday and optional-location patterns.
6. **Data Quality** — full-dataset coverage, missing locations, and unmapped reference checks.

Completion percentage is completed tasks divided by all tasks in the relevant group. Elapsed days are
calendar days from start through completion; same-day completions therefore have a value of zero. Open
tasks never receive an elapsed completion duration.
