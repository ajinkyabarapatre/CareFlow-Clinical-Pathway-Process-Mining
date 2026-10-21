"""Summarize and visualize the most frequent patient pathway variants."""

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd
import pm4py

if __package__:
    from .process_discovery import read_event_log, save_dfg_image
else:
    from process_discovery import read_event_log, save_dfg_image


TOP_VARIANTS = 5
TARGET_COVERAGE = 0.8
VARIANT_COLUMNS = ("rank", "variant", "case_count", "percentage")


def rank_variants(dataframe: pd.DataFrame) -> list[tuple[tuple[str, ...], int]]:
    """Count complete activity sequences and sort them by frequency."""
    case_variants = {
        str(case_id): tuple(group["activity"].astype(str))
        for case_id, group in dataframe.groupby("case_id", sort=False)
    }
    return sorted(
        Counter(case_variants.values()).items(),
        key=lambda item: (-item[1], item[0]),
    )


def select_major_variants(
    ranked_variants: list[tuple[tuple[str, ...], int]],
    total_cases: int,
    top: int,
    coverage: float,
) -> list[tuple[tuple[str, ...], int]]:
    """Select variants in rank order until coverage or the top-N limit is met."""
    if top < 1:
        raise ValueError("--top must be at least 1")
    if not 0 < coverage <= 1:
        raise ValueError("--coverage must be greater than 0 and at most 1")
    if total_cases < 1:
        raise ValueError("Cannot select variants from an empty event log")

    selected = []
    selected_cases = 0
    for variant in ranked_variants[:top]:
        selected.append(variant)
        selected_cases += variant[1]
        if selected_cases / total_cases >= coverage:
            break
    return selected


def build_variant_rows(
    variants: list[tuple[tuple[str, ...], int]], total_cases: int
) -> list[dict[str, int | str | float]]:
    """Format selected variants and their share of all cases for CSV export."""
    return [
        {
            "rank": rank,
            "variant": " -> ".join(variant),
            "case_count": count,
            "percentage": round(count / total_cases * 100, 2),
        }
        for rank, (variant, count) in enumerate(variants, start=1)
    ]


def main() -> None:
    """Write top variants and a DFG for variants meeting the coverage target."""
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Summarize frequent event-log variants and graph their DFG."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=directory / "sample_event_log.csv",
        help="CSV with case_id, activity, and timestamp columns.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=TOP_VARIANTS,
        help=f"Maximum number of variants to include (default: {TOP_VARIANTS}).",
    )
    parser.add_argument(
        "--coverage",
        type=float,
        default=TARGET_COVERAGE,
        help=(
            "Stop selecting when this cumulative share of cases is reached "
            f"(0-1; default: {TARGET_COVERAGE})."
        ),
    )
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"event-log file does not exist: {args.input}")
    try:
        dataframe, _ = read_event_log(args.input)
        ranked_variants = rank_variants(dataframe)
        total_cases = len(dataframe["case_id"].unique())
        major_variants = select_major_variants(
            ranked_variants, total_cases, args.top, args.coverage
        )
    except ValueError as error:
        parser.error(str(error))

    output_directory = directory / "output"
    output_directory.mkdir(parents=True, exist_ok=True)
    results = build_variant_rows(major_variants, total_cases)

    variants_path = output_directory / "top_variants.csv"
    pd.DataFrame(results, columns=VARIANT_COLUMNS).to_csv(
        variants_path, index=False
    )

    major_variant_set = {variant for variant, _ in major_variants}
    case_variants = {
        str(case_id): tuple(group["activity"].astype(str))
        for case_id, group in dataframe.groupby("case_id", sort=False)
    }
    major_case_ids = [
        case_id for case_id, variant in case_variants.items()
        if variant in major_variant_set
    ]
    major_dataframe = dataframe[
        dataframe["case_id"].astype(str).isin(major_case_ids)
    ]
    dfg, start_activities, end_activities = pm4py.discover_dfg(major_dataframe)
    graph_path = output_directory / "major_paths.png"
    save_dfg_image(
        dfg,
        start_activities,
        end_activities,
        graph_path,
        f"Major Patient Paths (Top {len(ranked_variants)} Variants)",
    )

    covered_cases = sum(count for _, count in major_variants)
    actual_coverage = covered_cases / total_cases
    print(
        f"Major patient paths: {covered_cases} of {total_cases} cases "
        f"({actual_coverage:.1%}) are represented by the selected variants."
    )
    for result in results:
        case_label = "case" if result["case_count"] == 1 else "cases"
        print(
            f"- Path {result['rank']}: {result['variant']} was observed in "
            f"{result['case_count']} {case_label} "
            f"({result['percentage']:.2f}%)."
        )
    if actual_coverage < args.coverage:
        print(
            f"The {args.top}-variant limit was reached before the requested "
            f"{args.coverage:.1%} coverage."
        )
    print(f"Top variants saved to: {variants_path}")
    print(f"Major-path DFG saved to: {graph_path}")


if __name__ == "__main__":
    main()
