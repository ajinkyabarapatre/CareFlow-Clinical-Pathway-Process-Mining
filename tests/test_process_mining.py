"""Focused tests for the Member 3 process-mining workflow."""

from pathlib import Path

import pandas as pd
import pm4py
import pytest

from process_mining.bottleneck_analysis import (
    OUTPUT_COLUMNS as BOTTLENECK_COLUMNS,
    calculate_metrics,
    load_event_log as load_bottleneck_event_log,
)
from process_mining.conformance_check import (
    IDEAL_PATH,
    OUTPUT_COLUMNS as CONFORMANCE_COLUMNS,
    analyze_event_log,
    build_ideal_model,
    classify_deviations,
)
from process_mining.major_paths import (
    VARIANT_COLUMNS,
    build_variant_rows,
    rank_variants,
    select_major_variants,
)
from process_mining.process_discovery import (
    SUMMARY_COLUMNS,
    build_discovery_summary,
    read_event_log,
)


def event_dataframe(
    cases: dict[str, list[tuple[str, int]]],
) -> pd.DataFrame:
    """Build a small, timestamp-ordered synthetic log from offset strings."""
    rows = []
    base = pd.Timestamp("2026-01-01T08:00:00Z")
    for case_number, (case_id, events) in enumerate(cases.items()):
        for activity, minutes_after_start in events:
            rows.append(
                {
                    "case_id": case_id,
                    "activity": activity,
                    "timestamp": base
                    + pd.Timedelta(days=case_number)
                    + pd.Timedelta(minutes=int(minutes_after_start)),
                }
            )
    return pd.DataFrame(rows)


def event_log_from(dataframe: pd.DataFrame):
    """Convert a test dataframe to the PM4Py event-log representation."""
    formatted = pm4py.format_dataframe(
        dataframe.copy(),
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )
    return pm4py.convert_to_event_log(formatted)


def test_variant_ranking_counts_cases_and_exports_percentages() -> None:
    ideal = list(IDEAL_PATH)
    repeated = ["Admission", "Triage", "Triage", "Diagnosis", "Treatment", "Discharge"]
    dataframe = event_dataframe(
        {"case-1": list(zip(ideal, range(5))), "case-2": list(zip(ideal, range(5))),
         "case-3": list(zip(repeated, range(6)))}
    )

    ranked = rank_variants(dataframe)
    selected = select_major_variants(ranked, total_cases=3, top=5, coverage=0.6)
    rows = build_variant_rows(selected, total_cases=3)

    assert ranked[0] == (tuple(ideal), 2)
    assert len(selected) == 1
    assert rows[0]["case_count"] == 2
    assert rows[0]["percentage"] == pytest.approx(66.67)
    assert tuple(rows[0]) == VARIANT_COLUMNS


def test_variant_selection_respects_top_limit_and_coverage_validation() -> None:
    ranked = [(("A",), 4), (("B",), 3), (("C",), 2), (("D",), 1)]

    selected = select_major_variants(ranked, total_cases=10, top=2, coverage=0.9)

    assert selected == ranked[:2]
    with pytest.raises(ValueError, match="--top"):
        select_major_variants(ranked, total_cases=10, top=0, coverage=0.8)
    with pytest.raises(ValueError, match="--coverage"):
        select_major_variants(ranked, total_cases=10, top=4, coverage=0)


def test_bottleneck_metrics_calculate_waits_and_have_stable_csv_schema(
    tmp_path: Path,
) -> None:
    dataframe = event_dataframe(
        {
            "case-1": [("A", 0), ("B", 60), ("C", 180)],
            "case-2": [("A", 0), ("B", 180), ("C", 300)],
        }
    )
    dataframe["_source_order"] = range(len(dataframe))

    metrics = calculate_metrics(dataframe)
    transition = metrics.loc[
        (metrics["from_activity"] == "A") & (metrics["to_activity"] == "B")
    ].iloc[0]
    output_path = tmp_path / "bottlenecks.csv"
    metrics.to_csv(output_path, index=False)
    exported = pd.read_csv(output_path)

    assert transition["transition_count"] == 2
    assert transition["mean_waiting_time_hours"] == pytest.approx(2.0)
    assert transition["median_waiting_time_hours"] == pytest.approx(2.0)
    assert transition["max_waiting_time_hours"] == pytest.approx(3.0)
    assert transition["p90_waiting_time_hours"] == pytest.approx(2.8)
    assert list(exported.columns) == list(BOTTLENECK_COLUMNS)
    assert metrics["is_bottleneck"].sum() == min(3, len(metrics))


@pytest.mark.parametrize(
    ("activities", "expected"),
    [
        (list(IDEAL_PATH), []),
        (["Admission", "Triage", "Treatment", "Discharge"], ["skipped"]),
        (
            ["Admission", "Triage", "Triage", "Diagnosis", "Treatment", "Discharge"],
            ["repeated"],
        ),
        (
            ["Admission", "Diagnosis", "Triage", "Treatment", "Discharge"],
            ["out_of_order"],
        ),
        (
            [*IDEAL_PATH[:-1], "Follow-up", IDEAL_PATH[-1]],
            ["extra_activity"],
        ),
    ],
)
def test_deviation_types(activities: list[str], expected: list[str]) -> None:
    assert classify_deviations(activities) == expected


def test_trace_can_report_multiple_deviation_types() -> None:
    activities = ["Admission", "Diagnosis", "Triage", "Triage", "Follow-up"]

    assert classify_deviations(activities) == [
        "skipped",
        "repeated",
        "out_of_order",
        "extra_activity",
    ]


def test_conformance_export_contains_one_flat_row_per_case(tmp_path: Path) -> None:
    cases = {
        "compliant": list(zip(IDEAL_PATH, [0, 15, 45, 75, 120])),
        "skipped": list(
            zip(
                ["Admission", "Triage", "Treatment", "Discharge"],
                [0, 15, 75, 120],
            )
        ),
        "repeated": list(
            zip(
                ["Admission", "Triage", "Triage", "Diagnosis", "Treatment", "Discharge"],
                [0, 15, 20, 45, 75, 120],
            )
        ),
        "out-of-order": list(
            zip(
                ["Admission", "Diagnosis", "Triage", "Treatment", "Discharge"],
                [0, 15, 20, 45, 75],
            )
        ),
    }
    dataframe = event_dataframe(cases)
    results, mean_fitness = analyze_event_log(
        dataframe, event_log_from(dataframe), *build_ideal_model()
    )
    output_path = tmp_path / "conformance_results.csv"
    pd.DataFrame(results, columns=CONFORMANCE_COLUMNS).to_csv(
        output_path, index=False
    )
    exported = pd.read_csv(output_path)

    assert len(exported) == 4
    assert list(exported.columns) == list(CONFORMANCE_COLUMNS)
    assert exported.set_index("case_id").loc["compliant", "is_compliant"]
    assert not exported.set_index("case_id").loc["skipped", "is_compliant"]
    assert exported.set_index("case_id").loc["skipped", "deviation_type"] == "skipped"
    assert (
        exported.set_index("case_id").loc["repeated", "deviation_type"] == "repeated"
    )
    assert (
        exported.set_index("case_id").loc["out-of-order", "deviation_type"]
        == "out_of_order"
    )
    assert exported.set_index("case_id").loc["compliant", "trace_variant"] == (
        "Admission -> Triage -> Diagnosis -> Treatment -> Discharge"
    )
    assert exported.set_index("case_id").loc["compliant", "duration_hours"] == 2.0
    assert 0 <= mean_fitness <= 1


def test_discovery_summary_reports_case_event_and_duration_metrics() -> None:
    dataframe = event_dataframe(
        {
            "case-1": list(zip(IDEAL_PATH, [0, 15, 45, 75, 120])),
            "case-2": list(zip(IDEAL_PATH, [0, 15, 45, 75, 180])),
        }
    )

    summary = build_discovery_summary(dataframe, event_log_from(dataframe))

    assert list(summary.columns) == list(SUMMARY_COLUMNS)
    assert summary.loc[0, "cases"] == 2
    assert summary.loc[0, "events"] == 10
    assert summary.loc[0, "activities"] == 5
    assert summary.loc[0, "variants"] == 1
    assert summary.loc[0, "average_case_duration_hours"] == pytest.approx(2.5)
    assert summary.loc[0, "max_case_duration_hours"] == 3.0


def test_event_log_reader_names_bad_timestamp_csv_rows(tmp_path: Path) -> None:
    input_path = tmp_path / "bad_timestamps.csv"
    input_path.write_text(
        "case_id,activity,timestamp\ncase-1,Admission,not-a-time\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"row 2 \(invalid: 'not-a-time'\)"):
        read_event_log(input_path)


def test_bottleneck_reader_names_bad_timestamp_csv_rows(tmp_path: Path) -> None:
    input_path = tmp_path / "bad_bottleneck_timestamp.csv"
    input_path.write_text(
        "case_id,activity,timestamp\ncase-1,Admission,not-a-time\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"row 2 \(invalid: 'not-a-time'\)"):
        load_bottleneck_event_log(input_path)
