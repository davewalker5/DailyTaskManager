"""Application data structures."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class TaskStatus(StrEnum):
    """Derived task status values."""

    OPEN = "Open"
    COMPLETED = "Completed"


@dataclass(frozen=True)
class Location:
    """A named location where tasks can take place."""

    location_id: int
    name: str


@dataclass(frozen=True)
class TaskFilter:
    """Filters accepted by the task browser.

    All fields are optional and are combined with AND semantics. The open-task
    override broadens only the configured start-date range.
    """

    start_from: date | None = None
    start_to: date | None = None
    description: str = ""
    status: TaskStatus | None = None
    type_id: int | None = None
    category_id: int | None = None
    include_open_outside_date_range: bool = False


@dataclass(frozen=True)
class ImportIssue:
    """A validation problem found in one imported CSV row."""

    row_number: int
    message: str


@dataclass(frozen=True)
class ImportResult:
    """Summary returned by a CSV import operation."""

    imported: int
    issues: tuple[ImportIssue, ...]
