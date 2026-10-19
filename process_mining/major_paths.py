"""Summarize and visualize the most frequent patient pathway variants."""

from collections import Counter
from pathlib import Path

import pandas as pd
import pm4py

from process_discovery import read_event_log, save_dfg_image


TOP_VARIANTS = 5
VARIANT_COLUMNS = ("rank", "variant", "case_count", "percentage")


def main() -> None:
    """Write the five most frequent variants and their filtered DFG."""
    directory = Path(__file__).resolve().parent
    output_directory = directory / "output"
    output_directory.mkdir(parents=True, exist_ok=True)
    dataframe, _ = read_event_log(directory / "sample_event_log.csv")

    case_variants = {
        str(case_id): tuple(group["activity"].astype(str))
        for case_id, group in dataframe.groupby("case_id", sort=False)
    }
    variant_counts = Counter(case_variants.values())
    total_cases = len(case_variants)
    ranked_variants = sorted(
        variant_counts.items(), key=lambda item: (-item[1], item[0])
    )[:TOP_VARIANTS]
    results = [
        {
            "rank": rank,
            "variant": " -> ".join(variant),
            "case_count": count,
            "percentage": round(count / total_cases * 100, 2),
        }
        for rank, (variant, count) in enumerate(ranked_variants, start=1)
    ]

    variants_path = output_directory / "top_variants.csv"
    pd.DataFrame(results, columns=VARIANT_COLUMNS).to_csv(
        variants_path, index=False
    )

    major_variant_set = {variant for variant, _ in ranked_variants}
    major_case_ids = [
        case_id
        for case_id, variant in case_variants.items()
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

    print(f"Major patient paths across {total_cases} cases:")
    for result in results:
        case_label = "case" if result["case_count"] == 1 else "cases"
        print(
            f"- Path {result['rank']}: {result['variant']} was observed in "
            f"{result['case_count']} {case_label} "
            f"({result['percentage']:.2f}%)."
        )
    print(f"Top variants saved to: {variants_path}")
    print(f"Major-path DFG saved to: {graph_path}")


if __name__ == "__main__":
    main()
