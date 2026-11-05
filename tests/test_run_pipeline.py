"""Tests for runner status reporting using temporary scripts."""

import csv
from pathlib import Path

from process_mining import run_pipeline


def make_step(tmp_path: Path, name: str, source: str):
    script = tmp_path / f"{name}.py"
    script.write_text(source, encoding="utf-8")
    output = tmp_path / f"{name}.csv"
    return run_pipeline.PipelineStep(name, script, (output,), accepts_input=False), output


def test_missing_script_is_skipped(tmp_path: Path, monkeypatch) -> None:
    missing = run_pipeline.PipelineStep(
        "missing", tmp_path / "missing.py", (), accepts_input=False
    )
    monkeypatch.setattr(run_pipeline, "PIPELINE_STEPS", [missing])
    monkeypatch.setattr(run_pipeline, "OUTPUT_DIRECTORY", tmp_path)

    results = run_pipeline.run_pipeline(Path("sample.csv"))

    assert results[0].status == "skipped"


def test_failing_script_is_reported_as_failed(tmp_path: Path, monkeypatch) -> None:
    step, _ = make_step(tmp_path, "failure", "raise SystemExit(2)\n")
    monkeypatch.setattr(run_pipeline, "PIPELINE_STEPS", [step])
    monkeypatch.setattr(run_pipeline, "OUTPUT_DIRECTORY", tmp_path)

    results = run_pipeline.run_pipeline(Path("sample.csv"))

    assert results[0].status == "failed"


def test_summary_csv_has_expected_columns(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "success.csv"
    step, expected_output = make_step(
        tmp_path,
        "success",
        "from pathlib import Path\n"
        f"Path({str(output_path)!r}).write_text('ok', encoding='utf-8')\n",
    )
    monkeypatch.setattr(run_pipeline, "PIPELINE_STEPS", [step])
    monkeypatch.setattr(run_pipeline, "OUTPUT_DIRECTORY", tmp_path)

    run_pipeline.run_pipeline(Path("sample.csv"))

    assert expected_output.is_file()
    with (tmp_path / "pipeline_summary.csv").open(
        newline="", encoding="utf-8"
    ) as summary_file:
        rows = csv.DictReader(summary_file)
        assert rows.fieldnames == list(run_pipeline.SUMMARY_COLUMNS)
        assert next(rows)["status"] == "passed"
