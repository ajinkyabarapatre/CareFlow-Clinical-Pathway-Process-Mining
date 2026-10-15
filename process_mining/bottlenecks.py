"""Summarize waiting times and case counts between consecutive event-log activities."""

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, median
from typing import Iterable, TextIO


OUTPUT_COLUMNS = (
    "from_activity",
    "to_activity",
    "avg_waiting_time_hours",
    "median_waiting_time_hours",
    "case_count",
    "transition_count",
)
REQUIRED_COLUMNS = ("case_id", "activity", "timestamp")


def _parse_timestamp(value: str, row_number: int) -> datetime:
    """Parse an ISO-8601 timestamp, treating timestamps without a zone as UTC."""
    try:
        timestamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            f"Invalid timestamp on CSV row {row_number}: {value!r}"
        ) from error

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _read_events(source: TextIO) -> list[tuple[str, str, datetime, int]]:
    reader = csv.DictReader(source)
    missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"Event log is missing required columns: {', '.join(missing)}")

    events = []
    for row_number, row in enumerate(reader, start=2):
        case_id = (row["case_id"] or "").strip()
        activity = (row["activity"] or "").strip()
        if not case_id or not activity:
            raise ValueError(
                f"CSV row {row_number} must have non-empty case_id and activity values"
            )
        timestamp = _parse_timestamp(row["timestamp"] or "", row_number)
        events.append((case_id, activity, timestamp, row_number))
    return events


def analyze_events(
    events: Iterable[tuple[str, str, datetime, int]],
) -> list[dict[str, str | int | float]]:
    """Aggregate average/median wait and counts for each consecutive activity pair."""
    cases: dict[str, list[tuple[str, datetime, int]]] = defaultdict(list)
    for case_id, activity, timestamp, row_number in events:
        cases[case_id].append((activity, timestamp, row_number))

    waits_by_transition: dict[tuple[str, str], list[float]] = defaultdict(list)
    cases_by_transition: dict[tuple[str, str], set[str]] = defaultdict(set)

    for case_id, case_events in cases.items():
        case_events.sort(key=lambda event: (event[1], event[2]))
        for previous, current in zip(case_events, case_events[1:]):
            from_activity, previous_time, _ = previous
            to_activity, current_time, _ = current
            transition = (from_activity, to_activity)
            waiting_hours = (current_time - previous_time).total_seconds() / 3600
            waits_by_transition[transition].append(waiting_hours)
            cases_by_transition[transition].add(case_id)

    results = []
    for (from_activity, to_activity), waits in sorted(waits_by_transition.items()):
        results.append(
            {
                "from_activity": from_activity,
                "to_activity": to_activity,
                "avg_waiting_time_hours": round(fmean(waits), 3),
                "median_waiting_time_hours": round(median(waits), 3),
                "case_count": len(cases_by_transition[(from_activity, to_activity)]),
                "transition_count": len(waits),
            }
        )
    return results


def analyze_csv(input_path: Path) -> list[dict[str, str | int | float]]:
    """Read and analyze a CSV event log with case_id, activity, and timestamp columns."""
    with input_path.open("r", encoding="utf-8-sig", newline="") as source:
        return analyze_events(_read_events(source))


def write_results(
    results: list[dict[str, str | int | float]], output_path: Path
) -> None:
    """Write transition metrics to a CSV file, creating its parent directory."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(results)


def verify() -> None:
    """Check transition calculations against a small synthetic event log."""
    sample_events = [
        ("case-1", "Registration", datetime(2026, 1, 1, tzinfo=timezone.utc), 2),
        ("case-1", "Assessment", datetime(2026, 1, 1, 1, tzinfo=timezone.utc), 3),
        ("case-1", "Discharge", datetime(2026, 1, 1, 3, tzinfo=timezone.utc), 4),
        ("case-2", "Registration", datetime(2026, 1, 2, tzinfo=timezone.utc), 5),
        ("case-2", "Assessment", datetime(2026, 1, 2, 2, tzinfo=timezone.utc), 6),
    ]
    results = analyze_events(sample_events)
    expected = [
        {
            "from_activity": "Assessment",
            "to_activity": "Discharge",
            "avg_waiting_time_hours": 2.0,
            "median_waiting_time_hours": 2.0,
            "case_count": 1,
            "transition_count": 1,
        },
        {
            "from_activity": "Registration",
            "to_activity": "Assessment",
            "avg_waiting_time_hours": 1.5,
            "median_waiting_time_hours": 1.5,
            "case_count": 2,
            "transition_count": 2,
        },
    ]
    assert results == expected, f"Unexpected transition metrics: {results!r}"
    print("Verification passed: average/median wait and case counts match.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate waiting-time bottlenecks between event-log activities."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="CSV event log containing case_id, activity, and timestamp columns",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs" / "bottlenecks.csv",
        help="Output CSV path (default: process_mining/outputs/bottlenecks.csv)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run a synthetic self-check without needing an event-log file",
    )
    args = parser.parse_args()

    if args.verify:
        if args.input is not None:
            parser.error("--verify cannot be combined with --input")
        verify()
        return
    if args.input is None:
        parser.error("provide --input EVENT_LOG.csv or use --verify")

    results = analyze_csv(args.input)
    write_results(results, args.output)
    print(f"Wrote {len(results)} activity transitions to {args.output}")


if __name__ == "__main__":
    main()
