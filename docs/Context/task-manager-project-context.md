# Daily Task Manager — Project Context

## Project Overview

Daily Task Manager is a local-first personal task-recording application built with Python, Streamlit, and SQLite.

It supports:

- Recording and completing daily tasks
- Reusing tasks from a task library
- Creating templates containing repeated task occurrences
- Organising tasks by category, type, and location
- Browsing historical tasks
- CSV import and export
- Local and Docker-based deployment

The application is intended for a single user. Authentication, teams, assignments, notifications, priorities, dependencies, and Kanban workflows are outside its scope.

## Technology Stack

- Python 3.13+
- Streamlit
- SQLite
- yoyo-migrations
- pytest
- Ruff
- Docker

Application code is located under:

```text
src/daily_task_manager/
```

Database migrations remain at the project root:

```text
migrations/
```

## Application Pages

### Today

The Today page displays tasks scheduled for the current date.

Each task row provides status-aware actions:

- Close — opens a dialog with a close-date picker defaulting to today
- Reopen — clears the task’s close date
- Delete — opens a confirmation dialog before deletion

Close is unavailable for completed tasks. Reopen is unavailable for open tasks.

The page also provides three expandable sections:

#### Add an ad-hoc task

Creates a task using:

- Description
- Optional location
- Task type
- Start date

#### Add tasks from a template

Requires:

- Task date
- Template

Every task occurrence configured in the selected template is created. A template may contain multiple occurrences of the same pre-defined task.

#### Add task from library

Requires:

- Task date
- Pre-defined task

The new task copies its description, type, category, and location from the library definition.

After tasks are added, the Today table refreshes automatically while retaining the completion message.

### Browse Tasks

Displays tasks matching the selected filters.

Filters include:

- Start date from
- Start date to
- Description
- Status
- Task type
- Category

The date range defaults from seven days ago through today.

Each row provides the same Close, Reopen, and Delete actions used on the Today page.

### Task Library

Maintains reusable pre-defined tasks.

The page uses a table-and-form interaction:

- Select a row using its checkbox to populate the form
- Save creates or updates a task
- Delete removes an unreferenced task
- Clear resets the form and table selection

A pre-defined task contains:

- Description
- Optional location
- Task type

Its category is derived from the selected task type.

A pre-defined task cannot be deleted while referenced by a template or historical task.

### Templates

Maintains reusable daily templates.

The table shows:

- Name
- Description
- Number of task occurrences
- Duplicate action

The form provides:

- Name
- Description
- A quantity for every pre-defined task

Quantities allow a template to contain repeated occurrences of the same task. For example, a laundry template may contain multiple Laundry task occurrences.

Actions are:

- Save
- Delete
- Clear
- Duplicate

Duplicating a template copies its description and ordered task memberships. Copy names use the first available suffix:

```text
Template Name - Copy
Template Name - Copy 2
Template Name - Copy 3
```

### Reference Data

Reference Data contains three tabs:

- Categories
- Task Types
- Locations

Each tab follows the same table-and-form pattern:

- Select a row using its checkbox
- Save creates or updates the record
- Delete removes an unused record
- Clear resets the form and selection

Reference data names are case-insensitively unique.

Deletion is rejected when a record is in use.

### Import

The Import page contains:

- Import-type selector
- Type-specific CSV guidance
- File uploader
- Import button
- Busy cursor and progress spinner
- Persistent completion and row-level validation messages

After a successful import, the selected file is cleared without removing the completion message.

Supported import types are:

#### Historical Tasks

```csv
Start,End,Description,Location,Type,Category
```

Dates use `DD/MM/YY`. End and Location values may be blank.

#### Pre-Defined Tasks

```csv
Description,Location,Type,Category
```

Location may be blank.

#### Templates

```csv
Template,Description,Location,Type,Category
```

Each row associates a pre-defined task with a named template.

The importer:

- Creates missing categories
- Creates missing task types
- Creates missing locations
- Creates missing pre-defined tasks
- Creates missing templates
- Adds missing template-task associations

#### Categories

```csv
Category
```

#### Task Types

```csv
Type,Category
```

Missing parent categories are created automatically.

#### Locations

```csv
Location
```

Imports are case-insensitive and idempotent where the CSV format represents unique records or associations.

CSV templates are stored in:

```text
data/templates/
```

### Export

The Export page contains:

- Export-type selector
- Editable filename
- Export button

Changing the export type resets the filename, even when the user previously edited it.

Default filenames are:

| Export type | Default filename |
|---|---|
| Historical Tasks | `historical-tasks` |
| Pre-Defined Tasks | `pre-defined-tasks` |
| Templates | `templates` |
| Categories | `categories` |
| Task Types | `task-types` |
| Locations | `locations` |

The `.csv` extension is added automatically when omitted.

Exports use the same field layouts as their corresponding imports.

Templates with task memberships produce one row per membership. Repeated task occurrences therefore produce repeated rows.

## Data Model

### `task_categories`

```text
category_id  INTEGER PRIMARY KEY
name         TEXT NOT NULL, case-insensitively unique
```

### `task_types`

```text
type_id      INTEGER PRIMARY KEY
name         TEXT NOT NULL
category_id  INTEGER NOT NULL, references task_categories
```

Task type names are unique within a category.

### `locations`

```text
location_id  INTEGER PRIMARY KEY
name         TEXT NOT NULL, case-insensitively unique
```

### `predefined_tasks`

```text
predefined_task_id  INTEGER PRIMARY KEY
description         TEXT NOT NULL
type_id             INTEGER NOT NULL, references task_types
location_id         INTEGER NULL, references locations
```

Description and task type form a unique definition.

### `daily_templates`

```text
template_id  INTEGER PRIMARY KEY
name         TEXT NOT NULL, case-insensitively unique
description  TEXT NULL
```

### `daily_template_tasks`

```text
template_task_id    INTEGER PRIMARY KEY
template_id         INTEGER NOT NULL, references daily_templates
predefined_task_id  INTEGER NOT NULL, references predefined_tasks
display_order       INTEGER NOT NULL
```

The same pre-defined task may occur multiple times in one template.

### `tasks`

```text
task_id             INTEGER PRIMARY KEY
description         TEXT NOT NULL
start_date          TEXT NOT NULL
end_date            TEXT NULL
type_id             INTEGER NOT NULL, references task_types
predefined_task_id  INTEGER NULL, references predefined_tasks
location_id         INTEGER NULL, references locations
```

Dates are stored as ISO `YYYY-MM-DD` values.

A task is open when `end_date` is null and completed when it contains a date.

When a task is instantiated from the library or a template, its description, type, and location are copied into the historical task. Later edits to the source definition do not change historical records.

Duplicate task descriptions on the same date are permitted.

## Service-Layer Rules

Business operations are implemented by `TaskManager`.

Important rules include:

- Required text is stripped and validated
- Names are resolved case-insensitively
- Completion dates cannot precede start dates
- Referenced records cannot be deleted
- Template memberships preserve task occurrence quantities
- Template-created tasks copy historical values
- CSV imports report invalid rows without silently discarding errors

The UI should call service methods rather than writing SQL directly.

## Database and Migrations

The database defaults to:

```text
data/taskmanager.db
```

It can be overridden using:

```text
DAILY_TASK_MANAGER_DB
```

The runtime root can be overridden using:

```text
DAILY_TASK_MANAGER_ROOT
```

The migration directory is resolved as:

```text
<runtime-root>/migrations
```

Migrations are applied automatically when a database connection is opened.

Migration SQL must remain compatible with the SQLite version supplied by the Docker base image. Schema changes that remove columns use SQLite’s portable create-copy-drop-rename pattern rather than `ALTER TABLE ... DROP COLUMN`.

## Docker Deployment

The Docker runtime uses:

```text
DAILY_TASK_MANAGER_ROOT=/opt/dailytaskmanager
DAILY_TASK_MANAGER_DB=/var/opt/dailytaskmanager/taskmanager.db
```

The Docker build folder must contain:

```text
daily_task_manager-<version>-py3-none-any.whl
streamlit_app.py
migrations/
```

The build script recreates the publish directory before copying these files.

The Dockerfile checks that the application entrypoint and initial migration exist, causing the image build to fail early if either is missing.

Persistent database storage is mounted at:

```text
/var/opt/dailytaskmanager/
```

## Development Commands

Create the virtual environment:

```bash
./scripts/make-venv.sh
```

Run the application:

```bash
venv/bin/streamlit run src/streamlit_app.py
```

Run tests:

```bash
venv/bin/pytest
```

Run lint checks:

```bash
venv/bin/ruff check src tests migrations
```

## Testing Expectations

Changes should normally include tests covering:

- Service-layer business rules
- Database constraints and migrations
- CSV field layouts and round-trip compatibility
- Import idempotency
- Template task quantities
- Delete restrictions
- Streamlit navigation and key UI behavior

All work should pass both pytest and Ruff before delivery.

## Design Principles

### Local First

The application runs without external services or network access.

### Preserve History

Historical task values are copied rather than dynamically inherited from reference records.

### Relational Integrity

Categories, types, locations, pre-defined tasks, templates, and historical tasks are connected using foreign keys.

### Consistent Editing

Task Library, Templates, Categories, Task Types, and Locations use a consistent table-selection and editing-form pattern.

### Portable Data

Every supported import type has a corresponding export format.

### Simple Scope

The application remains a focused personal task recorder rather than a general-purpose project-management system.
