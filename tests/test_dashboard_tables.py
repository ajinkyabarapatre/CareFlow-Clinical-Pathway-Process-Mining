"""Tests for the Week 3 dashboard table exports."""

from pathlib import Path

import pandas as pd
import pytest

from process_mining.build_dashboard_tables import (
    TABLE_COLUMNS,
    build_dashboard_tables,
)
from process_mining.process_discovery import read_event_log


SAMPLE_EVENT_LOG = (
    Path(__file__).resolve().parents[1]
    / "process_mining"
    / "sample_event_log.csv"
)


@pytest.fixture
def dashboard_tables() -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Build all dashboard tables from the checked-in sample event log."""
    event_log, _ = read_event_log(SAMPLE_EVENT_LOG)
    return event_log, build_dashboard_tables(event_log)


def test_variant_summary_covers_all_cases(
    dashboard_tables: tuple[pd.DataFrame, dict[str, pd.DataFrame]],
) -> None:
    _, tables = dashboard_tables
    assert tables["variant_summary"]["case_count"].sum() == 4
    assert tables["variant_summary"]["case_count"].sum() == tables[
        "case_summary"
    ]["case_id"].nunique()


def test_variant_percentages_sum_to_one_hundred(
    dashboard_tables: tuple[pd.DataFrame, dict[str, pd.DataFrame]],
) -> None:
    _, tables = dashboard_tables
    assert tables["variant_summary"]["pct_of_cases"].sum() == pytest.approx(100)


def test_case_durations_are_nonnegative(
    dashboard_tables: tuple[pd.DataFrame, dict[str, pd.DataFrame]],
) -> None:
    _, tables = dashboard_tables
    assert (tables["case_summary"]["total_duration_minutes"] >= 0).all()


def test_kpi_event_count_matches_event_log(
    dashboard_tables: tuple[pd.DataFrame, dict[str, pd.DataFrame]],
) -> None:
    event_log, tables = dashboard_tables
    assert tables["kpi_summary"].loc[0, "total_events"] == len(event_log)


def test_all_dashboard_tables_have_expected_columns(
    dashboard_tables: tuple[pd.DataFrame, dict[str, pd.DataFrame]],
) -> None:
    _, tables = dashboard_tables
    assert set(tables) == set(TABLE_COLUMNS)
    for table_name, expected_columns in TABLE_COLUMNS.items():
        assert tuple(tables[table_name].columns) == expected_columns
