"""Export Week 3 bottleneck metrics as Power BI-ready CSV files."""

import argparse
from pathlib import Path

import pandas as pd


TRANSITION_COLUMNS = (
    "from_activity",
    "to_activity",
    "transition_count",
    "avg_wait_minutes",
    "median_wait_minutes",
    "p90_wait_minutes",
    "max_wait_minutes",
    "bottleneck_rank",
)
LOOPBACK_COLUMNS = (
    "from_activity",
    "to_activity",
    "loopback_count",
    "cases_affected",
    "percent_cases_affected",
)
CONFORMANCE_CASE_COLUMNS = (
    "case_id",
    "actual_path",
    "is_compliant",
    "deviation_type",
    "missing_steps",
    "extra_steps",
)
CONFORMANCE_SUMMARY_COLUMNS = (
    "total_cases",
    "compliant_cases",
    "non_compliant_cases",
    "pct_compliant",
    "pct_non_compliant",
    "compliant_count",
    "skipped_step_count",
    "wrong_order_count",
    "repeated_step_count",
    "extra_step_count",
    "average_fitness",
)
REQUIRED_METRIC_COLUMNS = (
    *TRANSITION_COLUMNS[:-1],
    "bottleneck_rank",
    "loop_back_count",
    "loop_back_case_count",
    "pct_of_cases_affected",
)


def build_powerbi_exports(
    metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the transition and loop-back tables from calculated metrics."""
    missing_columns = [
        column for column in REQUIRED_METRIC_COLUMNS if column not in metrics
    ]
    if missing_columns:
        raise ValueError(
            "Bottleneck metrics are missing required columns: "
            + ", ".join(missing_columns)
        )

    transitions = metrics.loc[:, list(TRANSITION_COLUMNS)].copy()
    transitions = transitions.sort_values(
        "bottleneck_rank", kind="stable"
    ).reset_index(drop=True)

    if metrics.empty:
        loopbacks = pd.DataFrame(
            columns=[
                "from_activity",
                "to_activity",
                "loop_back_count",
                "loop_back_case_count",
                "pct_of_cases_affected",
            ]
        )
    else:
        loopbacks = metrics.loc[
            metrics["loop_back_count"] > 0,
            [
                "from_activity",
                "to_activity",
                "loop_back_count",
                "loop_back_case_count",
                "pct_of_cases_affected",
            ],
        ].copy()
    loopbacks = loopbacks.rename(
        columns={
            "loop_back_count": "loopback_count",
            "loop_back_case_count": "cases_affected",
            "pct_of_cases_affected": "percent_cases_affected",
        }
    )
    loopbacks = loopbacks.sort_values(
        ["loopback_count", "cases_affected", "from_activity", "to_activity"],
        ascending=[False, False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    return transitions, loopbacks.loc[:, list(LOOPBACK_COLUMNS)]


def export_bottleneck_csvs(
    input_path: Path, output_directory: Path
) -> tuple[Path, Path]:
    """Write clean transition and loop-back CSVs without an index column."""
    metrics = pd.read_csv(input_path)
    transitions, loopbacks = build_powerbi_exports(metrics)
    output_directory.mkdir(parents=True, exist_ok=True)

    transitions_path = output_directory / "bottleneck_transitions.csv"
    loopbacks_path = output_directory / "loopbacks.csv"
    transitions.to_csv(transitions_path, index=False)
    loopbacks.to_csv(loopbacks_path, index=False)
    return transitions_path, loopbacks_path


def build_conformance_exports(
    cases: pd.DataFrame,
    previous_summary: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the non-compliant cases and one-row conformance summary tables."""
    if "case_id" not in cases and "Case_ID" in cases:
        cases = cases.rename(columns={"Case_ID": "case_id"})
    missing_columns = [
        column for column in CONFORMANCE_CASE_COLUMNS if column not in cases
    ]
    if missing_columns:
        raise ValueError(
            "Conformance results are missing required columns: "
            + ", ".join(missing_columns)
        )

    clean_cases = cases.loc[:, list(CONFORMANCE_CASE_COLUMNS)].copy()
    compliant = clean_cases["is_compliant"].astype("string").str.lower().eq("true")
    non_compliant = clean_cases.loc[~compliant].reset_index(drop=True)
    deviations = clean_cases["deviation_type"].astype("string")
    deviation_counts = deviations.value_counts()
    total_cases = len(clean_cases)
    compliant_cases = int(compliant.sum())

    summary_values: dict[str, int | float | None] = {
        "total_cases": total_cases,
        "compliant_cases": compliant_cases,
        "non_compliant_cases": total_cases - compliant_cases,
        "pct_compliant": (
            100.0 * compliant_cases / total_cases if total_cases else 0.0
        ),
        "pct_non_compliant": (
            100.0 * (total_cases - compliant_cases) / total_cases
            if total_cases
            else 0.0
        ),
        **{
            f"{deviation_type}_count": int(deviation_counts.get(deviation_type, 0))
            for deviation_type in (
                "compliant",
                "skipped_step",
                "wrong_order",
                "repeated_step",
                "extra_step",
            )
        },
        "average_fitness": None,
    }

    if previous_summary is not None and not previous_summary.empty:
        if "average_fitness" in previous_summary:
            summary_values["average_fitness"] = previous_summary.loc[
                previous_summary.index[0], "average_fitness"
            ]
    summary = pd.DataFrame([summary_values], columns=CONFORMANCE_SUMMARY_COLUMNS)
    return non_compliant, summary


def export_conformance_csvs(
    input_path: Path,
    output_directory: Path,
    summary_input_path: Path | None = None,
) -> tuple[Path, Path]:
    """Write non-compliant cases and a summary CSV without index columns."""
    try:
        cases = pd.read_csv(input_path)
        previous_summary = (
            pd.read_csv(summary_input_path)
            if summary_input_path is not None and summary_input_path.is_file()
            else None
        )
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read conformance CSV: {error}") from error

    non_compliant, summary = build_conformance_exports(cases, previous_summary)
    output_directory.mkdir(parents=True, exist_ok=True)
    non_compliant_path = output_directory / "non_compliant_cases.csv"
    summary_path = output_directory / "conformance_summary.csv"
    non_compliant.to_csv(non_compliant_path, index=False)
    summary.to_csv(summary_path, index=False)
    return non_compliant_path, summary_path


def main() -> None:
    """Export bottleneck and available conformance tables for Power BI."""
    output_directory = Path(__file__).resolve().parent / "output"
    parser = argparse.ArgumentParser(
        description="Export bottleneck metrics for Power BI."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=output_directory / "bottlenecks.csv",
        help="Calculated bottleneck metrics CSV.",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=output_directory,
        help="Folder for the Power BI CSV files.",
    )
    parser.add_argument(
        "--conformance-input",
        type=Path,
        default=output_directory / "conformance_results.csv",
        help="Per-case conformance results CSV from conformance_check.py.",
    )
    parser.add_argument(
        "--conformance-summary",
        type=Path,
        default=output_directory / "conformance_summary.csv",
        help="Optional summary CSV containing the average fitness value.",
    )
    args = parser.parse_args()
    has_conformance_input = args.conformance_input.is_file()
    if not args.input.is_file() and not has_conformance_input:
        parser.error(
            "neither bottleneck metrics nor conformance results exist: "
            f"{args.input}; {args.conformance_input}"
        )

    if args.input.is_file():
        try:
            transitions_path, loopbacks_path = export_bottleneck_csvs(
                args.input, args.output_directory
            )
        except ValueError as error:
            parser.error(str(error))

        transitions = pd.read_csv(transitions_path)
        loopbacks = pd.read_csv(loopbacks_path)
        print(
            f"Wrote {len(transitions)} transitions to {transitions_path} "
            f"with columns: {', '.join(transitions.columns)}"
        )
        print(
            f"Wrote {len(loopbacks)} loop-backs to {loopbacks_path} "
            f"with columns: {', '.join(loopbacks.columns)}"
        )
    else:
        print(
            "Bottleneck exports were skipped because no metrics were found at "
            f"{args.input}."
        )

    if has_conformance_input:
        try:
            non_compliant_path, summary_path = export_conformance_csvs(
                args.conformance_input,
                args.output_directory,
                args.conformance_summary,
            )
        except ValueError as error:
            parser.error(str(error))
        non_compliant = pd.read_csv(non_compliant_path)
        print(
            f"Wrote {len(non_compliant)} non-compliant cases to "
            f"{non_compliant_path}"
        )
        print(f"Wrote conformance summary to {summary_path}")
    else:
        print(
            "Conformance exports were skipped because no per-case results were "
            f"found at {args.conformance_input}. Run conformance_check.py first."
        )


if __name__ == "__main__":
    main()
