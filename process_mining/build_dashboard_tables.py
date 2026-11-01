"""Build flat, Power BI-ready tables from the clinical event log."""

import argparse
from pathlib import Path
from typing import Callable

import pandas as pd

if __package__:
    from .process_discovery import read_event_log
else:
    from process_discovery import read_event_log


REQUIRED_COLUMNS = ("case_id", "activity", "timestamp")
TABLE_COLUMNS = {
    "process_map_edges": (
        "from_activity",
        "to_activity",
        "case_count",
        "avg_wait_minutes",
    ),
    "process_map_nodes": (
        "activity",
        "event_count",
        "case_count",
        "avg_time_in_step_minutes",
    ),
    "case_summary": (
        "case_id",
        "start_time",
        "end_time",
        "total_duration_minutes",
        "num_events",
        "has_loopback",
        "path_variant",
    ),
    "variant_summary": (
        "path_variant",
        "case_count",
        "pct_of_cases",
        "avg_duration_minutes",
    ),
    "kpi_summary": (
        "total_cases",
        "total_events",
        "avg_case_duration_minutes",
        "median_case_duration_minutes",
        "pct_cases_with_loopback",
        "top_bottleneck_transition",
        "top_bottleneck_avg_wait_minutes",
    ),
    "hourly_arrivals": (
        "hour_of_day",
        "case_count",
        "avg_case_duration_minutes",
    ),
}


def _ordered_events(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate and order canonical case, activity, and timestamp columns."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataframe]
    if missing_columns:
        raise ValueError(
            "Event log is missing required columns: " + ", ".join(missing_columns)
        )
    if dataframe.empty:
        raise ValueError("Event log must contain at least one event")

    events = dataframe.loc[:, list(REQUIRED_COLUMNS)].copy()
    for column in ("case_id", "activity"):
        events[column] = events[column].astype("string").str.strip()
        if events[column].isna().any() or events[column].eq("").any():
            raise ValueError(f"Event log contains an empty {column} value")

    events["timestamp"] = pd.to_datetime(
        events["timestamp"], utc=True, errors="coerce"
    )
    if events["timestamp"].isna().any():
        raise ValueError("Event log contains an invalid timestamp")

    events["_source_order"] = range(len(events))
    events = events.sort_values(
        ["case_id", "timestamp", "activity", "_source_order"], kind="stable"
    ).reset_index(drop=True)
    waits = events.groupby("case_id", sort=False)["timestamp"].diff().dropna()
    if (waits < pd.Timedelta(0)).any():
        raise ValueError("Consecutive events must not have negative durations")
    return events


def _case_durations(events: pd.DataFrame) -> pd.DataFrame:
    """Return one row per case with duration and timestamps."""
    grouped = events.groupby("case_id", sort=False)["timestamp"]
    cases = grouped.agg(start_time="min", end_time="max").reset_index()
    cases["total_duration_minutes"] = (
        cases["end_time"] - cases["start_time"]
    ).dt.total_seconds() / 60
    counts = events.groupby("case_id", sort=False).size().rename("num_events")
    cases = cases.join(counts, on="case_id")
    return cases


def _transition_events(events: pd.DataFrame) -> pd.DataFrame:
    """Return each event and its next event within the same case."""
    following = events.groupby("case_id", sort=False)
    transitions = events.copy()
    transitions["to_activity"] = following["activity"].shift(-1)
    transitions["next_timestamp"] = following["timestamp"].shift(-1)
    transitions = transitions.loc[transitions["to_activity"].notna()].copy()
    transitions["wait_minutes"] = (
        transitions["next_timestamp"] - transitions["timestamp"]
    ).dt.total_seconds() / 60
    return transitions


def _has_loopback(activities: list[str]) -> bool:
    """Return whether a case visits an activity it has already seen."""
    previously_seen: set[str] = set()
    for activity in activities:
        if activity in previously_seen:
            return True
        previously_seen.add(activity)
    return False


def build_process_map_edges(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Summarize observed directly-follows transitions for the process map."""
    events = _ordered_events(dataframe)
    transitions = _transition_events(events)
    edges = (
        transitions.groupby(["activity", "to_activity"], sort=True)
        .agg(
            case_count=("case_id", "nunique"),
            avg_wait_minutes=("wait_minutes", "mean"),
        )
        .reset_index()
        .rename(columns={"activity": "from_activity"})
    )
    return edges.loc[:, list(TABLE_COLUMNS["process_map_edges"])]


def build_process_map_nodes(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Summarize event and case counts plus average time before the next step."""
    events = _ordered_events(dataframe)
    transitions = _transition_events(events)
    nodes = (
        events.groupby("activity", sort=True)
        .agg(event_count=("activity", "size"), case_count=("case_id", "nunique"))
        .reset_index()
    )
    step_times = (
        transitions.groupby("activity", sort=True)["wait_minutes"]
        .mean()
        .rename("avg_time_in_step_minutes")
        .reset_index()
    )
    nodes = nodes.merge(step_times, on="activity", how="left")
    return nodes.loc[:, list(TABLE_COLUMNS["process_map_nodes"])]


def build_case_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return duration, path, and loop-back details for each case."""
    events = _ordered_events(dataframe)
    cases = _case_durations(events)
    paths = events.groupby("case_id", sort=False)["activity"].agg(list)
    cases["path_variant"] = cases["case_id"].map(
        paths.map(lambda activities: " -> ".join(activities))
    )
    cases["has_loopback"] = cases["case_id"].map(
        paths.map(_has_loopback)
    ).astype(bool)
    for column in ("start_time", "end_time"):
        cases[column] = cases[column].map(
            lambda timestamp: timestamp.isoformat().replace("+00:00", "Z")
        )
    return cases.loc[:, list(TABLE_COLUMNS["case_summary"])]


def build_variant_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aggregate case counts, population shares, and duration by path variant."""
    cases = build_case_summary(dataframe)
    variants = (
        cases.groupby("path_variant", sort=True)
        .agg(
            case_count=("case_id", "size"),
            avg_duration_minutes=("total_duration_minutes", "mean"),
        )
        .reset_index()
    )
    variants["pct_of_cases"] = variants["case_count"] / len(cases) * 100
    variants = variants.sort_values(
        ["case_count", "path_variant"],
        ascending=[False, True],
        kind="stable",
    )
    return variants.loc[:, list(TABLE_COLUMNS["variant_summary"])].reset_index(
        drop=True
    )


def build_kpi_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return overall case, event, duration, loop-back, and bottleneck KPIs."""
    events = _ordered_events(dataframe)
    cases = build_case_summary(events)
    edges = build_process_map_edges(events)
    if edges.empty:
        top_transition = ""
        top_wait: float | None = None
    else:
        top_edge = edges.sort_values(
            ["avg_wait_minutes", "case_count", "from_activity", "to_activity"],
            ascending=[False, False, True, True],
            kind="stable",
        ).iloc[0]
        top_transition = f"{top_edge['from_activity']} -> {top_edge['to_activity']}"
        top_wait = float(top_edge["avg_wait_minutes"])

    result = {
        "total_cases": int(len(cases)),
        "total_events": int(len(events)),
        "avg_case_duration_minutes": float(cases["total_duration_minutes"].mean()),
        "median_case_duration_minutes": float(
            cases["total_duration_minutes"].median()
        ),
        "pct_cases_with_loopback": float(cases["has_loopback"].mean() * 100),
        "top_bottleneck_transition": top_transition,
        "top_bottleneck_avg_wait_minutes": top_wait,
    }
    return pd.DataFrame([result], columns=TABLE_COLUMNS["kpi_summary"])


def build_hourly_arrivals(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Group cases by their UTC start hour and average case duration."""
    events = _ordered_events(dataframe)
    cases = _case_durations(events)
    cases["hour_of_day"] = cases["start_time"].dt.hour
    hourly = (
        cases.groupby("hour_of_day", sort=True)
        .agg(
            case_count=("case_id", "size"),
            avg_case_duration_minutes=("total_duration_minutes", "mean"),
        )
        .reset_index()
    )
    return hourly.loc[:, list(TABLE_COLUMNS["hourly_arrivals"])]


def build_dashboard_tables(dataframe: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build all six dashboard tables from one validated event log."""
    builders: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
        "process_map_edges": build_process_map_edges,
        "process_map_nodes": build_process_map_nodes,
        "case_summary": build_case_summary,
        "variant_summary": build_variant_summary,
        "kpi_summary": build_kpi_summary,
        "hourly_arrivals": build_hourly_arrivals,
    }
    return {name: builder(dataframe) for name, builder in builders.items()}


def main() -> None:
    """Write all dashboard tables as CSV files under output/powerbi."""
    script_directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Build Power BI dashboard tables from an event-log CSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=script_directory / "sample_event_log.csv",
        help="CSV with case_id, activity, and timestamp columns.",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=script_directory / "output" / "powerbi",
        help="Output folder for the six dashboard CSV files.",
    )
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"event-log file does not exist: {args.input}")

    try:
        dataframe, _ = read_event_log(args.input)
        tables = build_dashboard_tables(dataframe)
    except ValueError as error:
        parser.error(str(error))

    args.output_directory.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        output_path = args.output_directory / f"{name}.csv"
        table.to_csv(output_path, index=False)
        print(f"Wrote {len(table)} rows to {output_path}")


if __name__ == "__main__":
    main()
