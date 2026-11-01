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


def main() -> None:
    """Export the bottleneck-analysis results from the default output folder."""
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
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"bottleneck metrics file does not exist: {args.input}")

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


if __name__ == "__main__":
    main()
