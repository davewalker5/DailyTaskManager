"""Descriptive activity measures shared by the extended reporting notebooks."""

from dataclasses import dataclass

import pandas as pd

TYPE_COLUMNS = ["Category", "Task Type"]
AGE_BANDS = ["0–7 days", "8–30 days", "31–90 days", "91+ days"]


@dataclass(frozen=True)
class ReportPeriod:
    """Inclusive calendar dates and optional exact-match history filters."""

    start_date: str
    end_date: str
    category: str | None = None
    task_type: str | None = None
    location: str | None = None

    def __post_init__(self) -> None:
        """Validate finite, ordered dates before any query or calculation."""
        for value in (self.start_date, self.end_date):
            timestamp = pd.Timestamp(value)
            if pd.isna(timestamp) or timestamp.tzinfo or timestamp != timestamp.normalize():
                raise ValueError("Reporting dates must be finite timezone-naive calendar dates")
        if self.start > self.end:
            raise ValueError("start_date must not follow end_date")

    @property
    def start(self) -> pd.Timestamp:
        """Return the inclusive first reporting date."""
        return pd.Timestamp(self.start_date)

    @property
    def end(self) -> pd.Timestamp:
        """Return the inclusive final reporting date (also the as-of date)."""
        return pd.Timestamp(self.end_date)


def filter_history(data: pd.DataFrame, period: ReportPeriod) -> pd.DataFrame:
    """Prepare history through the as-of date, retaining pre-period observations.

    :param data: Rows returned by task-history.sql.
    :param period: Reporting bounds and exact-match dimension filters.
    :return: Independent frame with normalised calendar dates.
    :raises ValueError: If dates are missing or completion precedes start.
    """
    result = data.copy()
    for column in ("Start Date", "Completion Date"):
        result[column] = pd.to_datetime(result[column], errors="raise").dt.normalize()
    if result["Start Date"].isna().any():
        raise ValueError("Task start dates must be recorded")
    if (result["Completion Date"] < result["Start Date"]).any():
        raise ValueError("Completion dates must not precede start dates")
    result = result.loc[result["Start Date"].le(period.end)]
    for column, value in (
        ("Category", period.category),
        ("Task Type", period.task_type),
        ("Location", period.location),
    ):
        if value is not None:
            result = result.loc[result[column].eq(value)]
    return result.copy()


def period_tasks(history: pd.DataFrame, period: ReportPeriod) -> pd.DataFrame:
    """Select starts in the period without mutating history.

    :param history: Prepared history including earlier observations.
    :param period: Inclusive reporting bounds.
    :return: Period task cohort.
    """
    return history.loc[history["Start Date"].between(period.start, period.end)].copy()


def monthly_profile(
    history: pd.DataFrame, period: ReportPeriod
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Count monthly diversity and category shares, including months without starts.

    :param history: Prepared, dimension-filtered history.
    :param period: Inclusive reporting bounds.
    :return: Diversity table and category percentage table. Empty months have undefined shares.
    """
    tasks = period_tasks(history, period)
    tasks["Month"] = tasks["Start Date"].dt.to_period("M").dt.to_timestamp()
    months = pd.date_range(period.start.replace(day=1), period.end.replace(day=1), freq="MS")
    grouped = tasks.groupby("Month")
    diversity = (
        grouped.agg(
            **{
                "Active Categories": ("Category", "nunique"),
                "Tasks Started": ("Task ID", "size"),
            }
        )
        .reindex(months, fill_value=0)
        .rename_axis("Month")
    )
    # Type names are unique within a category, not across the whole database.
    diversity["Distinct Task Types"] = (
        tasks.drop_duplicates(["Month", *TYPE_COLUMNS])
        .groupby("Month")
        .size()
        .reindex(months, fill_value=0)
    )
    counts = pd.crosstab(tasks["Month"], tasks["Category"]).reindex(months, fill_value=0)
    mix = counts.div(counts.sum(axis=1).replace(0, float("nan")), axis=0).mul(100)
    return diversity.reset_index(), mix.rename_axis("Month").reset_index()


def active_days(history: pd.DataFrame, period: ReportPeriod) -> pd.DataFrame:
    """Count distinct start dates per task type, with a calendar-day denominator.

    :param history: Prepared history.
    :param period: Inclusive reporting bounds, including partial months if selected.
    :return: Active-day counts and percentages for every previously observed type.
    """
    types = history[TYPE_COLUMNS].drop_duplicates()
    counts = period_tasks(history, period).groupby(TYPE_COLUMNS)["Start Date"].nunique()
    result = types.merge(counts.rename("Active Days"), on=TYPE_COLUMNS, how="left").fillna(0)
    result["Active Days"] = result["Active Days"].astype(int)
    result["Days in Period"] = (period.end - period.start).days + 1
    result["Percentage of Days Active"] = result["Active Days"] / result["Days in Period"] * 100
    return result.sort_values("Active Days", ascending=False).reset_index(drop=True)


def rolling_profile(history: pd.DataFrame, period: ReportPeriod, window: int = 90) -> pd.DataFrame:
    """Calculate trailing calendar-day activity, including the displayed date.

    :param history: All observed history through the reporting end date.
    :param period: Dates to display; earlier history supplies window context.
    :param window: Positive number of calendar days in each window.
    :return: Daily tasks, active days and type diversity for the filtered activity.
    :raises ValueError: If the window is not a positive integer.
    """
    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        raise ValueError("rolling_window must be a positive integer")
    dates = pd.date_range(period.start - pd.Timedelta(days=window - 1), period.end)
    daily = history.groupby("Start Date").size().reindex(dates, fill_value=0)
    result = pd.DataFrame(
        {
            "Tasks": daily.rolling(window, min_periods=window).sum(),
            "Active Days": daily.gt(0).rolling(window, min_periods=window).sum(),
        }
    )
    type_days = pd.crosstab(
        history["Start Date"], [history[column] for column in TYPE_COLUMNS]
    ).reindex(dates, fill_value=0)
    result["Distinct Task Types"] = (
        type_days.rolling(window, min_periods=window).sum().gt(0).sum(axis=1)
    )
    return result.loc[period.start :].rename_axis("Date").reset_index()


def yearly_comparison(history: pd.DataFrame, period: ReportPeriod) -> pd.DataFrame:
    """Compare month-of-year active days, marking partial months explicitly.

    :param history: Prepared history, optionally filtered to a selected activity.
    :param period: Inclusive bounds; dates outside these bounds are not extrapolated.
    :return: Year/month rows with actual exposure and active-day percentages.
    """
    dates = pd.Series(pd.date_range(period.start, period.end), name="Date")
    calendar = pd.DataFrame({"Year": dates.dt.year, "Month": dates.dt.month})
    calendar["Active"] = dates.isin(period_tasks(history, period)["Start Date"])
    result = (
        calendar.groupby(["Year", "Month"])
        .agg(**{"Active Days": ("Active", "sum"), "Observed Days": ("Active", "size")})
        .reset_index()
    )
    month_dates = pd.to_datetime(dict(year=result["Year"], month=result["Month"], day=1))
    result["Partial Month"] = result["Observed Days"].ne(month_dates.dt.days_in_month)
    result["Percentage of Days Active"] = result["Active Days"] / result["Observed Days"] * 100
    return result


def activity_continuity(
    history: pd.DataFrame,
    period: ReportPeriod,
    dormancy_threshold: int = 90,
) -> pd.DataFrame:
    """Describe status and gaps from recorded start dates, without inferring causes.

    :param history: Full prepared history; first occurrence means first recorded occurrence.
    :param period: Reporting bounds and as-of date.
    :param dormancy_threshold: Positive absence length in days; equality meets threshold.
    :return: Status, previous/latest activity, and observed inter-activity gap statistics.
    :raises ValueError: If the threshold is not a positive integer.
    """
    if (
        isinstance(dormancy_threshold, bool)
        or not isinstance(dormancy_threshold, int)
        or dormancy_threshold <= 0
    ):
        raise ValueError("dormancy_threshold must be a positive integer")
    columns = [
        *TYPE_COLUMNS,
        "Status",
        "First Activity",
        "Previous Activity",
        "Latest Activity",
        "Days Since Last Activity",
        "Longest Gap (Days)",
        "Median Gap (Days)",
    ]
    rows = []
    for keys, group in history.groupby(TYPE_COLUMNS):
        dates = group["Start Date"].drop_duplicates().sort_values()
        current = dates.loc[dates.ge(period.start)]
        previous = dates.loc[dates.lt(period.start)]
        gaps = dates.diff().dt.days
        current_gap = (period.end - dates.iloc[-1]).days
        # Dormant takes precedence at period end; established means at least two active dates.
        if current_gap >= dormancy_threshold and len(dates) >= 2:
            status = "Dormant"
        elif dates.iloc[0] >= period.start:
            status = "New"
        elif not current.empty and gaps.loc[current.index].ge(dormancy_threshold).any():
            status = "Resumed"
        elif not current.empty:
            status = "Active"
        else:
            status = "Not active in period"
        # Gap summaries use complete intervals with both endpoints inside the period.
        period_gaps = current.diff().dt.days.dropna()
        rows.append(
            [
                *keys,
                status,
                dates.iloc[0],
                previous.max(),
                dates.iloc[-1],
                current_gap,
                period_gaps.max(),
                period_gaps.median(),
            ]
        )
    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values("Days Since Last Activity", ascending=False)
        .reset_index(drop=True)
    )


def completion_by_type(history: pd.DataFrame, period: ReportPeriod) -> pd.DataFrame:
    """Summarise elapsed calendar days for period starts completed by the as-of date.

    :param history: Prepared history.
    :param period: Inclusive start-date cohort and completion cutoff.
    :return: Counts, median, mean, p90, maximum and same-day percentage per task type.
    """
    tasks = period_tasks(history, period)
    tasks = tasks.loc[tasks["Completion Date"].le(period.end)].copy()
    tasks["Days"] = (tasks["Completion Date"] - tasks["Start Date"]).dt.days
    result = tasks.groupby(TYPE_COLUMNS)["Days"].agg(
        **{
            "Completed Tasks": "size",
            "Median Days": "median",
            "Mean Days": "mean",
            "Maximum Days": "max",
        }
    )
    result["90th Percentile Days"] = tasks.groupby(TYPE_COLUMNS)["Days"].quantile(0.9)
    same_day = tasks.assign(Same=tasks["Days"].eq(0)).groupby(TYPE_COLUMNS)["Same"].mean()
    result["Same Day Percentage"] = same_day * 100
    return result.reset_index()


def backlog_by_age(
    history: pd.DataFrame, period: ReportPeriod, by_type: bool = False
) -> pd.DataFrame:
    """Count all outstanding tasks at period end, including starts before the period.

    :param history: Prepared history through the as-of date.
    :param period: Supplies the as-of date; the start bound does not truncate backlog.
    :param by_type: Include task type as well as category in grouping.
    :return: Table with all four age bands, including zero counts.
    """
    tasks = history.loc[
        history["Completion Date"].isna() | history["Completion Date"].gt(period.end)
    ].copy()
    tasks["Age Band"] = pd.cut(
        (period.end - tasks["Start Date"]).dt.days,
        bins=[-1, 7, 30, 90, float("inf")],
        labels=AGE_BANDS,
    )
    groups = TYPE_COLUMNS if by_type else ["Category"]
    result = tasks.groupby([*groups, "Age Band"], observed=True).size().unstack("Age Band")
    return result.reindex(columns=AGE_BANDS, fill_value=0).fillna(0).astype(int).reset_index()
