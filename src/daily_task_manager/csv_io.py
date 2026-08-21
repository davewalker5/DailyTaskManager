"""Validated import and export of the application's CSV formats."""

import csv
import io
from collections.abc import Callable
from datetime import date, datetime

from daily_task_manager.models import ImportIssue, ImportResult, TaskFilter
from daily_task_manager.service import TaskManager

HISTORICAL_IMPORT_COLUMNS = ("Start", "End", "Description", "Type", "Category")
HISTORICAL_EXPORT_COLUMNS = ("Start", "End", "Description", "Location", "Type", "Category")
TEMPLATE_IMPORT_COLUMNS = ("Template", "Description", "Location", "Type", "Category")
CATEGORY_IMPORT_COLUMNS = ("Category",)
TYPE_IMPORT_COLUMNS = ("Type", "Category")
LOCATION_IMPORT_COLUMNS = ("Location",)
PREDEFINED_ALIASES = {
    "description": ("Description", "Task description", "Achievement"),
    "location": ("Location",),
    "type": ("Type", "Task type"),
    "category": ("Category", "Task category"),
}
UK_DATE_FORMAT = "%d/%m/%y"


def _read_rows(content: bytes) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    """Decode CSV bytes and return normalised dictionary rows.

    :param content: Uploaded CSV bytes.
    :return: Rows and source field names.
    :raises ValueError: If the content is not valid UTF-8 or has no header.
    """
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("CSV must be UTF-8 encoded") from error
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV must contain a header row")
    fieldnames = tuple(name.strip() for name in reader.fieldnames if name is not None)
    rows = [
        {(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in reader
    ]
    return rows, fieldnames


def _parse_uk_date(value: str, field_name: str, required: bool = True) -> date | None:
    """Parse the legacy spreadsheet's UK short-date format.

    :param value: Date text.
    :param field_name: Name used in validation errors.
    :param required: Whether a blank value is invalid.
    :return: Parsed date or none for an allowed blank.
    :raises ValueError: If required or malformed.
    """
    if not value:
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    try:
        return datetime.strptime(value, UK_DATE_FORMAT).date()
    except ValueError as error:
        raise ValueError(f"{field_name} must use DD/MM/YY format") from error


def import_historical_tasks(content: bytes, manager: TaskManager) -> ImportResult:
    """Validate and import legacy spreadsheet task rows.

    Valid rows are imported; invalid rows are reported with source row numbers.

    :param content: CSV file bytes.
    :param manager: Destination task service.
    :return: Import count and validation issues.
    :raises ValueError: If required columns are absent.
    """
    rows, fieldnames = _read_rows(content)
    missing = set(HISTORICAL_IMPORT_COLUMNS) - set(fieldnames)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    issues: list[ImportIssue] = []
    imported = 0
    for row_number, row in enumerate(rows, start=2):
        try:
            description = row["Description"].strip()
            if not description:
                raise ValueError("Description is required")
            start_date = _parse_uk_date(row["Start"], "Start")
            end_date = _parse_uk_date(row["End"], "End", required=False)
            assert start_date is not None
            if end_date is not None and end_date < start_date:
                raise ValueError("End cannot be before Start")
            type_id = manager.resolve_category_and_type(row["Category"], row["Type"])
            location_id = manager.resolve_location(row.get("Location", ""))
            imported += manager.add_imported_tasks(
                [(description, start_date, end_date, type_id, location_id)]
            )
        except (ValueError, KeyError) as error:
            issues.append(ImportIssue(row_number, str(error)))
    return ImportResult(imported, tuple(issues))


def _resolve_alias(fieldnames: tuple[str, ...], aliases: tuple[str, ...]) -> str | None:
    """Find the first accepted import heading present in a file.

    :param fieldnames: Source CSV headings.
    :param aliases: Accepted alternatives in priority order.
    :return: Matching source heading, if present.
    """
    lookup = {field.casefold(): field for field in fieldnames}
    return next((lookup[alias.casefold()] for alias in aliases if alias.casefold() in lookup), None)


def import_predefined_tasks(content: bytes, manager: TaskManager) -> ImportResult:
    """Import reusable tasks while resolving and reusing their hierarchy.

    :param content: CSV file bytes.
    :param manager: Destination task service.
    :return: Count of newly created definitions and row issues.
    :raises ValueError: If a required logical column is absent.
    """
    rows, fieldnames = _read_rows(content)
    columns = {
        logical_name: _resolve_alias(fieldnames, aliases)
        for logical_name, aliases in PREDEFINED_ALIASES.items()
    }
    missing = [
        name for name, source in columns.items() if name != "location" and source is None
    ]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    issues: list[ImportIssue] = []
    imported = 0
    for row_number, row in enumerate(rows, start=2):
        try:
            description = row[columns["description"] or ""]
            type_id = manager.resolve_category_and_type(
                row[columns["category"] or ""], row[columns["type"] or ""]
            )
            location_column = columns["location"]
            location_id = manager.resolve_location(row[location_column] if location_column else "")
            if manager.ensure_predefined_task(description, type_id, location_id):
                imported += 1
        except (ValueError, KeyError) as error:
            issues.append(ImportIssue(row_number, str(error)))
    return ImportResult(imported, tuple(issues))


def import_templates(content: bytes, manager: TaskManager) -> ImportResult:
    """Import template memberships while resolving all referenced records.

    :param content: CSV file bytes.
    :param manager: Destination task service.
    :return: Count of new template-task associations and row issues.
    :raises ValueError: If a required column is absent.
    """
    rows, fieldnames = _read_rows(content)
    missing = set(TEMPLATE_IMPORT_COLUMNS) - set(fieldnames)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    issues: list[ImportIssue] = []
    imported = 0
    for row_number, row in enumerate(rows, start=2):
        try:
            type_id = manager.resolve_category_and_type(row["Category"], row["Type"])
            location_id = manager.resolve_location(row["Location"])
            if manager.ensure_template_task(
                row["Template"], row["Description"], type_id, location_id
            ):
                imported += 1
        except (ValueError, KeyError) as error:
            issues.append(ImportIssue(row_number, str(error)))
    return ImportResult(imported, tuple(issues))


def _import_reference_data(
    content: bytes,
    manager: TaskManager,
    columns: tuple[str, ...],
    ensure: Callable[..., bool],
) -> ImportResult:
    """Import an idempotent reference-data CSV format.

    :param content: CSV file bytes.
    :param manager: Destination task service.
    :param columns: Required source columns in argument order.
    :param ensure: Callable that creates one reference record if missing.
    :return: Count of new records and row issues.
    """
    rows, fieldnames = _read_rows(content)
    missing = set(columns) - set(fieldnames)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    issues: list[ImportIssue] = []
    imported = 0
    for row_number, row in enumerate(rows, start=2):
        try:
            if ensure(*(row[column] for column in columns)):
                imported += 1
        except (ValueError, KeyError) as error:
            issues.append(ImportIssue(row_number, str(error)))
    return ImportResult(imported, tuple(issues))


def import_categories(content: bytes, manager: TaskManager) -> ImportResult:
    """Import categories by name."""
    return _import_reference_data(
        content, manager, CATEGORY_IMPORT_COLUMNS, manager.ensure_category
    )


def import_types(content: bytes, manager: TaskManager) -> ImportResult:
    """Import task types and resolve their parent categories."""
    return _import_reference_data(content, manager, TYPE_IMPORT_COLUMNS, manager.ensure_type)


def import_locations(content: bytes, manager: TaskManager) -> ImportResult:
    """Import locations by name."""
    return _import_reference_data(
        content, manager, LOCATION_IMPORT_COLUMNS, manager.ensure_location
    )


def export_tasks(
    manager: TaskManager,
    start_from: date | None = None,
    start_to: date | None = None,
) -> bytes:
    """Export tasks in the historical-task import format.

    :param manager: Source task service.
    :param start_from: Optional inclusive earliest start date.
    :param start_to: Optional inclusive latest start date.
    :return: UTF-8 CSV bytes.
    """
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=HISTORICAL_EXPORT_COLUMNS)
    writer.writeheader()
    for task in manager.list_tasks(TaskFilter(start_from=start_from, start_to=start_to)):
        writer.writerow(
            {
                "Start": date.fromisoformat(task["start_date"]).strftime(UK_DATE_FORMAT),
                "End": (
                    date.fromisoformat(task["end_date"]).strftime(UK_DATE_FORMAT)
                    if task["end_date"]
                    else ""
                ),
                "Description": task["description"],
                "Location": task["location_name"] or "",
                "Type": task["type_name"],
                "Category": task["category_name"],
            }
        )
    return output.getvalue().encode("utf-8")


def _write_csv(columns: tuple[str, ...], rows: list[dict[str, object]]) -> bytes:
    """Encode dictionaries as a UTF-8 CSV with a stable column order."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def export_predefined_tasks(manager: TaskManager) -> bytes:
    """Export reusable tasks in their import format."""
    return _write_csv(
        ("Description", "Location", "Type", "Category"),
        [
            {
                "Description": row["description"],
                "Location": row["location_name"] or "",
                "Type": row["type_name"],
                "Category": row["category_name"],
            }
            for row in manager.list_predefined_tasks()
        ],
    )


def export_templates(manager: TaskManager) -> bytes:
    """Export template memberships in their import format."""
    rows: list[dict[str, object]] = []
    for template in manager.list_templates():
        rows.extend(
            {
                "Template": template["name"],
                "Description": task["description"],
                "Location": task["location_name"] or "",
                "Type": task["type_name"],
                "Category": task["category_name"],
            }
            for task in manager.get_template_tasks(template["template_id"])
        )
    return _write_csv(TEMPLATE_IMPORT_COLUMNS, rows)


def export_categories(manager: TaskManager) -> bytes:
    """Export categories in their import format."""
    return _write_csv(
        CATEGORY_IMPORT_COLUMNS,
        [{"Category": row["name"]} for row in manager.list_categories()],
    )


def export_types(manager: TaskManager) -> bytes:
    """Export task types in their import format."""
    return _write_csv(
        TYPE_IMPORT_COLUMNS,
        [
            {"Type": row["name"], "Category": row["category_name"]}
            for row in manager.list_types()
        ],
    )


def export_locations(manager: TaskManager) -> bytes:
    """Export locations in their import format."""
    return _write_csv(
        LOCATION_IMPORT_COLUMNS,
        [{"Location": row["name"]} for row in manager.list_locations()],
    )
