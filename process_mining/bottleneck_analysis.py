"""Calculate and visualize waiting-time bottlenecks in an event log."""

import argparse
import logging
import math
from pathlib import Path

import pandas as pd
import pm4py
from pm4py.objects.log.obj import EventLog


LOGGER = logging.getLogger(__name__)
REQUIRED_COLUMNS = ("case_id", "activity", "timestamp")
OUTPUT_COLUMNS = (
    "from_activity",
    "to_activity",
    "transition_count",
    "mean_waiting_time_hours",
    "median_waiting_time_hours",
    "max_waiting_time_hours",
    "p90_waiting_time_hours",
    "bottleneck_rank",
    "is_bottleneck",
    "avg_wait_minutes",
    "median_wait_minutes",
    "p90_wait_minutes",
    "max_wait_minutes",
    "pct_of_all_transitions",
)
POWER_BI_COLUMNS = (
    "from_activity",
    "to_activity",
    "transition_count",
    "avg_wait_minutes",
    "median_wait_minutes",
    "p90_wait_minutes",
    "max_wait_minutes",
    "pct_of_all_transitions",
    "bottleneck_rank",
)
TOP_TRANSITIONS = 10
BOTTLENECK_COUNT = 3


def load_event_log(input_path: Path) -> tuple[pd.DataFrame, EventLog]:
    """Load a CSV event log, accepting either the dbt or sample column names."""
    dataframe = pd.read_csv(input_path)
    column_aliases = {
        "case_id": ("case_id", "Case_ID"),
        "activity": ("activity", "Activity_Name"),
        "timestamp": ("timestamp", "Timestamp"),
    }
    rename_columns = {}
    for canonical_name, aliases in column_aliases.items():
        matching = next(
            (column for column in aliases if column in dataframe.columns), None
        )
        if matching is not None:
            rename_columns[matching] = canonical_name
    dataframe = dataframe.rename(columns=rename_columns)

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in dataframe.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Event log is missing required columns: {', '.join(missing_columns)}"
        )
    if dataframe.empty:
        raise ValueError("Event log must contain at least one event")

    for column in ("case_id", "activity"):
        dataframe[column] = dataframe[column].astype("string").str.strip()
        invalid = dataframe[column].isna() | dataframe[column].eq("")
        if invalid.any():
            rows = ", ".join(str(int(index) + 2) for index in dataframe.index[invalid])
            raise ValueError(
                f"Event log contains an empty {column} value on CSV row(s): {rows}"
            )

    raw_timestamps = dataframe["timestamp"]
    parsed_timestamps = pd.to_datetime(
        raw_timestamps, utc=True, errors="coerce"
    )
    invalid_timestamps = parsed_timestamps.isna()
    if invalid_timestamps.any():
        bad_rows = []
        for index in dataframe.index[invalid_timestamps]:
            value = raw_timestamps.loc[index]
            reason = "empty" if pd.isna(value) or not str(value).strip() else "invalid"
            bad_rows.append(f"row {int(index) + 2} ({reason}: {value!r})")
        raise ValueError(
            "Invalid timestamp value(s) in event log: "
            + "; ".join(bad_rows)
            + ". Rows include the CSV header."
        )
    dataframe["timestamp"] = parsed_timestamps
    dataframe["_source_order"] = range(len(dataframe))
    dataframe = dataframe.sort_values(
        ["case_id", "timestamp", "_source_order"],
        kind="stable",
    )
    _validate_positive_transition_durations(dataframe)
    formatted = pm4py.format_dataframe(
        dataframe,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )
    return formatted, pm4py.convert_to_event_log(formatted)


def calculate_metrics(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Calculate ranked, positive-duration metrics for each activity transition."""
    ordered = dataframe.sort_values(
        ["case_id", "timestamp", "_source_order"],
        kind="stable",
    ).copy()
    case_events = ordered.groupby("case_id", sort=False)
    ordered["next_activity"] = case_events["activity"].shift(-1)
    ordered["next_timestamp"] = case_events["timestamp"].shift(-1)

    transitions = ordered.loc[ordered["next_activity"].notna()].copy()
    transitions["waiting_time_hours"] = (
        transitions["next_timestamp"] - transitions["timestamp"]
    ).dt.total_seconds() / 3600
    transitions = transitions.loc[transitions["waiting_time_hours"] > 0].copy()

    if transitions.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    metrics = (
        transitions.groupby(["activity", "next_activity"])["waiting_time_hours"]
        .agg(
            transition_count="size",
            mean_waiting_time_hours="mean",
            median_waiting_time_hours="median",
            max_waiting_time_hours="max",
            p90_waiting_time_hours=lambda values: values.quantile(
                0.9, interpolation="linear"
            ),
        )
        .reset_index()
        .rename(
            columns={
                "activity": "from_activity",
                "next_activity": "to_activity",
            }
        )
    )
    total_transitions = int(metrics["transition_count"].sum())
    metrics["avg_wait_minutes"] = metrics["mean_waiting_time_hours"] * 60
    metrics["median_wait_minutes"] = metrics["median_waiting_time_hours"] * 60
    metrics["p90_wait_minutes"] = metrics["p90_waiting_time_hours"] * 60
    metrics["max_wait_minutes"] = metrics["max_waiting_time_hours"] * 60
    metrics["pct_of_all_transitions"] = (
        metrics["transition_count"] / total_transitions * 100
        if total_transitions
        else 0.0
    )
    metrics = metrics.sort_values(
        [
            "avg_wait_minutes",
            "transition_count",
            "from_activity",
            "to_activity",
        ],
        ascending=[False, False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    metrics["bottleneck_rank"] = range(1, len(metrics) + 1)
    metrics["is_bottleneck"] = metrics["bottleneck_rank"] <= BOTTLENECK_COUNT
    return metrics.loc[:, list(OUTPUT_COLUMNS)]


def _validate_positive_transition_durations(dataframe: pd.DataFrame) -> None:
    """Reject event logs whose consecutive events have zero or negative waits."""
    ordered = dataframe.sort_values(
        ["case_id", "timestamp", "_source_order"],
        kind="stable",
    )
    gaps = ordered.groupby("case_id", sort=False)["timestamp"].diff().dropna()
    invalid_gaps = gaps <= pd.Timedelta(0)
    if invalid_gaps.any():
        raise ValueError(
            "Consecutive events must have strictly increasing timestamps; "
            f"found {int(invalid_gaps.sum())} zero or negative duration(s)"
        )


def validate_transition_sanity(
    dataframe: pd.DataFrame, metrics: pd.DataFrame
) -> None:
    """Check that every case's consecutive event pair is counted exactly once."""
    expected_count = len(dataframe) - int(dataframe["case_id"].nunique())
    actual_count = int(metrics["transition_count"].sum())
    if actual_count != expected_count:
        raise AssertionError(
            f"Expected {expected_count} transitions from events and cases, "
            f"but calculated {actual_count}"
        )
    if (metrics["avg_wait_minutes"] < 0).any():
        raise AssertionError("Transition metrics must not contain negative waits")


def cross_check_pm4py(metrics: pd.DataFrame, event_log: EventLog) -> None:
    """Verify pandas mean waits against PM4Py's performance directly-follows graph."""
    performance_dfg, _, _ = pm4py.discover_performance_dfg(event_log)
    pandas_means = {
        (row.from_activity, row.to_activity): float(row.avg_wait_minutes) * 60
        for row in metrics.itertuples(index=False)
    }
    if set(performance_dfg) != set(pandas_means):
        raise AssertionError(
            "Pandas transitions do not match the PM4Py performance DFG"
        )
    for transition, performance in performance_dfg.items():
        pm4py_mean_seconds = float(performance["mean"])
        if not math.isclose(
            pandas_means[transition],
            pm4py_mean_seconds,
            rel_tol=1e-9,
            abs_tol=1e-6,
        ):
            raise AssertionError(
                f"Mean wait mismatch for {transition!r}: pandas="
                f"{pandas_means[transition]} seconds, "
                f"PM4Py={pm4py_mean_seconds} seconds"
            )


def write_performance_dfg(event_log: EventLog, output_path: Path) -> None:
    """Save PM4Py's performance DFG with mean edge waits labeled in hours."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Circle, FancyArrowPatch

    dfg, _, _ = pm4py.discover_performance_dfg(event_log)
    activities = sorted({activity for edge in dfg for activity in edge})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(figsize=(max(8, len(activities) * 1.8), 6))
    if not dfg:
        axes.text(0.5, 0.5, "No activity transitions found", ha="center", va="center")
        axes.set_axis_off()
    else:
        angles = np.linspace(np.pi / 2, np.pi / 2 - 2 * np.pi, len(activities), endpoint=False)
        positions = {
            activity: np.array([np.cos(angle), np.sin(angle)])
            for activity, angle in zip(activities, angles)
        }
        for (source, target), performance in dfg.items():
            mean_seconds = performance["mean"]
            start = positions[source]
            end = positions[target]
            if source == target:
                arrow = FancyArrowPatch(
                    start + np.array([0.08, 0.08]),
                    start + np.array([-0.08, 0.08]),
                    connectionstyle="arc3,rad=1.8",
                    arrowstyle="-|>",
                    mutation_scale=14,
                    color="#2878B5",
                    linewidth=1.5,
                )
                label_position = start + np.array([0, 0.36])
            else:
                direction = 0.14 if source < target else -0.14
                arrow = FancyArrowPatch(
                    start,
                    end,
                    shrinkA=30,
                    shrinkB=30,
                    connectionstyle=f"arc3,rad={direction}",
                    arrowstyle="-|>",
                    mutation_scale=14,
                    color="#2878B5",
                    linewidth=1.5,
                )
                label_position = (start + end) / 2 + np.array([0, 0.08])
            axes.add_patch(arrow)
            axes.text(
                label_position[0],
                label_position[1],
                f"{mean_seconds / 3600:.2f} h",
                ha="center",
                va="center",
                fontsize=9,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8},
            )

        for activity, position in positions.items():
            axes.add_patch(
                Circle(position, radius=0.12, facecolor="#EAF2F8", edgecolor="#2878B5")
            )
            axes.text(*position, activity, ha="center", va="center", fontsize=9)
        axes.set_title("Performance DFG — Mean Waiting Time")
        axes.set_xlim(-1.5, 1.5)
        axes.set_ylim(-1.35, 1.5)
        axes.set_aspect("equal")
        axes.axis("off")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def write_top_transitions_chart(
    metrics: pd.DataFrame, output_path: Path
) -> None:
    """Save a horizontal bar chart of the ten pairs with highest mean wait."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = metrics.head(TOP_TRANSITIONS).iloc[::-1]
    figure, axes = plt.subplots(figsize=(11, max(4, 0.55 * len(top) + 1.5)))
    if top.empty:
        axes.text(0.5, 0.5, "No activity transitions found", ha="center", va="center")
        axes.set_axis_off()
    else:
        labels = top["from_activity"] + " -> " + top["to_activity"]
        axes.barh(labels, top["mean_waiting_time_hours"], color="#2878B5")
        axes.set_xlabel("Mean waiting time (hours)")
        axes.set_title("Top 10 Slowest Activity Transitions")
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    script_directory = Path(__file__).resolve().parent
    output_directory = script_directory / "output"

    parser = argparse.ArgumentParser(
        description="Calculate directly-follows waiting-time bottlenecks."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=script_directory / "sample_event_log.csv",
        help="CSV event log (default: process_mining/sample_event_log.csv)",
    )
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"event-log file does not exist: {args.input}")

    try:
        dataframe, event_log = load_event_log(args.input)
    except ValueError as error:
        parser.error(str(error))
    metrics = calculate_metrics(dataframe)
    validate_transition_sanity(dataframe, metrics)
    cross_check_pm4py(metrics, event_log)

    csv_path = output_directory / "bottleneck_transitions.csv"
    legacy_csv_path = output_directory / "bottlenecks.csv"
    dfg_path = output_directory / "performance_dfg.png"
    chart_path = output_directory / "top_10_slowest_transitions.png"
    output_directory.mkdir(parents=True, exist_ok=True)
    power_bi_metrics = metrics.head(TOP_TRANSITIONS).loc[
        :, list(POWER_BI_COLUMNS)
    ]
    power_bi_metrics.to_csv(csv_path, index=False)
    metrics.to_csv(legacy_csv_path, index=False)
    write_performance_dfg(event_log, dfg_path)
    write_top_transitions_chart(metrics, chart_path)

    LOGGER.info("Analyzed %s events across %s cases.", len(dataframe), len(event_log))
    LOGGER.info("Cross-checked pandas transition means against PM4Py.")
    LOGGER.info(
        "Wrote %s top transition rows to %s", len(power_bi_metrics), csv_path
    )
    LOGGER.info("Wrote the legacy ranked transition CSV to %s", legacy_csv_path)
    LOGGER.info("Wrote the performance DFG to %s", dfg_path)
    LOGGER.info("Wrote the top-transition chart to %s", chart_path)
    LOGGER.info(
        "Top 10 transitions by mean wait:\n%s",
        metrics.head(TOP_TRANSITIONS)[
            ["from_activity", "to_activity", "transition_count", "avg_wait_minutes"]
        ].to_string(index=False),
    )


if __name__ == "__main__":
    main()
