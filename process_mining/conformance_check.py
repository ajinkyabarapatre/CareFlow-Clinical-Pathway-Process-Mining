"""Check event-log conformance against the ideal clinical pathway."""

from collections import Counter
from pathlib import Path

import pandas as pd
import pm4py
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils


IDEAL_PATH = ("Admission", "Triage", "Diagnosis", "Treatment", "Discharge")
REQUIRED_COLUMNS = ("case_id", "activity", "timestamp")
OUTPUT_COLUMNS = (
    "case_id",
    "activities",
    "fitness_score",
    "is_conforming",
    "deviations",
)


def build_ideal_model() -> tuple[PetriNet, Marking, Marking]:
    """Build a Petri net that permits only the ideal sequence."""
    net = PetriNet("ideal_clinical_pathway")
    places = [
        PetriNet.Place(f"place_{index}") for index in range(len(IDEAL_PATH) + 1)
    ]
    for place in places:
        net.places.add(place)

    for index, activity in enumerate(IDEAL_PATH):
        transition = PetriNet.Transition(f"transition_{index}", activity)
        net.transitions.add(transition)
        petri_utils.add_arc_from_to(places[index], transition, net)
        petri_utils.add_arc_from_to(transition, places[index + 1], net)

    initial_marking = Marking({places[0]: 1})
    final_marking = Marking({places[-1]: 1})
    return net, initial_marking, final_marking


def read_event_log(input_path: Path) -> tuple[pd.DataFrame, EventLog]:
    """Read and order events, then convert them to a PM4Py event log."""
    dataframe = pd.read_csv(input_path)
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
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


def _describe_deviations(activities: list[str]) -> list[str]:
    """Name missing, repeated, out-of-order, and unexpected activities."""
    counts = Counter(activities)
    deviations = []

    missing = [activity for activity in IDEAL_PATH if counts[activity] == 0]
    if missing:
        deviations.append(f"skipped: {', '.join(missing)}")

    repeated = [activity for activity in IDEAL_PATH if counts[activity] > 1]
    if repeated:
        deviations.append(f"repeated: {', '.join(repeated)}")

    unexpected = sorted(set(activities) - set(IDEAL_PATH))
    if unexpected:
        deviations.append(f"unexpected: {', '.join(unexpected)}")

    pathway_positions = [
        IDEAL_PATH.index(activity)
        for activity in activities
        if activity in IDEAL_PATH
    ]
    if any(
        current < previous
        for previous, current in zip(pathway_positions, pathway_positions[1:])
    ):
        deviations.append("out of order")

    return deviations


def analyze_event_log(
    dataframe: pd.DataFrame,
    event_log: EventLog,
    net: PetriNet,
    initial_marking: Marking,
    final_marking: Marking,
) -> tuple[list[dict[str, str | float | bool]], float]:
    """Return per-case token-replay fitness and the mean trace fitness."""
    replay_results = token_replay.apply(
        event_log, net, initial_marking, final_marking
    )
    activities_by_case = {
        str(case_id): group["activity"].astype(str).tolist()
        for case_id, group in dataframe.groupby("case_id", sort=False)
    }
    results = []

    for trace, replay_result in zip(event_log, replay_results):
        case_id = str(trace.attributes["concept:name"])
        activities = activities_by_case[case_id]
        deviations = _describe_deviations(activities)
        # Exact sequence matching keeps conformance stricter than replay fitness alone.
        is_conforming = tuple(activities) == IDEAL_PATH and replay_result["trace_is_fit"]
        results.append(
            {
                "case_id": case_id,
                "activities": " -> ".join(activities),
                "fitness_score": float(replay_result["trace_fitness"]),
                "is_conforming": is_conforming,
                "deviations": "; ".join(deviations),
            }
        )

    overall_fitness = (
        sum(float(result["fitness_score"]) for result in results) / len(results)
    )
    return results, overall_fitness


def main() -> None:
    """Run token-based replay and save one result row per case."""
    directory = Path(__file__).resolve().parent
    input_path = directory / "sample_event_log.csv"
    output_path = directory / "output" / "conformance_results.csv"

    dataframe, event_log = read_event_log(input_path)
    net, initial_marking, final_marking = build_ideal_model()
    results, overall_fitness = analyze_event_log(
        dataframe, event_log, net, initial_marking, final_marking
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results, columns=OUTPUT_COLUMNS).to_csv(output_path, index=False)

    # Fitness 1.0 means a perfect replay; lower scores reflect token deviations,
    # not clinical severity or a literal percentage of correct activities.
    conforming_count = sum(bool(result["is_conforming"]) for result in results)
    print(f"Cases analyzed: {len(results)}")
    print(f"Conforming cases: {conforming_count}")
    print(f"Non-conforming cases: {len(results) - conforming_count}")
    print(f"Overall mean trace fitness: {overall_fitness:.3f}")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
