"""Discover a directly-follows graph and Petri net from a patient event log."""

import argparse
from pathlib import Path

import matplotlib
import pandas as pd
import networkx as nx
import pm4py
from pm4py.objects.log.obj import EventLog


REQUIRED_COLUMNS = ("case_id", "activity", "timestamp")
SUMMARY_COLUMNS = (
    "cases",
    "events",
    "activities",
    "variants",
    "average_case_duration_hours",
    "max_case_duration_hours",
)


def _pyplot():
    """Load a non-interactive Matplotlib backend for file rendering."""
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def save_dfg_image(
    dfg: dict[tuple[str, str], int],
    start_activities: dict[str, int],
    end_activities: dict[str, int],
    output_path: Path,
    title: str,
) -> None:
    """Render a frequency DFG without requiring the Graphviz executable."""
    plt = _pyplot()
    graph = nx.DiGraph()
    graph.add_nodes_from(start_activities)
    graph.add_nodes_from(end_activities)
    graph.add_weighted_edges_from(
        (source, target, count) for (source, target), count in dfg.items()
    )
    positions = nx.spring_layout(graph, seed=42)

    labels = {
        activity: "\n".join(
            label
            for label in (
                activity,
                f"start: {start_activities[activity]}"
                if activity in start_activities
                else "",
                f"end: {end_activities[activity]}"
                if activity in end_activities
                else "",
            )
            if label
        )
        for activity in graph
    }
    figure, axes = plt.subplots(
        figsize=(max(8, len(graph) * 1.5), max(5, len(graph)))
    )
    nx.draw_networkx_nodes(graph, positions, node_size=3000, node_color="#D9EAF7", ax=axes)
    nx.draw_networkx_labels(graph, positions, labels=labels, font_size=9, ax=axes)
    nx.draw_networkx_edges(
        graph,
        positions,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=18,
        connectionstyle="arc3,rad=0.08",
        min_source_margin=18,
        min_target_margin=18,
        ax=axes,
    )
    nx.draw_networkx_edge_labels(
        graph,
        positions,
        edge_labels={(source, target): count for (source, target), count in dfg.items()},
        font_size=9,
        ax=axes,
    )
    axes.set_title(title)
    axes.axis("off")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def save_petri_net_image(
    net: pm4py.PetriNet,
    initial_marking: pm4py.Marking,
    final_marking: pm4py.Marking,
    output_path: Path,
) -> None:
    """Render a Petri net without requiring the Graphviz executable."""
    plt = _pyplot()
    graph = nx.DiGraph()
    places = sorted(net.places, key=lambda place: place.name)
    transitions = sorted(net.transitions, key=lambda transition: transition.name)
    graph.add_nodes_from(places)
    graph.add_nodes_from(transitions)
    graph.add_edges_from((arc.source, arc.target) for arc in net.arcs)
    positions = nx.spring_layout(graph, seed=42)
    place_labels = {
        place: (
            f"{place.name}\n"
            f"{initial_marking.get(place, 0)}→{final_marking.get(place, 0)}"
        )
        for place in places
    }
    transition_labels = {
        transition: transition.label or transition.name
        for transition in transitions
    }

    figure, axes = plt.subplots(
        figsize=(max(8, len(graph) * 1.2), max(5, len(graph) * 0.7))
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=places,
        node_shape="o",
        node_size=1800,
        node_color="#D9EAF7",
        ax=axes,
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        nodelist=transitions,
        node_shape="s",
        node_size=1500,
        node_color="#F7D9A8",
        ax=axes,
    )
    nx.draw_networkx_labels(graph, positions, labels=place_labels, font_size=8, ax=axes)
    nx.draw_networkx_labels(
        graph, positions, labels=transition_labels, font_size=8, ax=axes
    )
    nx.draw_networkx_edges(
        graph,
        positions,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=18,
        min_source_margin=15,
        min_target_margin=15,
        ax=axes,
    )
    axes.set_title("Inductive Miner Petri Net")
    axes.axis("off")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def read_event_log(input_path: Path) -> tuple[pd.DataFrame, EventLog]:
    """Read, validate, order, and convert a CSV event log to PM4Py."""
    try:
        dataframe = pd.read_csv(input_path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read event-log CSV '{input_path}': {error}") from error
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe]
    if missing:
        raise ValueError(
            f"Event log is missing required columns: {', '.join(missing)}"
        )
    if dataframe.empty:
        raise ValueError("Event log must contain at least one event")

    for column in ("case_id", "activity"):
        dataframe[column] = dataframe[column].astype("string").str.strip()
        invalid = dataframe[column].isna() | dataframe[column].eq("")
        if invalid.any():
            raise ValueError(f"Event log contains an empty {column} value")

    raw_timestamps = dataframe["timestamp"]
    parsed_timestamps = pd.to_datetime(
        raw_timestamps, utc=True, errors="coerce"
    )
    invalid_timestamps = parsed_timestamps.isna()
    if invalid_timestamps.any():
        bad_rows = []
        for index in dataframe.index[invalid_timestamps]:
            source_row = int(index) + 2
            value = raw_timestamps.loc[index]
            reason = "empty" if pd.isna(value) or not str(value).strip() else "invalid"
            bad_rows.append(f"row {source_row} ({reason}: {value!r})")
        details = "; ".join(bad_rows)
        raise ValueError(
            f"Invalid timestamp value(s) in event log: {details}. "
            "Rows are numbered as they appear in the CSV, including the header."
        )
    dataframe["timestamp"] = parsed_timestamps
    dataframe["_source_order"] = range(len(dataframe))
    dataframe = dataframe.sort_values(
        ["case_id", "timestamp", "activity", "_source_order"],
        kind="stable",
    ).drop(columns="_source_order").reset_index(drop=True)
    formatted = pm4py.format_dataframe(
        dataframe,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )
    return formatted, pm4py.convert_to_event_log(formatted)


def build_discovery_summary(dataframe: pd.DataFrame, event_log: EventLog) -> pd.DataFrame:
    """Return one-row case, event, variant, and duration summary metrics."""
    case_durations = dataframe.groupby("case_id", sort=False)["timestamp"].agg(
        start="min", end="max"
    )
    durations_hours = (
        case_durations["end"] - case_durations["start"]
    ).dt.total_seconds() / 3600
    return pd.DataFrame(
        [
            {
                "cases": int(dataframe["case_id"].nunique()),
                "events": int(len(dataframe)),
                "activities": int(dataframe["activity"].nunique()),
                "variants": int(len(pm4py.get_variants(event_log))),
                "average_case_duration_hours": float(durations_hours.mean()),
                "max_case_duration_hours": float(durations_hours.max()),
            }
        ],
        columns=SUMMARY_COLUMNS,
    )


def main() -> None:
    """Discover and save a frequency DFG and an Inductive Miner Petri net."""
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Discover a frequency DFG and Petri net from an event-log CSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=directory / "sample_event_log.csv",
        help="CSV with case_id, activity, and timestamp columns.",
    )
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"event-log file does not exist: {args.input}")

    output_directory = directory / "output"
    output_directory.mkdir(parents=True, exist_ok=True)
    try:
        dataframe, event_log = read_event_log(args.input)
    except ValueError as error:
        parser.error(str(error))

    dfg, start_activities, end_activities = pm4py.discover_dfg(event_log)
    dfg_path = output_directory / "dfg.png"
    save_dfg_image(
        dfg,
        start_activities,
        end_activities,
        dfg_path,
        "Frequency Directly-Follows Graph",
    )

    net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(
        event_log
    )
    petri_net_path = output_directory / "petri_net.png"
    save_petri_net_image(
        net,
        initial_marking,
        final_marking,
        petri_net_path,
    )

    summary_path = output_directory / "discovery_summary.csv"
    summary = build_discovery_summary(dataframe, event_log)
    summary.to_csv(summary_path, index=False)
    print(f"Cases: {summary.loc[0, 'cases']}")
    print(f"Events: {summary.loc[0, 'events']}")
    print(f"Activities: {summary.loc[0, 'activities']}")
    print(f"Variants: {summary.loc[0, 'variants']}")
    print(
        "Average case duration: "
        f"{summary.loc[0, 'average_case_duration_hours']:.2f} hours"
    )
    print(
        "Maximum case duration: "
        f"{summary.loc[0, 'max_case_duration_hours']:.2f} hours"
    )
    print(f"DFG saved to: {dfg_path}")
    print(f"Petri net saved to: {petri_net_path}")
    print(f"Discovery summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
