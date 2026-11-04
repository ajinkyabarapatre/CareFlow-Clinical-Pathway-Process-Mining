"""Create a simple, per-patient conformance report from an event-log CSV."""

from collections import Counter
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "sample_event_log.csv"
OUTPUT_DIR = BASE_DIR / "output"
CASE_COL = "case_id"
ACTIVITY_COL = "activity"
TIME_COL = "timestamp"
IDEAL_PATH = ["Admission", "Triage", "Diagnosis", "Treatment", "Discharge"]
OPTIONAL_STEPS = {"X-Ray", "Lab"}

CASE_COLUMNS = (
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
    "compliant_count",
    "skipped_step_count",
    "extra_step_count",
    "loop_back_count",
    "wrong_order_count",
)
DEVIATION_TYPES = (
    "compliant",
    "skipped_step",
    "extra_step",
    "loop_back",
    "wrong_order",
)
REQUIRED_COLUMNS = (CASE_COL, ACTIVITY_COL, TIME_COL)


def _validate_and_sort(event_log: pd.DataFrame) -> pd.DataFrame:
    """Validate the required CSV fields and return events in case/time order."""
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in event_log.columns
    ]
    if missing_columns:
        raise ValueError(
            "Event log is missing required columns: "
            + ", ".join(missing_columns)
        )

    ordered = event_log.copy()
    for column in (CASE_COL, ACTIVITY_COL):
        ordered[column] = ordered[column].astype("string").str.strip()
        invalid_values = ordered[column].isna() | ordered[column].eq("")
        if invalid_values.any():
            raise ValueError(f"Event log contains an empty {column} value.")

    raw_timestamps = ordered[TIME_COL]
    timestamps = pd.to_datetime(raw_timestamps, utc=True, errors="coerce")
    if timestamps.isna().any():
        raise ValueError(
            f"Event log contains an empty or invalid {TIME_COL} value."
        )

    ordered[TIME_COL] = timestamps
    ordered["_source_order"] = range(len(ordered))
    ordered = ordered.sort_values(
        [CASE_COL, TIME_COL, "_source_order"], kind="stable"
    )
    return ordered.drop(columns="_source_order").reset_index(drop=True)


def load_event_log(input_file: Path = INPUT_FILE) -> pd.DataFrame:
    """Read, validate, and sort an event-log CSV by case and timestamp."""
    try:
        event_log = pd.read_csv(input_file)
    except (
        OSError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as error:
        raise ValueError(
            f"Could not read event-log CSV '{input_file}': {error}"
        ) from error
    return _validate_and_sort(event_log)


def get_actual_paths(event_log: pd.DataFrame) -> dict[str, list[str]]:
    """Return each patient's activities in timestamp order."""
    ordered = _validate_and_sort(event_log)
    return {
        str(case_id): group[ACTIVITY_COL].astype(str).tolist()
        for case_id, group in ordered.groupby(CASE_COL, sort=False)
    }


def check_case(actual_path: list[str]) -> dict[str, bool | str | list[str]]:
    """Classify a path and report its required and unapproved activities."""
    activity_counts = Counter(actual_path)
    missing_steps = [
        step for step in IDEAL_PATH if activity_counts[step] == 0
    ]
    extra_steps = list(
        dict.fromkeys(
            activity
            for activity in actual_path
            if activity not in IDEAL_PATH and activity not in OPTIONAL_STEPS
        )
    )

    ideal_positions = [
        IDEAL_PATH.index(activity)
        for activity in actual_path
        if activity in IDEAL_PATH
    ]
    has_loop_back = any(count > 1 for count in activity_counts.values())
    has_wrong_order = any(
        current < previous
        for previous, current in zip(ideal_positions, ideal_positions[1:])
    )

    # Use one primary label per case; missing and extra steps remain visible.
    if has_loop_back:
        deviation_type = "loop_back"
    elif has_wrong_order:
        deviation_type = "wrong_order"
    elif missing_steps:
        deviation_type = "skipped_step"
    elif extra_steps:
        deviation_type = "extra_step"
    else:
        deviation_type = "compliant"

    return {
        "actual_path": list(actual_path),
        "is_compliant": deviation_type == "compliant",
        "deviation_type": deviation_type,
        "missing_steps": missing_steps,
        "extra_steps": extra_steps,
    }


def build_case_table(event_log: pd.DataFrame) -> pd.DataFrame:
    """Build one report row for each patient in the event log."""
    paths = get_actual_paths(event_log)
    rows = []
    for case_id, actual_path in paths.items():
        result = check_case(actual_path)
        rows.append(
            {
                "Case_ID": case_id,
                "actual_path": " -> ".join(actual_path),
                "is_compliant": result["is_compliant"],
                "deviation_type": result["deviation_type"],
                "missing_steps": "; ".join(result["missing_steps"]),
                "extra_steps": "; ".join(result["extra_steps"]),
            }
        )
    return pd.DataFrame(rows, columns=CASE_COLUMNS)


def build_summary(case_table: pd.DataFrame) -> dict[str, int | float]:
    """Count cases and calculate compliance percentages, including empty logs."""
    deviation_counts = case_table["deviation_type"].value_counts()
    total_cases = len(case_table)
    compliant_cases = int(
        case_table["is_compliant"].astype(bool).sum()
    )
    non_compliant_cases = total_cases - compliant_cases
    return {
        "total_cases": total_cases,
        "compliant_cases": compliant_cases,
        "non_compliant_cases": non_compliant_cases,
        "pct_compliant": (
            100.0 * compliant_cases / total_cases if total_cases else 0.0
        ),
        "pct_non_compliant": (
            100.0 * non_compliant_cases / total_cases if total_cases else 0.0
        ),
        **{
            f"{deviation_type}_count": int(
                deviation_counts.get(deviation_type, 0)
            )
            for deviation_type in DEVIATION_TYPES
        },
    }


def main() -> None:
    """Print the report and save case-level and summary CSV files."""
    event_log = load_event_log()
    case_table = build_case_table(event_log)
    summary = build_summary(case_table)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cases_path = OUTPUT_DIR / "conformance_report_cases.csv"
    summary_path = OUTPUT_DIR / "conformance_report_summary.csv"
    export_table = case_table.rename(columns={"Case_ID": "case_id"})
    export_table.to_csv(cases_path, index=False)
    pd.DataFrame([summary], columns=SUMMARY_COLUMNS).to_csv(
        summary_path, index=False
    )

    print("Case results:")
    print(export_table.to_string(index=False))
    print("\nSummary:")
    for name, value in summary.items():
        print(f"{name}: {value}")
    print(f"\nCase report saved to: {cases_path}")
    print(f"Summary report saved to: {summary_path}")


if __name__ == "__main__":
    main()
