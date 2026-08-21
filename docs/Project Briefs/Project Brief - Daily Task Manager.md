# Daily Task Manager

## 1. Purpose

Develop a lightweight personal task-management and activity-recording application to replace the existing spreadsheet-based system.

The application is primarily intended to record tasks undertaken on a particular day, while also providing simple task planning through reusable task definitions and daily templates.

The application should retain the simplicity of the spreadsheet workflow while replacing spreadsheet formulae, validation lists and duplicated data with an appropriate relational data model.

The initial implementation will use **Python, Streamlit and SQLite**.

## 2. Core Concepts

The system distinguishes between:

- **Task Categories** — broad classifications of activity.
- **Task Types** — more specific classifications belonging to a category.
- **Pre-defined Tasks** — reusable definitions of commonly performed tasks.
- **Daily Templates** — collections of pre-defined tasks which can be used to populate a day's task list.
- **Tasks** — actual instances of work recorded against a date.

For example:

**Practical → Cleaning → Maintenance clean the bathroom**

where:

- `Practical` is the category;
- `Cleaning` is the task type;
- `Maintenance clean the bathroom` is the task description.

Task category should therefore be derived through the task type rather than stored redundantly against each task.

## 3. Task Status

Each task has a start date and an optional end date.

Task status is derived from these dates:

- **Open** — `end_date IS NULL`
- **Completed** — `end_date IS NOT NULL`

Status should not be stored separately in the database.

A task may therefore start on one date and remain open until it is completed on a later date.

## 4. Proposed Data Model

### Task Categories

Stores the highest-level task classifications.

Fields:

- `category_id` — primary key
- `name` — unique category name

Examples include `Practical` and `Interests`.

### Task Types

Stores the available task types.

Fields:

- `type_id` — primary key
- `name` — task type name
- `category_id` — foreign key to Task Categories

Each task type belongs to exactly one category.

Examples include `Cleaning`, `Laundry`, `Cooking`, `Household`, `Gardening` and `Wildlife`.

### Pre-defined Tasks

Stores reusable task definitions.

Fields:

- `predefined_task_id` — primary key
- `description`
- `type_id` — foreign key to Task Types

A pre-defined task does not represent work actually undertaken and therefore has no start or end date.

### Daily Templates

Stores named templates from which daily task lists can be created.

Fields:

- `template_id` — primary key
- `name`
- `description` — optional

Although only one standard daily template may initially be required, templates should be explicitly represented in the schema rather than assuming a single hard-coded template.

### Daily Template Tasks

Associates pre-defined tasks with templates.

Fields:

- `template_id` — foreign key to Daily Templates
- `predefined_task_id` — foreign key to Pre-defined Tasks
- `display_order` — optional ordering within the template

The combination of `template_id` and `predefined_task_id` should be unique.

### Tasks

Stores actual task/activity records.

Fields:

- `task_id` — primary key
- `description`
- `start_date`
- `end_date` — nullable
- `type_id` — foreign key to Task Types
- `predefined_task_id` — nullable foreign key to Pre-defined Tasks

`predefined_task_id` records the origin of a task created from the task library/template but is NULL for an ad-hoc task.

The task description and type are copied into the task when it is instantiated. Historical tasks therefore remain unchanged if a pre-defined task is subsequently renamed or reclassified.

Category is not stored on the task because it is available through:

`Task → Task Type → Task Category`

### Database Path

If the environment variable DAILY_TASK_MANAGER_DB is set, it should be used as the path to the database. If not, the following path relative to the root of the project should be used:

```text
data/taskmanager.db
```

### Migrations

Migrations should be managed using yoyo migrations.

## 5. Daily Workflow

### Create a Day's Tasks

The user selects:

- a date;
- a daily template.

The application displays all pre-defined tasks belonging to the selected template.

The user can then:

- select all tasks;
- select individual tasks;
- add the selected tasks to the chosen date.

For each selected item, a new Task record is created with:

- `start_date` set to the selected date;
- `end_date` initially NULL;
- description and task type copied from the pre-defined task.

### Add an Ad-hoc Task

The user can create a task which is not present in the daily template.

By default:

- Start Date = today
- End Date = NULL

The user supplies:

- description;
- task type.

Category is inferred automatically from the selected task type.

### Complete a Task

An open task can be marked completed.

By default, this sets:

`end_date = today`

The completion date should be editable so that tasks can be entered or corrected retrospectively.

A completed task can be reopened by clearing its end date.

## 6. Task Browser

The application should provide a browsable task history.

The browser should support filtering by:

- Start date or date range
- Task description
- Task status
- Task type
- Task category

Task-description searching should use a **case-insensitive substring match**.

For example, searching for:

`dish`

should match:

`Unload the dishwasher`

Tasks should display at least:

- Start Date
- End Date
- Description
- Type
- Category
- Status

Open and completed tasks should be readily distinguishable.

## 7. Administration

The application should provide simple maintenance screens for:

- Task Categories
- Task Types
- Pre-defined Tasks
- Daily Templates

The user should be able to add and edit these records.

Records referenced by other data cannot be deleted, preserving referential integrity and historical reporting.

## 8. CSV Import

### Import Pre-defined Tasks

The application should accept a CSV file containing pre-defined tasks.

At minimum the import format should support:

- Task description
- Task type
- Task category

The importer should resolve the hierarchy:

`Category → Type → Pre-defined Task`

Existing categories and types should be reused rather than duplicated.

### Import Historical Tasks

The application should accept CSV files in the form used by the existing spreadsheet:

| Column | Meaning |
|---|---|
| Start | Start Date |
| End | End Date |
| Achievement | Task Description |
| Type | Task Type |
| Category | Task Category |

Blank End values are imported as NULL.

The importer should create or resolve the corresponding Task Category and Task Type records before importing each task.

Dates from the existing spreadsheet are supplied in UK `DD/MM/YY` format but should be stored internally in SQLite using ISO `YYYY-MM-DD` dates.

The import process should perform validation and report malformed or inconsistent records rather than silently importing them.

## 9. CSV Export

Tasks should be exportable to CSV.

For compatibility with the previous spreadsheet and for easy independent analysis, the exported data should contain:

- Start
- End
- Achievement
- Type
- Category

The export should contain human-readable values rather than database IDs.

Export should respect the current task-browser filters where practical, allowing either the complete task history or a selected subset to be exported.

## 10. Design Principles

### Simple

The application is a personal task recorder, not a general-purpose project-management system.

Features such as users, teams, assignments, dependencies, priorities, notifications and Kanban boards are outside the initial scope.

### Relational

Information should have a single authoritative location.

In particular, the spreadsheet relationship:

`Type → VLOOKUP → Category`

becomes a proper relational relationship:

`task_types.category_id → task_categories.category_id`

### Preserve History

Changes to templates and pre-defined tasks must not retrospectively alter the historical task record.

### Portable

SQLite should contain the complete application database and require no external database server.

CSV import/export provides a simple mechanism for migration, backup and independent analysis.

### Local First

The initial application is intended to run locally and does not require authentication, cloud services or an Internet connection.

## 11. Initial Streamlit Application Structure

A suitable initial navigation structure is:

**Today**

View today's tasks, add ad-hoc tasks, complete/reopen tasks and add tasks from a template.

**Add from Template**

Choose a date and template, select some or all template tasks and instantiate them.

**Browse Tasks**

Search and filter historical and open tasks.

**Task Library**

Maintain pre-defined tasks.

**Templates**

Create and maintain daily templates.

**Types & Categories**

Maintain the task classification hierarchy.

**Import / Export**

Import existing spreadsheet/task data and pre-defined tasks; export task history.

## 12. Initial Scope / MVP

The first usable version should provide:

1. SQLite database creation and schema.
2. Category and task-type maintenance.
3. Pre-defined task library.
4. Daily template maintenance.
5. Creation of a day's tasks from a template.
6. Creation of ad-hoc tasks.
7. Completion and reopening of tasks.
8. Task browsing and filtering.
9. Import of the existing spreadsheet CSV format.
10. CSV export.

Once these functions are working, additional features should be driven by actual use rather than attempting to anticipate the requirements of a larger task-management system.

All code should be in accordance with the project coding standards in:

```text
docs/Project Briefs/Project Coding Standards.md
```
