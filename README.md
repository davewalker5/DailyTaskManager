[![GitHub issues](https://img.shields.io/github/issues/davewalker5/DailyTaskManager)](https://github.com/davewalker5/DailyTaskManager/issues)
[![Releases](https://img.shields.io/github/v/release/davewalker5/DailyTaskManager.svg?include_prereleases)](https://github.com/davewalker5/DailyTaskManager/releases)
[![License](https://img.shields.io/badge/License-mit-blue.svg)](https://github.com/davewalker5/DailyTaskManager/blob/main/LICENSE)
[![Language](https://img.shields.io/badge/language-python-blue.svg)](https://www.python.org)
[![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/davewalker5/DailyTaskManager)](https://github.com/davewalker5/DailyTaskManager/)

# Daily Task Manager

## Overview

Daily Task Manager is a local-first application for recording, organising and reviewing personal daily tasks.

Built with Python, Streamlit and SQLite, it provides a focused workflow for creating tasks, marking them as complete, reusing common task definitions and browsing task history. Task data is stored locally and database migrations are applied automatically when the application starts.

The application is intended for a single user and can be run locally or in Docker. It does not require an external database, cloud service or Internet connection.

## Daily Task Tracking

### Today

The Today page displays tasks whose start date is today. Tasks are ordered by start date and description and can be:

- Closed using a selected completion date
- Reopened by clearing their completion date
- Deleted after confirmation

New tasks can be added individually, selected from the task library or created together from a reusable template.

An ad-hoc task records:

- Description
- Start date
- Task type and its associated category
- Optional location

### Browse Tasks

Browse current and historical tasks using filters for:

- Start-date range
- Description
- Open or completed status
- Task type
- Category

The same close, reopen and delete actions available on the Today page can be applied from the filtered results.

## Reusable Tasks and Templates

### Task Library

The Task Library stores pre-defined tasks that can be added without repeatedly entering the same details. Each definition contains a description, task type and optional location; its category is inherited from the selected task type.

When a library task is added to a date, its current values are copied into the task history. Later changes to the library definition do not alter existing historical tasks.

### Daily Templates

Templates group task-library entries into reusable daily routines. A template can contain any number of task occurrences, including repeated occurrences of the same task.

Templates can be created, edited, duplicated and deleted. Adding a template to a date creates a separate historical task for every occurrence configured in that template.

## Task Organisation

Tasks are organised using three sets of reference data:

- Categories provide the top-level classification
- Task types belong to a category
- Locations optionally record where a task takes place

The Reference Data page maintains these values. Names are matched case-insensitively, and records that are already in use cannot be deleted.

A task is considered open while it has no end date and completed once an end date has been recorded. Completion dates cannot be earlier than the task's start date.

## Data Exchange

### CSV Import

Import data from CSV files for:

- Historical tasks
- Pre-defined tasks
- Templates
- Categories
- Task types
- Locations

Historical-task dates use `DD/MM/YY`. Location and task end date may be left blank where the selected format permits them.

Template imports contain one row for each task occurrence associated with a template. During import, missing categories, task types, locations, pre-defined tasks and templates are created as required. Invalid rows are reported individually so that valid records can still be imported.

Ready-to-use CSV layouts are provided in [`data/templates`](data/templates).

### CSV Export

Export the same six datasets using CSV layouts compatible with the corresponding import formats. Default filenames are supplied and can be edited before downloading.

Historical-task exports can optionally be filtered inclusively by task start date. The default range runs from the beginning of the current year through today.

CSV export provides a portable copy of task data for backup, migration, spreadsheet use or independent analysis.

## Project Scope

Daily Task Manager is deliberately designed as a simple personal task recorder rather than a general-purpose project-management platform.

Its scope includes:

- Recording, completing, reopening and deleting daily tasks
- Maintaining reusable task definitions and daily templates
- Organising tasks by category, type and location
- Searching and filtering task history
- Importing and exporting portable CSV data
- Local and Docker-based deployment

Authentication, multiple users, teams, assignments, priorities, dependencies, reminders, notifications and Kanban workflows are outside the current scope. New functionality is intended to be driven by practical personal use while preserving the application's local-first design and straightforward data model.

## Feedback

To report an issue or suggest an improvement, please use the project's [GitHub Issues](https://github.com/davewalker5/DailyTaskManager/issues) page.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
