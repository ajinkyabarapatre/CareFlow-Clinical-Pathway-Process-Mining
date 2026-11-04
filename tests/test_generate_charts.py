"""Tests for dashboard charts and KPI summaries."""

from pathlib import Path

import pandas as pd
import pytest

from process_mining.generate_charts import (
    CASE_COL,
    build_transitions,
    kpi_table,
    load_event_log,
    variant_table,
)


SAMPLE_LOG = (
    Path(__file__).resolve().parents[1]
    / "process_mining"
    / "sample_event_log.csv"
)


def test_transitions_cover_each_case_step_and_have_no_negative_waits() -> None:
    events = load_event_log(SAMPLE_LOG)
    transitions = build_transitions(events)

    assert len(transitions) == len(events) - events[CASE_COL].nunique()
    assert (transitions["wait_minutes"] >= 0).all()


def test_variant_percentages_cover_all_cases_and_kpi_case_count_matches() -> None:
    events = load_event_log(SAMPLE_LOG)

    variants = variant_table(events)
    kpis = kpi_table(events)

    assert variants["pct_of_cases"].sum() == pytest.approx(100)
    assert kpis.loc[0, "total_cases"] == events[CASE_COL].nunique()
    assert variants.loc[0, "variant_id"] == "V1"


def test_empty_event_log_has_a_clear_error(tmp_path: Path) -> None:
    empty_log = tmp_path / "empty.csv"
    empty_log.write_text("case_id,activity,timestamp\n", encoding="utf-8")

    with pytest.raises(ValueError, match="contains no events"):
        load_event_log(empty_log)
