"""Replay event-log cases against the ideal pathway and export deviations."""

import argparse
from collections import Counter
from pathlib import Path
import warnings

import pandas as pd
import pm4py
from pm4py.objects.log.obj import EventLog
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import petri_utils

try:
    from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
except ImportError:
    token_replay = None


IDEAL_PATH = ["Admission", "Triage", "Diagnosis", "Treatment", "Discharge"]
OPTIONAL_STEPS = {"X-Ray", "Lab"}
REQUIRED_COLUMNS = ("case_id", "activity", "timestamp")
DEVIATION_TYPES = (
    "compliant",
    "skipped_step",
    "wrong_order",
    "repeated_step",
    "extra_step",
)
LEGACY_DEVIATION_TYPES = ("skipped", "repeated", "out_of_order", "extra_activity")
OUTPUT_COLUMNS = (
    "case_id",
    "fitness_score",
    "is_compliant",
    "deviation_type",
    "trace_variant",
    "duration_hours",
)
CONFORMANCE_COLUMNS = (
    "Case_ID",
    "actual_path",
    "is_compliant",
    "deviation_type",
    "missing_steps",
    "extra_steps",
)
SUMMARY_COLUMNS = (
    "total_cases",
    "compliant_cases",
    "non_compliant_cases",
    "pct_compliant",
    "pct_non_compliant",
    *(f"{deviation_type}_count" for deviation_type in DEVIATION_TYPES),
    "average_fitness",
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

    for index, place in enumerate(places):
        for optional_step in sorted(OPTIONAL_STEPS):
            transition = PetriNet.Transition(
                f"optional_{index}_{optional_step}", optional_step
            )
            net.transitions.add(transition)
            petri_utils.add_arc_from_to(place, transition, net)
            petri_utils.add_arc_from_to(transition, place, net)

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
    if dataframe.empty:
        dataframe = dataframe.drop(columns="_source_order")
        dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True)
        return dataframe, EventLog()

    dataframe = dataframe.sort_values(
        ["case_id", "timestamp", "_source_order"],
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
        for deviation_type in LEGACY_DEVIATION_TYPES
        if deviation_flags[deviation_type]
    ]


def _classify_path(
    activities: list[str],
) -> tuple[str, list[str], list[str]]:
    """Classify a path and return its missing and unapproved activities."""
    counts = Counter(activities)
    missing_steps = [step for step in IDEAL_PATH if counts[step] == 0]
    extra_steps = list(
        dict.fromkeys(
            activity
            for activity in activities
            if activity not in IDEAL_PATH and activity not in OPTIONAL_STEPS
        )
    )
    required_positions = [
        IDEAL_PATH.index(activity)
        for activity in activities
        if activity in IDEAL_PATH
    ]
    repeated = any(counts[step] > 1 for step in IDEAL_PATH)
    wrong_order = any(
        current < previous
        for previous, current in zip(required_positions, required_positions[1:])
    )

    if repeated:
        deviation_type = "repeated_step"
    elif wrong_order:
        deviation_type = "wrong_order"
    elif missing_steps:
        deviation_type = "skipped_step"
    elif extra_steps:
        deviation_type = "extra_step"
    else:
        deviation_type = "compliant"
    return deviation_type, missing_steps, extra_steps


def _average_token_fitness(dataframe: pd.DataFrame) -> float | None:
    """Try token replay against the ideal Petri net, if the PM4Py API supports it."""
    if dataframe.empty:
        return None

    replay = getattr(token_replay, "apply", None)
    if not callable(replay):
        warnings.warn(
            "PM4Py token-replay API is unavailable; fitness was not calculated.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None

    try:
        ordered = dataframe.sort_values(
            ["case_id", "timestamp"], kind="stable"
        ).copy()
        formatted = pm4py.format_dataframe(
            ordered,
            case_id="case_id",
            activity_key="activity",
            timestamp_key="timestamp",
        )
        event_log = pm4py.convert_to_event_log(formatted)
        net, initial_marking, final_marking = build_ideal_model()
        replay_results = replay(event_log, net, initial_marking, final_marking)
        scores = [float(result["trace_fitness"]) for result in replay_results]
        return sum(scores) / len(scores) if scores else None
    except (AttributeError, ImportError, KeyError, TypeError, ValueError) as error:
        warnings.warn(
            f"PM4Py token replay could not calculate fitness ({error}); "
            "continuing without it.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None


def analyze_conformance(
    dataframe: pd.DataFrame,
) -> tuple[list[dict[str, str | float | bool]], dict[str, int | float | None]]:
    """Classify every case and summarize compliance against the ideal pathway."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataframe]
    if missing_columns:
        raise ValueError(
            "Event log is missing required columns: " + ", ".join(missing_columns)
        )

    ordered = dataframe.copy()
    if not ordered.empty:
        ordered["timestamp"] = pd.to_datetime(
            ordered["timestamp"], utc=True, errors="raise"
        )
        ordered = ordered.sort_values(
            ["case_id", "timestamp"], kind="stable"
        )

    results: list[dict[str, str | float | bool]] = []
    for case_id, group in ordered.groupby("case_id", sort=True):
        activities = group["activity"].astype(str).tolist()
        deviation_type, missing_steps, extra_steps = _classify_path(activities)
        results.append(
            {
                "Case_ID": str(case_id),
                "actual_path": " -> ".join(activities),
                "is_compliant": deviation_type == "compliant",
                "deviation_type": deviation_type,
                "missing_steps": "; ".join(missing_steps),
                "extra_steps": "; ".join(extra_steps),
            }
        )

    average_fitness = _average_token_fitness(ordered)

    counts = Counter(str(result["deviation_type"]) for result in results)
    total_cases = len(results)
    compliant_cases = counts["compliant"]
    summary: dict[str, int | float | None] = {
        "total_cases": total_cases,
        "compliant_cases": compliant_cases,
        "non_compliant_cases": total_cases - compliant_cases,
        "pct_compliant": (
            100.0 * compliant_cases / total_cases if total_cases else 0.0
        ),
        "pct_non_compliant": (
            100.0 * (total_cases - compliant_cases) / total_cases
            if total_cases
            else 0.0
        ),
        **{
            f"{deviation_type}_count": counts[deviation_type]
            for deviation_type in DEVIATION_TYPES
        },
        "average_fitness": average_fitness,
    }
    return results, summary


def analyze_event_log(
    dataframe: pd.DataFrame,
    event_log: EventLog,
    net: PetriNet,
    initial_marking: Marking,
    final_marking: Marking,
) -> tuple[list[dict[str, str | float | bool]], float]:
    """Return per-case token fitness, compliance, deviation types, and duration."""
    replay = getattr(token_replay, "apply", None)
    if not callable(replay):
        raise RuntimeError("PM4Py token-replay API is unavailable.")
    replay_results = replay(event_log, net, initial_marking, final_marking)
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
            tuple(activities) == tuple(IDEAL_PATH)
            and bool(replay_result["trace_is_fit"])
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
    """Check all event-log cases and save case and summary CSV files."""
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Check event-log traces against the configured ideal pathway."
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
        dataframe, _ = read_event_log(args.input)
    except ValueError as error:
        parser.error(str(error))

    results, summary = analyze_conformance(dataframe)

    output_directory = directory / "output"
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "conformance_results.csv"
    summary_path = output_directory / "conformance_summary.csv"
    pd.DataFrame(results, columns=CONFORMANCE_COLUMNS).to_csv(
        output_path, index=False
    )
    pd.DataFrame([summary], columns=SUMMARY_COLUMNS).to_csv(
        summary_path, index=False
    )

    print(f"Cases analyzed: {summary['total_cases']}")
    print(f"Compliant cases: {summary['compliant_cases']}")
    print(f"Non-compliant cases: {summary['non_compliant_cases']}")
    if summary["average_fitness"] is None:
        print("Average token-replay fitness: unavailable")
    else:
        print(f"Average token-replay fitness: {summary['average_fitness']:.3f}")
    print(f"Case results saved to: {output_path}")
    print(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
