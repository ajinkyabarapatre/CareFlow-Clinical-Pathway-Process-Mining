"""Export bottleneck and conformance results as Power BI-ready CSV files."""

import re
from pathlib import Path

import pandas as pd


INPUT_FILES = ("bottlenecks.csv", "conformance_results.csv")


def snake_case(column: str) -> str:
    """Convert a column header to lowercase snake_case."""
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", column.strip())
    return re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()


def prepare_export(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize headers, timestamp fields, and boolean values."""
    result = data.copy()
    result.columns = [snake_case(column) for column in result.columns]
    if len(set(result.columns)) != len(result.columns):
        raise ValueError("Input has duplicate columns after snake_case normalization")

    for column in result.columns:
        if column in {"timestamp", "datetime", "date"} or column.endswith(
            ("_timestamp", "_datetime", "_date", "_at")
        ):
            parsed = pd.to_datetime(result[column], utc=True, errors="coerce")
            invalid = (
                result[column].notna()
                & result[column].astype(str).str.strip().ne("")
                & parsed.isna()
            )
            if invalid.any():
                raise ValueError(f"Invalid timestamp in column '{column}'")
            result[column] = parsed.dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ").fillna("")
        elif (
            result[column].dropna().astype(str).str.lower().isin(
                {"true", "false"}
            ).all()
            and result[column].notna().any()
        ):
            result[column] = result[column].astype("string").str.lower()
    return result


def main() -> None:
    """Export both analysis tables to process_mining/output/powerbi/."""
    output = Path(__file__).resolve().parent / "output"
    inputs = [output / name for name in INPUT_FILES]
    missing = [path.name for path in inputs if not path.is_file()]
    if missing:
        raise SystemExit(
            f"Cannot export to Power BI; missing input file(s): {', '.join(missing)}"
        )
    destination = output / "powerbi"
    destination.mkdir(parents=True, exist_ok=True)
    for source in inputs:
        data = prepare_export(pd.read_csv(source))
        target = destination / source.name
        data.to_csv(target, index=False)
        print(f"{target}: {len(data)} rows; columns: {', '.join(data.columns)}")


if __name__ == "__main__":
    main()
