"""Tests for the configurable Week 4 conformance checker."""

from pathlib import Path
import sys

import pandas as pd
import pytest

from process_mining.conformance_check import (
    CONFORMANCE_COLUMNS,
    IDEAL_PATH,
    SUMMARY_COLUMNS,
    analyze_conformance,
)
from process_mining.export_for_powerbi import (
    CONFORMANCE_CASE_COLUMNS,
    CONFORMANCE_SUMMARY_COLUMNS,
    export_conformance_csvs,
    main as export_for_powerbi_main,
)


def event_log(activities: list[str]) -> pd.DataFrame:
    """Create one timestamped case from an ordered list of activities."""
    start = pd.Timestamp("2026-11-01T08:00:00Z")
    return pd.DataFrame(
        [
            {
                "case_id": "case-1",
                "activity": activity,
                "timestamp": start + pd.Timedelta(minutes=offset * 10),
            }
            for offset, activity in enumerate(activities)
        ],
        columns=("case_id", "activity", "timestamp"),
    )


def test_perfectly_ideal_case_is_compliant() -> None:
    results, summary = analyze_conformance(event_log(IDEAL_PATH))

    assert results[0]["actual_path"] == " -> ".join(IDEAL_PATH)
    assert results[0]["is_compliant"] is True
    assert results[0]["deviation_type"] == "compliant"
    assert results[0]["missing_steps"] == ""
    assert results[0]["extra_steps"] == ""
    assert summary["compliant_cases"] == 1
    assert tuple(results[0]) == CONFORMANCE_COLUMNS
    assert tuple(summary) == SUMMARY_COLUMNS


def test_missing_mandatory_activity_is_a_skipped_step() -> None:
    activities = [IDEAL_PATH[0], IDEAL_PATH[1], IDEAL_PATH[-1]]
    results, _ = analyze_conformance(event_log(activities))

    assert results[0]["deviation_type"] == "skipped_step"
    assert results[0]["missing_steps"] == "; ".join(IDEAL_PATH[2:-1])


def test_mandatory_activities_in_wrong_order_are_flagged() -> None:
    activities = [IDEAL_PATH[0], IDEAL_PATH[2], IDEAL_PATH[1], IDEAL_PATH[-1]]
    results, _ = analyze_conformance(event_log(activities))

    assert results[0]["deviation_type"] == "wrong_order"
    assert results[0]["missing_steps"] == IDEAL_PATH[-2]


def test_returning_to_an_earlier_activity_is_a_loop_back() -> None:
    activities = [
        IDEAL_PATH[0],
        IDEAL_PATH[1],
        IDEAL_PATH[2],
        IDEAL_PATH[1],
        *IDEAL_PATH[3:],
    ]
    results, _ = analyze_conformance(event_log(activities))

    assert results[0]["deviation_type"] == "repeated_step"


def test_allowed_optional_activity_does_not_make_case_non_compliant() -> None:
    activities = [*IDEAL_PATH[:2], "X-Ray", *IDEAL_PATH[2:]]
    results, _ = analyze_conformance(event_log(activities))

    assert results[0]["is_compliant"] is True


def test_unapproved_activity_is_reported_as_an_extra_step() -> None:
    activities = [*IDEAL_PATH[:-1], "Unapproved", IDEAL_PATH[-1]]
    results, _ = analyze_conformance(event_log(activities))

    assert results[0]["deviation_type"] == "extra_step"
    assert results[0]["extra_steps"] == "Unapproved"


def test_empty_log_has_zero_cases_and_zero_percentages() -> None:
    empty_log = pd.DataFrame(columns=("case_id", "activity", "timestamp"))

    results, summary = analyze_conformance(empty_log)

    assert results == []
    assert summary["total_cases"] == 0
    assert summary["compliant_cases"] + summary["non_compliant_cases"] == 0
    assert summary["pct_compliant"] == 0
    assert summary["pct_non_compliant"] == 0


def test_case_counts_balance_and_powerbi_exports_are_snake_case(
    tmp_path: Path,
) -> None:
    cases = pd.concat(
        [
            event_log(IDEAL_PATH).assign(case_id="compliant"),
            event_log([IDEAL_PATH[0], IDEAL_PATH[1], IDEAL_PATH[-1]]).assign(
                case_id="skipped"
            ),
            event_log(
                [IDEAL_PATH[0], IDEAL_PATH[2], IDEAL_PATH[1], IDEAL_PATH[-1]]
            ).assign(case_id="wrong-order"),
        ],
        ignore_index=True,
    )
    results, summary = analyze_conformance(cases)
    assert summary["compliant_cases"] + summary["non_compliant_cases"] == (
        summary["total_cases"]
    )

    output_directory = tmp_path / "output"
    cases_path = tmp_path / "conformance_results.csv"
    summary_path = tmp_path / "conformance_summary.csv"
    pd.DataFrame(results, columns=CONFORMANCE_COLUMNS).to_csv(
        cases_path, index=False
    )
    pd.DataFrame([summary], columns=SUMMARY_COLUMNS).to_csv(
        summary_path, index=False
    )
    non_compliant_path, exported_summary_path = export_conformance_csvs(
        cases_path, output_directory, summary_path
    )
    non_compliant = pd.read_csv(non_compliant_path)
    exported_summary = pd.read_csv(exported_summary_path)

    assert tuple(non_compliant.columns) == CONFORMANCE_CASE_COLUMNS
    assert tuple(exported_summary.columns) == CONFORMANCE_SUMMARY_COLUMNS
    assert len(non_compliant) == 2
    assert exported_summary.loc[0, "total_cases"] == 3
    assert exported_summary.loc[0, "compliant_cases"] == 1
    assert not any(
        column.startswith("Unnamed:")
        for column in (*non_compliant.columns, *exported_summary.columns)
    )


def test_powerbi_exporter_can_run_without_bottleneck_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cases_path = tmp_path / "conformance_results.csv"
    pd.DataFrame(
        [
            {
                "Case_ID": "case-1",
                "actual_path": "Admission -> Discharge",
                "is_compliant": False,
                "deviation_type": "skipped_step",
                "missing_steps": "Triage",
                "extra_steps": "",
            }
        ]
    ).to_csv(cases_path, index=False)
    output_directory = tmp_path / "output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "export_for_powerbi.py",
            "--input",
            str(tmp_path / "missing_bottlenecks.csv"),
            "--conformance-input",
            str(cases_path),
            "--conformance-summary",
            str(tmp_path / "missing_summary.csv"),
            "--output-directory",
            str(output_directory),
        ],
    )

    export_for_powerbi_main()

    assert (output_directory / "non_compliant_cases.csv").is_file()
    assert (output_directory / "conformance_summary.csv").is_file()
