"""Reusable calculations and presentation helpers for reporting notebooks."""

from __future__ import annotations

from datetime import date

import pandas as pd

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def normalise_history(data: pd.DataFrame) -> pd.DataFrame:
    """Return task history with consistent date and derived time columns."""
    result = data.copy()
    for column in ("Start Date", "Completion Date"):
        result[column] = pd.to_datetime(result[column], errors="coerce")
    result["Start Month"] = result["Start Date"].dt.to_period("M").dt.to_timestamp()
    result["Completion Month"] = result["Completion Date"].dt.to_period("M").dt.to_timestamp()
    result["Start Day"] = pd.Categorical(
        result["Start Date"].dt.day_name(), categories=DAY_ORDER, ordered=True
    )
    return result


def percentage(numerator: pd.Series | int, denominator: pd.Series | int):
    """Calculate a percentage, returning zero when the denominator is zero."""
    if isinstance(denominator, pd.Series):
        return numerator.div(denominator.where(denominator.ne(0))).mul(100).fillna(0).round(1)
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def summary(data: pd.DataFrame) -> pd.DataFrame:
    """Build the headline summary for a filtered history dataset."""
    total = len(data)
    completed = int(data["Completion Date"].notna().sum())
    return pd.DataFrame([{
        "Total Tasks": total,
        "Completed Tasks": completed,
        "Open Tasks": total - completed,
        "Completion Percentage": percentage(completed, total),
        "Categories": data["Category"].nunique(),
        "Task Types": data["Task Type"].nunique(),
        "Recorded Locations": data.loc[data["Has Location"].eq(1), "Location"].nunique(),
    }])


def grouped_summary(data: pd.DataFrame, columns: str | list[str]) -> pd.DataFrame:
    """Summarise task volume and completion for one or more dimensions."""
    groups = [columns] if isinstance(columns, str) else columns
    result = data.groupby(groups, observed=True, dropna=False).agg(
        **{"Task Count": ("Task ID", "count"), "Completed Tasks": ("Completion Date", "count")}
    ).reset_index()
    result["Open Tasks"] = result["Task Count"] - result["Completed Tasks"]
    result["Percentage of Tasks"] = percentage(result["Task Count"], len(data))
    result["Completion Percentage"] = percentage(result["Completed Tasks"], result["Task Count"])
    return result.sort_values(["Task Count", *groups], ascending=[False] + [True] * len(groups))


def monthly_activity(data: pd.DataFrame) -> pd.DataFrame:
    """Return started, completed, and start-month status counts."""
    started = data.groupby("Start Month").size().rename("Tasks Started")
    completed = (
        data.dropna(subset=["Completion Month"])
        .groupby("Completion Month")
        .size()
        .rename("Tasks Completed")
    )
    status = data.pivot_table(
        index="Start Month",
        columns="Status",
        values="Task ID",
        aggfunc="count",
        fill_value=0,
    )
    result = (
        pd.concat([started, completed, status], axis=1)
        .fillna(0)
        .astype(int)
        .reset_index()
    )
    return result.rename(columns={result.columns[0]: "Month"})


def open_task_analysis(data: pd.DataFrame, report_date: date) -> pd.DataFrame:
    """Return open tasks with exact age and useful, non-overdue age bands."""
    result = data[data["Completion Date"].isna()].copy()
    result["Age (Days)"] = (pd.Timestamp(report_date) - result["Start Date"]).dt.days
    result["Age Band"] = pd.cut(
        result["Age (Days)"], bins=[-float("inf"), 7, 30, 90, float("inf")],
        labels=["0–7 days", "8–30 days", "31–90 days", "91+ days"]
    )
    return result
