"""Discover a directly-follows graph and Petri net from a patient event log."""

from pathlib import Path

import matplotlib
import pandas as pd
import networkx as nx
import pm4py
from pm4py.objects.log.obj import EventLog


REQUIRED_COLUMNS = ("case_id", "activity", "timestamp")


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
    dataframe = pd.read_csv(input_path)
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

    missing_timestamps = dataframe["timestamp"].isna() | dataframe[
        "timestamp"
    ].astype("string").str.strip().eq("")
    if missing_timestamps.any():
        raise ValueError("Event log contains an empty timestamp value")

    dataframe["timestamp"] = pd.to_datetime(
        dataframe["timestamp"], utc=True, errors="raise"
    )
    dataframe = dataframe.sort_values("timestamp", kind="stable").reset_index(
        drop=True
    )
    formatted = pm4py.format_dataframe(
        dataframe,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )
    return formatted, pm4py.convert_to_event_log(formatted)


def main() -> None:
    """Discover and save a frequency DFG and an Inductive Miner Petri net."""
    directory = Path(__file__).resolve().parent
    output_directory = directory / "output"
    output_directory.mkdir(parents=True, exist_ok=True)
    dataframe, event_log = read_event_log(directory / "sample_event_log.csv")

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

    print(f"Cases: {dataframe['case_id'].nunique()}")
    print(f"Activities: {dataframe['activity'].nunique()}")
    print(f"Variants: {len(pm4py.get_variants(event_log))}")
    print(f"DFG saved to: {dfg_path}")
    print(f"Petri net saved to: {petri_net_path}")


if __name__ == "__main__":
    main()
