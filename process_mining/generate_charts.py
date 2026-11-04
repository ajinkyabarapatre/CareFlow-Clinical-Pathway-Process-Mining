"""Generate dashboard charts and summary tables from a patient event log."""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


INPUT_FILE = Path(__file__).resolve().parent / "sample_event_log.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "charts"
CASE_COL = "case_id"
ACTIVITY_COL = "activity"
TIME_COL = "timestamp"
TOP_N = 10


def _validate_columns(events: pd.DataFrame) -> None:
    """Raise a clear error when any required event-log column is absent."""
    required = (CASE_COL, ACTIVITY_COL, TIME_COL)
    missing = [column for column in required if column not in events.columns]
    if missing:
        raise ValueError(
            "Event log is missing required columns: " + ", ".join(missing)
        )


def _ordered_events(events: pd.DataFrame) -> pd.DataFrame:
    """Return a validated copy, ordered by patient and event time."""
    _validate_columns(events)
    ordered = events.loc[:, [CASE_COL, ACTIVITY_COL, TIME_COL]].copy()
    for column in (CASE_COL, ACTIVITY_COL):
        ordered[column] = ordered[column].astype("string").str.strip()
        if ordered[column].isna().any() or ordered[column].eq("").any():
            raise ValueError(f"Event log contains an empty {column} value")

    ordered[TIME_COL] = pd.to_datetime(
        ordered[TIME_COL], utc=True, errors="coerce"
    )
    if ordered[TIME_COL].isna().any():
        raise ValueError(f"Event log contains an invalid {TIME_COL} value")

    ordered["_source_order"] = range(len(ordered))
    ordered = ordered.sort_values(
        [CASE_COL, TIME_COL, "_source_order"], kind="stable"
    )
    return ordered.drop(columns="_source_order").reset_index(drop=True)


def load_event_log(input_file: Path = INPUT_FILE) -> pd.DataFrame:
    """Read, validate, and sort a CSV event log."""
    try:
        events = pd.read_csv(input_file)
    except pd.errors.EmptyDataError as error:
        raise ValueError(f"Event log is empty or has no header: {input_file}") from error
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read event log '{input_file}': {error}") from error

    _validate_columns(events)
    if events.empty:
        raise ValueError(f"Event log contains no events: {input_file}")
    return _ordered_events(events)


def build_transitions(events: pd.DataFrame) -> pd.DataFrame:
    """Return each patient's consecutive activity pair and its wait in minutes."""
    columns = (CASE_COL, "from_activity", "to_activity", "wait_minutes")
    ordered = _ordered_events(events)
    if ordered.empty:
        return pd.DataFrame(columns=columns)

    grouped = ordered.groupby(CASE_COL, sort=False)
    following_activity = grouped[ACTIVITY_COL].shift(-1)
    following_time = grouped[TIME_COL].shift(-1)
    transitions = pd.DataFrame(
        {
            CASE_COL: ordered[CASE_COL],
            "from_activity": ordered[ACTIVITY_COL],
            "to_activity": following_activity,
            "from_time": ordered[TIME_COL],
            "to_time": following_time,
        }
    )
    transitions = transitions.loc[transitions["to_activity"].notna()].copy()
    transitions["wait_minutes"] = (
        transitions["to_time"] - transitions["from_time"]
    ).dt.total_seconds() / 60
    transitions = transitions.loc[transitions["wait_minutes"] >= 0]
    return transitions.loc[:, list(columns)].reset_index(drop=True)


def bottleneck_table(transitions: pd.DataFrame) -> pd.DataFrame:
    """Summarize transition counts and waiting-time metrics, slowest first."""
    columns = (
        "from_activity",
        "to_activity",
        "transition",
        "transition_count",
        "avg_wait_minutes",
        "max_wait_minutes",
    )
    if transitions.empty:
        return pd.DataFrame(columns=columns)

    summary = (
        transitions.groupby(["from_activity", "to_activity"], sort=False)
        .agg(
            transition_count=("wait_minutes", "size"),
            avg_wait_minutes=("wait_minutes", "mean"),
            max_wait_minutes=("wait_minutes", "max"),
        )
        .reset_index()
    )
    summary["transition"] = (
        summary["from_activity"] + " -> " + summary["to_activity"]
    )
    summary = summary.sort_values(
        ["avg_wait_minutes", "max_wait_minutes", "transition"],
        ascending=[False, False, True],
        kind="stable",
    )
    return summary.loc[:, list(columns)].reset_index(drop=True)


def variant_table(events: pd.DataFrame) -> pd.DataFrame:
    """List complete patient paths by frequency, assigning V1 to the most common."""
    columns = ("path_variant", "case_count", "pct_of_cases", "variant_id")
    ordered = _ordered_events(events)
    if ordered.empty:
        return pd.DataFrame(columns=columns)

    paths = ordered.groupby(CASE_COL, sort=False)[ACTIVITY_COL].agg(
        lambda activities: " -> ".join(activities.astype(str))
    )
    counts = paths.value_counts()
    variants = counts.rename_axis("path_variant").rename("case_count").reset_index()
    variants["pct_of_cases"] = variants["case_count"] / len(paths) * 100
    variants["variant_id"] = [
        f"V{rank}" for rank in range(1, len(variants) + 1)
    ]
    return variants.loc[:, list(columns)]


def _has_loopback(activities: list[str]) -> bool:
    """Return whether a patient revisits an activity already seen."""
    visited: set[str] = set()
    for activity in activities:
        if activity in visited:
            return True
        visited.add(activity)
    return False


def case_table(events: pd.DataFrame) -> pd.DataFrame:
    """Return each patient's start, end, event count, duration, and loop-back flag."""
    columns = (
        CASE_COL,
        "start_time",
        "end_time",
        "num_events",
        "duration_minutes",
        "has_loopback",
    )
    ordered = _ordered_events(events)
    if ordered.empty:
        return pd.DataFrame(columns=columns)

    cases = (
        ordered.groupby(CASE_COL, sort=False)
        .agg(
            start_time=(TIME_COL, "min"),
            end_time=(TIME_COL, "max"),
            num_events=(ACTIVITY_COL, "size"),
        )
        .reset_index()
    )
    cases["duration_minutes"] = (
        cases["end_time"] - cases["start_time"]
    ).dt.total_seconds() / 60
    paths = ordered.groupby(CASE_COL, sort=False)[ACTIVITY_COL].agg(list)
    cases["has_loopback"] = cases[CASE_COL].map(
        paths.map(_has_loopback)
    ).astype(bool)
    return cases.loc[:, list(columns)]


def kpi_table(events: pd.DataFrame) -> pd.DataFrame:
    """Calculate overall case, event, activity, stay, loop-back, and bottleneck KPIs."""
    columns = (
        "total_cases",
        "total_events",
        "total_activities",
        "avg_stay_minutes",
        "max_stay_minutes",
        "pct_cases_with_loopback",
        "top_bottleneck",
        "top_bottleneck_avg_wait",
    )
    ordered = _ordered_events(events)
    if ordered.empty:
        return pd.DataFrame(
            [
                {
                    "total_cases": 0,
                    "total_events": 0,
                    "total_activities": 0,
                    "avg_stay_minutes": 0.0,
                    "max_stay_minutes": 0.0,
                    "pct_cases_with_loopback": 0.0,
                    "top_bottleneck": "",
                    "top_bottleneck_avg_wait": 0.0,
                }
            ],
            columns=columns,
        )

    cases = case_table(ordered)
    bottlenecks = bottleneck_table(build_transitions(ordered))
    if bottlenecks.empty:
        top_bottleneck = ""
        top_bottleneck_avg_wait = 0.0
    else:
        top_bottleneck = str(bottlenecks.loc[0, "transition"])
        top_bottleneck_avg_wait = float(
            bottlenecks.loc[0, "avg_wait_minutes"]
        )

    return pd.DataFrame(
        [
            {
                "total_cases": int(ordered[CASE_COL].nunique()),
                "total_events": int(len(ordered)),
                "total_activities": int(ordered[ACTIVITY_COL].nunique()),
                "avg_stay_minutes": float(cases["duration_minutes"].mean()),
                "max_stay_minutes": float(cases["duration_minutes"].max()),
                "pct_cases_with_loopback": float(
                    cases["has_loopback"].mean() * 100
                ),
                "top_bottleneck": top_bottleneck,
                "top_bottleneck_avg_wait": top_bottleneck_avg_wait,
            }
        ],
        columns=columns,
    )


def save_charts(
    transitions: pd.DataFrame,
    variants: pd.DataFrame,
    cases: pd.DataFrame,
    events: pd.DataFrame,
    output_dir: Path = OUTPUT_DIR,
) -> None:
    """Save four labeled dashboard charts as PNG files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    bottlenecks = bottleneck_table(transitions).head(TOP_N).iloc[::-1]
    figure, axes = plt.subplots(figsize=(10, max(4, len(bottlenecks) * 0.5)))
    if bottlenecks.empty:
        axes.text(0.5, 0.5, "No transitions found", ha="center", va="center")
    else:
        axes.barh(bottlenecks["transition"], bottlenecks["avg_wait_minutes"])
    axes.set_title("Top Bottlenecks by Average Wait")
    axes.set_xlabel("Average wait (minutes)")
    axes.set_ylabel("Activity transition")
    figure.tight_layout()
    figure.savefig(output_dir / "top_bottlenecks.png", dpi=150)
    plt.close(figure)

    top_variants = variants.head(TOP_N).iloc[::-1]
    figure, axes = plt.subplots(figsize=(10, max(4, len(top_variants) * 0.5)))
    if top_variants.empty:
        axes.text(0.5, 0.5, "No path variants found", ha="center", va="center")
    else:
        axes.barh(top_variants["variant_id"], top_variants["case_count"])
    axes.set_title("Most Common Patient Path Variants")
    axes.set_xlabel("Number of cases")
    axes.set_ylabel("Path variant")
    figure.tight_layout()
    figure.savefig(output_dir / "path_variants.png", dpi=150)
    plt.close(figure)

    ordered_cases = cases.sort_values("duration_minutes", ascending=False)
    figure, axes = plt.subplots(figsize=(10, 5))
    if ordered_cases.empty:
        axes.text(0.5, 0.5, "No patient cases found", ha="center", va="center")
    else:
        axes.bar(
            ordered_cases[CASE_COL].astype(str),
            ordered_cases["duration_minutes"],
        )
        axes.tick_params(axis="x", labelrotation=45)
    axes.set_title("Stay Time per Patient Case")
    axes.set_xlabel("Patient case")
    axes.set_ylabel("Stay time (minutes)")
    figure.tight_layout()
    figure.savefig(output_dir / "stay_time_per_case.png", dpi=150)
    plt.close(figure)

    activity_counts = events[ACTIVITY_COL].value_counts().head(TOP_N).iloc[::-1]
    figure, axes = plt.subplots(figsize=(10, max(4, len(activity_counts) * 0.5)))
    if activity_counts.empty:
        axes.text(0.5, 0.5, "No activities found", ha="center", va="center")
    else:
        axes.barh(activity_counts.index.astype(str), activity_counts.values)
    axes.set_title("Event Counts by Activity")
    axes.set_xlabel("Number of events")
    axes.set_ylabel("Activity")
    figure.tight_layout()
    figure.savefig(output_dir / "activity_counts.png", dpi=150)
    plt.close(figure)


def main() -> None:
    """Build and save dashboard KPIs, variants, and charts."""
    events = load_event_log()
    transitions = build_transitions(events)
    variants = variant_table(events)
    cases = case_table(events)
    kpis = kpi_table(events)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    kpis.to_csv(OUTPUT_DIR / "kpi_summary.csv", index=False)
    variants.to_csv(OUTPUT_DIR / "variant_table.csv", index=False)
    save_charts(transitions, variants, cases, events, OUTPUT_DIR)
    print(kpis.to_string(index=False))
    print(f"Dashboard charts and tables saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
