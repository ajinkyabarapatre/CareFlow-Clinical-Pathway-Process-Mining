"""Tests for dashboard helper functions and sample-log KPIs."""

from pathlib import Path

import pytest

from process_mining.dashboard_app import (
    calculate_dashboard_kpis,
    load_dashboard_event_log,
)


SAMPLE_EVENT_LOG = (
    Path(__file__).resolve().parents[1]
    / "process_mining"
    / "sample_event_log.csv"
)


def test_sample_event_log_dashboard_kpis() -> None:
    """The dashboard KPIs should match the checked-in sample event log."""
    dataframe = load_dashboard_event_log(SAMPLE_EVENT_LOG)
    kpis = calculate_dashboard_kpis(dataframe)

    assert kpis["total_cases"] == 4
    assert kpis["total_events"] == 20
    assert kpis["avg_case_duration_minutes"] == pytest.approx(120.0)
    assert kpis["pct_cases_with_loopback"] == pytest.approx(25.0)
    assert kpis["pct_compliant"] == pytest.approx(25.0)
    assert kpis["pct_non_compliant"] == pytest.approx(75.0)
