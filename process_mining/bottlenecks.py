"""Analyze activity-transition waiting times in a patient event log."""

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, median
from tempfile import TemporaryDirectory
from typing import Iterable, TextIO


REQUIRED_COLUMNS = ("case_id", "activity", "timestamp")
GROUP_COLUMNS = ("department", "patient_group")
OUTPUT_COLUMNS = (
    "group_by",
    "group_value",
    "rank",
    "from_activity",
    "to_activity",
    "avg_waiting_time_hours",
    "median_waiting_time_hours",
    "max_waiting_time_hours",
    "case_count",
    "transition_count",
)
TOP_TRANSITIONS = 10


@dataclass(frozen=True)
class Event:
    """One event and its original CSV position for deterministic tie-breaking."""

    case_id: str
    activity: str
    timestamp: datetime
    row_number: int
    dimensions: dict[str, str]


def _parse_timestamp(value: str, row_number: int) -> datetime:
    """Parse ISO-8601 timestamps, treating unzoned values as UTC."""
    if not value.strip():
        raise ValueError(f"Missing timestamp on CSV row {row_number}")
    try:
        timestamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"Invalid timestamp on CSV row {row_number}: {value!r}"
        ) from error

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _read_events(source: TextIO) -> list[Event]:
    reader = csv.DictReader(source)
    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in (reader.fieldnames or [])
    ]
    if missing:
        raise ValueError(f"Event log is missing required columns: {', '.join(missing)}")

    events = []
    for row_number, row in enumerate(reader, start=2):
        case_id = (row.get("case_id") or "").strip()
        activity = (row.get("activity") or "").strip()
        if not case_id or not activity:
            raise ValueError(
                f"CSV row {row_number} must have non-empty case_id and activity values"
            )
        dimensions = {
            column: (row.get(column) or "").strip() or "Unspecified"
            for column in GROUP_COLUMNS
            if column in (reader.fieldnames or [])
        }
        events.append(
            Event(
                case_id=case_id,
                activity=activity,
                timestamp=_parse_timestamp(row.get("timestamp") or "", row_number),
                row_number=row_number,
                dimensions=dimensions,
            )
        )
    return events


def to_pm4py_event_log(events: Iterable[Event]):
    """Convert parsed events to a PM4Py event log and its formatted dataframe."""
    import pandas as pd
    import pm4py

    rows = [
        {
            "case_id": event.case_id,
            "activity": event.activity,
            "timestamp": event.timestamp,
            "row_number": event.row_number,
            **event.dimensions,
        }
        for event in events
    ]
    dataframe = pd.DataFrame(rows)
    formatted_dataframe = pm4py.format_dataframe(
        dataframe,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )
    return pm4py.convert_to_event_log(formatted_dataframe), formatted_dataframe


def analyze_events(events: Iterable[Event]) -> list[dict[str, str | int | float]]:
    """Calculate transition metrics for all events and available group dimensions."""
    cases: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        cases[event.case_id].append(event)

    waits: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    transition_cases: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)

    for case_id, case_events in cases.items():
        case_events.sort(
            key=lambda event: (event.timestamp, event.activity, event.row_number)
        )
        for previous, current in zip(case_events, case_events[1:]):
            transition = (previous.activity, current.activity)
            waiting_hours = (
                current.timestamp - previous.timestamp
            ).total_seconds() / 3600
            scopes = [("all", "all")]
            scopes.extend(
                (column, previous.dimensions[column])
                for column in GROUP_COLUMNS
                if column in previous.dimensions
            )
            for group_by, group_value in scopes:
                key = (
                    group_by,
                    group_value,
                    transition[0],
                    transition[1],
                )
                waits[key].append(waiting_hours)
                transition_cases[key].add(case_id)

    unsorted_results = []
    for key, transition_waits in waits.items():
        group_by, group_value, from_activity, to_activity = key
        unsorted_results.append(
            {
                "group_by": group_by,
                "group_value": group_value,
                "from_activity": from_activity,
                "to_activity": to_activity,
                "avg_waiting_time_hours": round(fmean(transition_waits), 3),
                "median_waiting_time_hours": round(median(transition_waits), 3),
                "max_waiting_time_hours": round(max(transition_waits), 3),
                "case_count": len(transition_cases[key]),
                "transition_count": len(transition_waits),
            }
        )

    by_scope: dict[tuple[str, str], list[dict[str, str | int | float]]] = defaultdict(list)
    for result in unsorted_results:
        by_scope[(str(result["group_by"]), str(result["group_value"]))].append(result)

    results = []
    for scope_results in by_scope.values():
        scope_results.sort(
            key=lambda result: (
                -float(result["avg_waiting_time_hours"]),
                -float(result["median_waiting_time_hours"]),
                -float(result["max_waiting_time_hours"]),
                str(result["from_activity"]),
                str(result["to_activity"]),
            )
        )
        for rank, result in enumerate(scope_results, start=1):
            results.append({**result, "rank": rank})

    results.sort(
        key=lambda result: (
            str(result["group_by"]) != "all",
            str(result["group_by"]),
            str(result["group_value"]),
            int(result["rank"]),
        )
    )
    return results


def analyze_csv(input_path: Path) -> list[dict[str, str | int | float]]:
    """Read a CSV event log and calculate its transition metrics."""
    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        return analyze_events(_read_events(source))


def write_results(
    results: list[dict[str, str | int | float]], output_path: Path
) -> None:
    """Write ranked metrics to CSV, creating the output directory if needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(results)


def write_chart(
    results: list[dict[str, str | int | float]], output_path: Path
) -> None:
    """Save a horizontal chart of the ten slowest ungrouped transitions."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top_results = [
        result for result in results if result["group_by"] == "all"
    ][:TOP_TRANSITIONS]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(figsize=(11, max(4, 0.55 * len(top_results) + 1.5)))
    if top_results:
        labels = [
            f"{result['from_activity']} -> {result['to_activity']}"
            for result in reversed(top_results)
        ]
        values = [
            float(result["avg_waiting_time_hours"])
            for result in reversed(top_results)
        ]
        axes.barh(labels, values, color="#2878B5")
        axes.set_xlabel("Average waiting time (hours)")
        axes.set_title("Top 10 Bottlenecks by Average Waiting Time")
    else:
        axes.text(0.5, 0.5, "No activity transitions found", ha="center", va="center")
        axes.set_axis_off()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def verify() -> None:
    """Check duplicate-time ordering, metrics, PM4Py conversion, and output files."""
    from io import StringIO

    csv_source = StringIO(
        "case_id,activity,timestamp,department,patient_group\n"
        "case-1,Registration,2026-01-01T00:00:00Z,ED,adult\n"
        "case-1,Assessment,2026-01-01T01:00:00Z,ED,adult\n"
        "case-1,Assessment,2026-01-01T01:00:00Z,ED,adult\n"
        "case-1,Discharge,2026-01-01T03:00:00Z,ED,adult\n"
        "case-2,Registration,2026-01-02T00:00:00Z,ED,pediatric\n"
        "case-2,Assessment,2026-01-02T02:00:00Z,ED,pediatric\n"
    )
    events = _read_events(csv_source)
    results = analyze_events(events)
    registration_to_assessment = next(
        result
        for result in results
        if result["group_by"] == "all"
        and result["from_activity"] == "Registration"
        and result["to_activity"] == "Assessment"
    )
    expected_metrics = {
        "avg_waiting_time_hours": 1.5,
        "median_waiting_time_hours": 1.5,
        "max_waiting_time_hours": 2.0,
        "case_count": 2,
        "transition_count": 2,
    }
    assert all(
        registration_to_assessment[key] == value
        for key, value in expected_metrics.items()
    ), f"Unexpected transition metrics: {registration_to_assessment!r}"
    assert any(
        result["group_by"] == "all"
        and result["from_activity"] == "Assessment"
        and result["to_activity"] == "Assessment"
        and result["max_waiting_time_hours"] == 0
        for result in results
    ), "Events with equal timestamps must produce zero-hour waits"
    assert any(
        result["group_by"] == "patient_group"
        and result["group_value"] == "adult"
        for result in results
    ), "Expected patient-group breakdown was not generated"

    event_log, dataframe = to_pm4py_event_log(events)
    assert len(dataframe) == len(events)
    assert sum(len(trace) for trace in event_log) == len(events)

    with TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)
        csv_path = temporary_path / "bottlenecks.csv"
        chart_path = temporary_path / "bottlenecks.png"
        write_results(results, csv_path)
        write_chart(results, chart_path)
        assert csv_path.is_file()
        assert chart_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    try:
        _parse_timestamp("", 2)
    except ValueError as error:
        assert "Missing timestamp" in str(error)
    else:
        raise AssertionError("Missing timestamps must be reported")
    print("Verification passed: metrics, duplicate timestamps, groups, PM4Py, and outputs.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate waiting-time bottlenecks between event-log activities."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="CSV event log containing case_id, activity, and timestamp columns",
    )
    output_directory = Path(__file__).resolve().parent / "output"
    parser.add_argument(
        "--output",
        type=Path,
        default=output_directory / "ranked_bottlenecks.csv",
        help="Output CSV path (default: process_mining/output/ranked_bottlenecks.csv)",
    )
    parser.add_argument(
        "--chart-output",
        type=Path,
        default=output_directory / "ranked_bottlenecks.png",
        help="Output chart path (default: process_mining/output/ranked_bottlenecks.png)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run synthetic checks without needing a patient event-log file",
    )
    args = parser.parse_args()

    if args.verify:
        if args.input is not None:
            parser.error("--verify cannot be combined with --input")
        verify()
        return
    if args.input is None:
        parser.error("provide --input EVENT_LOG.csv or use --verify")
    if not args.input.is_file():
        parser.error(f"event-log file does not exist: {args.input}")

    with args.input.open("r", encoding="utf-8-sig", newline="") as source:
        events = _read_events(source)
    event_log, dataframe = to_pm4py_event_log(events)
    results = analyze_events(events)
    write_results(results, args.output)
    write_chart(results, args.chart_output)
    case_count = len(event_log)
    top_results = [
        result for result in results if result["group_by"] == "all"
    ][:TOP_TRANSITIONS]
    print(
        f"Loaded {len(dataframe)} events across {case_count} cases into PM4Py; "
        f"ranked {len(top_results)} bottlenecks."
    )
    print(f"Wrote {len(results)} ranked rows to {args.output}")
    print(f"Wrote the top-transition chart to {args.chart_output}")


if __name__ == "__main__":
    main()
