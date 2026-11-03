from pathlib import Path


def test_bottleneck_sql_views_use_case_ordered_transitions() -> None:
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "06_bottleneck_views.sql"
    sql = sql_path.read_text(encoding="utf-8")

    assert "vw_transition_times" in sql
    assert "vw_bottleneck_summary" in sql
    assert "vw_loopbacks" in sql
    assert "LEAD(" in sql
    assert "PARTITION BY Case_ID" in sql
