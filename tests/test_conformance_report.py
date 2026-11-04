"""Tests for the standalone conformance report."""

from pathlib import Path

import pandas as pd
import pytest

from process_mining.conformance_report import (
    IDEAL_PATH,
    build_case_table,
    build_summary,
    check_case,
    load_event_log,
)


def test_ideal_case_is_compliant() -> None:
    result = check_case(IDEAL_PATH)

    assert result["is_compliant"] is True
    assert result["deviation_type"] == "compliant"
    assert result["actual_path"] == IDEAL_PATH


def test_missing_required_activity_is_a_skipped_step() -> None:
    result = check_case(["Admission", "Triage", "Treatment", "Discharge"])

    assert result["deviation_type"] == "skipped_step"
    assert result["missing_steps"] == ["Diagnosis"]


def test_activities_in_wrong_order_are_detected() -> None:
    result = check_case(
        ["Admission", "Diagnosis", "Triage", "Treatment", "Discharge"]
    )

    assert result["deviation_type"] == "wrong_order"


def test_repeated_activity_is_a_loop_back() -> None:
    result = check_case(
        ["Admission", "Triage", "Triage", "Diagnosis", "Treatment", "Discharge"]
    )

    assert result["deviation_type"] == "loop_back"


def test_unrecognized_activity_is_an_extra_step() -> None:
    result = check_case(
        ["Admission", "Triage", "Diagnosis", "Follow-up", "Treatment", "Discharge"]
    )

    assert result["deviation_type"] == "extra_step"
    assert result["extra_steps"] == ["Follow-up"]


def test_empty_log_has_zero_cases_and_clear_percentages(tmp_path: Path) -> None:
    empty_csv = tmp_path / "empty_event_log.csv"
    empty_csv.write_text("case_id,activity,timestamp\n", encoding="utf-8")

    case_table = build_case_table(load_event_log(empty_csv))
    summary = build_summary(case_table)

    assert case_table.empty
    assert summary["total_cases"] == 0
    assert summary["pct_compliant"] == 0
    assert summary["pct_non_compliant"] == 0


def test_case_counts_balance_and_missing_columns_are_clear() -> None:
    event_log = pd.DataFrame(
        [
            {"case_id": "good", "activity": step, "timestamp": f"2026-01-01T08:{i:02}:00Z"}
            for i, step in enumerate(IDEAL_PATH)
        ]
        + [
            {"case_id": "skipped", "activity": step, "timestamp": f"2026-01-02T08:{i:02}:00Z"}
            for i, step in enumerate(
                ["Admission", "Triage", "Treatment", "Discharge"]
            )
        ]
    )
    summary = build_summary(build_case_table(event_log))

    assert summary["compliant_cases"] + summary["non_compliant_cases"] == (
        summary["total_cases"]
    )
    with pytest.raises(ValueError, match="missing required columns"):
        build_case_table(pd.DataFrame(columns=["case_id", "activity"]))
