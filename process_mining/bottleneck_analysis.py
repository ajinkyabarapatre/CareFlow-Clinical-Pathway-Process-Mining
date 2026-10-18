"""Calculate and visualize waiting-time bottlenecks in an event log."""

import argparse
from pathlib import Path

import pandas as pd
import pm4py
from pm4py.objects.log.obj import EventLog


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
)
TOP_TRANSITIONS = 10
BOTTLENECK_COUNT = 3


def load_event_log(input_path: Path) -> tuple[pd.DataFrame, EventLog]:
    """Load, validate, order, and convert a CSV event log for PM4Py."""
    dataframe = pd.read_csv(input_path)
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
            raise ValueError(f"Event log contains an empty {column} value")

    timestamps = dataframe["timestamp"].astype("string").str.strip()
    if (dataframe["timestamp"].isna() | timestamps.eq("")).any():
        raise ValueError("Event log contains an empty timestamp value")
    dataframe["timestamp"] = pd.to_datetime(
        dataframe["timestamp"], utc=True, errors="raise"
    )
    dataframe["_source_order"] = range(len(dataframe))
    dataframe = dataframe.sort_values(
        ["case_id", "timestamp", "activity", "_source_order"],
        kind="stable",
    )
    formatted = pm4py.format_dataframe(
        dataframe,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )
    return formatted, pm4py.convert_to_event_log(formatted)


def calculate_metrics(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Calculate ranked waiting-time metrics for each directly-follows pair."""
    ordered = dataframe.sort_values(
        ["case_id", "timestamp", "activity", "_source_order"],
        kind="stable",
    ).copy()
    case_events = ordered.groupby("case_id", sort=False)
    ordered["next_activity"] = case_events["activity"].shift(-1)
    ordered["next_timestamp"] = case_events["timestamp"].shift(-1)

    transitions = ordered.loc[ordered["next_activity"].notna()].copy()
    transitions["waiting_time_hours"] = (
        transitions["next_timestamp"] - transitions["timestamp"]
    ).dt.total_seconds() / 3600

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
    metrics = metrics.sort_values(
        ["mean_waiting_time_hours", "from_activity", "to_activity"],
        ascending=[False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    metrics["bottleneck_rank"] = range(1, len(metrics) + 1)
    metrics["is_bottleneck"] = metrics["bottleneck_rank"] <= BOTTLENECK_COUNT
    return metrics.loc[:, OUTPUT_COLUMNS]


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

    dataframe, event_log = load_event_log(args.input)
    metrics = calculate_metrics(dataframe)

    csv_path = output_directory / "bottlenecks.csv"
    dfg_path = output_directory / "performance_dfg.png"
    chart_path = output_directory / "top_10_slowest_transitions.png"
    output_directory.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(csv_path, index=False)
    write_performance_dfg(event_log, dfg_path)
    write_top_transitions_chart(metrics, chart_path)

    print(f"Analyzed {len(dataframe)} events across {len(event_log)} cases.")
    print(f"Wrote {len(metrics)} transition rows to {csv_path}")
    print(f"Wrote the performance DFG to {dfg_path}")
    print(f"Wrote the top-transition chart to {chart_path}")


if __name__ == "__main__":
    main()
