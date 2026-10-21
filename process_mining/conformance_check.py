"""Replay event-log cases against the ideal pathway and export deviations."""

import argparse
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
DEVIATION_TYPES = ("skipped", "repeated", "out_of_order", "extra_activity")
OUTPUT_COLUMNS = (
    "case_id",
    "fitness_score",
    "is_compliant",
    "deviation_type",
    "trace_variant",
    "duration_hours",
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
    """Read, validate, order, and convert a CSV event log to PM4Py."""
    try:
        dataframe = pd.read_csv(input_path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read event-log CSV '{input_path}': {error}") from error

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


def classify_deviations(activities: list[str]) -> list[str]:
    """Return every applicable deviation label in a stable, documented order."""
    counts = Counter(activities)
    pathway_positions = [
        IDEAL_PATH.index(activity)
        for activity in activities
        if activity in IDEAL_PATH
    ]
    deviation_flags = {
        "skipped": any(counts[activity] == 0 for activity in IDEAL_PATH),
        "repeated": any(counts[activity] > 1 for activity in IDEAL_PATH),
        "out_of_order": any(
            current < previous
            for previous, current in zip(
                pathway_positions, pathway_positions[1:]
            )
        ),
        "extra_activity": any(activity not in IDEAL_PATH for activity in activities),
    }
    return [
        deviation_type
        for deviation_type in DEVIATION_TYPES
        if deviation_flags[deviation_type]
    ]


def analyze_event_log(
    dataframe: pd.DataFrame,
    event_log: EventLog,
    net: PetriNet,
    initial_marking: Marking,
    final_marking: Marking,
) -> tuple[list[dict[str, str | float | bool]], float]:
    """Return per-case token fitness, compliance, deviation types, and duration."""
    replay_results = token_replay.apply(
        event_log, net, initial_marking, final_marking
    )
    case_data = {
        str(case_id): {
            "activities": group["activity"].astype(str).tolist(),
            "duration_hours": float(
                (
                    group["timestamp"].max() - group["timestamp"].min()
                ).total_seconds()
                / 3600
            ),
        }
        for case_id, group in dataframe.groupby("case_id", sort=False)
    }
    results = []

    for trace, replay_result in zip(event_log, replay_results):
        case_id = str(trace.attributes["concept:name"])
        activities = case_data[case_id]["activities"]
        deviations = classify_deviations(activities)
        is_compliant = (
            tuple(activities) == IDEAL_PATH and bool(replay_result["trace_is_fit"])
        )
        results.append(
            {
                "case_id": case_id,
                "fitness_score": float(replay_result["trace_fitness"]),
                "is_compliant": is_compliant,
                "deviation_type": ";".join(deviations) if deviations else "none",
                "trace_variant": " -> ".join(activities),
                "duration_hours": case_data[case_id]["duration_hours"],
            }
        )

    mean_fitness = sum(
        float(result["fitness_score"]) for result in results
    ) / len(results)
    return results, mean_fitness


def main() -> None:
    """Run token replay and save a Power BI-ready per-case CSV."""
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Check event-log traces against the fixed ideal pathway."
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
    try:
        dataframe, event_log = read_event_log(args.input)
    except ValueError as error:
        parser.error(str(error))

    net, initial_marking, final_marking = build_ideal_model()
    results, mean_fitness = analyze_event_log(
        dataframe, event_log, net, initial_marking, final_marking
    )

    output_path = directory / "output" / "conformance_results.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results, columns=OUTPUT_COLUMNS).to_csv(output_path, index=False)

    compliant_count = sum(bool(result["is_compliant"]) for result in results)
    print(f"Cases analyzed: {len(results)}")
    print(f"Compliant cases: {compliant_count}")
    print(f"Non-compliant cases: {len(results) - compliant_count}")
    print(f"Mean token-replay fitness: {mean_fitness:.3f}")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
