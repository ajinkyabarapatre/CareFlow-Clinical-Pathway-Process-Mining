"""Load generated dashboard CSV files into BigQuery tables."""

import argparse
import logging
import os
from pathlib import Path


LOGGER = logging.getLogger(__name__)


def get_csv_files(input_directory: Path) -> list[Path]:
    """Return CSV files in a folder in stable name order."""
    if not input_directory.is_dir():
        raise FileNotFoundError(
            f"Dashboard output folder does not exist: {input_directory}"
        )
    return sorted(input_directory.glob("*.csv"), key=lambda path: path.name)


def load_csv_files(
    csv_files: list[Path],
    project_id: str,
    dataset_id: str,
    *,
    dry_run: bool = False,
) -> None:
    """Print or load each CSV into a corresponding ``pm_`` BigQuery table."""
    if dry_run:
        for csv_file in csv_files:
            table_id = f"{project_id}.{dataset_id}.pm_{csv_file.stem}"
            print(f"Would load {csv_file} -> {table_id} (WRITE_TRUNCATE)")
        return

    try:
        from google.api_core.exceptions import GoogleAPIError
        from google.auth.exceptions import GoogleAuthError
        from google.cloud import bigquery
    except ImportError as error:
        raise RuntimeError(
            "BigQuery loading requires google-cloud-bigquery; "
            "install the packages in requirements.txt."
        ) from error

    try:
        client = bigquery.Client(project=project_id)
        for csv_file in csv_files:
            table_id = f"{project_id}.{dataset_id}.pm_{csv_file.stem}"
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.CSV,
                skip_leading_rows=1,
                autodetect=True,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            )
            LOGGER.info("Loading %s into %s", csv_file, table_id)
            with csv_file.open("rb") as source:
                job = client.load_table_from_file(
                    source, table_id, job_config=job_config
                )
            job.result()
            LOGGER.info("Loaded %s rows into %s", job.output_rows, table_id)
    except (GoogleAPIError, GoogleAuthError, OSError) as error:
        raise RuntimeError(f"Could not load dashboard CSVs into BigQuery: {error}") from error


def main() -> None:
    """Load every dashboard CSV, or list the planned loads with --dry-run."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    script_directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Load process-mining dashboard CSVs into BigQuery."
    )
    parser.add_argument(
        "--input-directory",
        type=Path,
        default=script_directory / "output" / "powerbi",
        help="Folder containing dashboard CSV files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned table loads without requiring BigQuery credentials.",
    )
    args = parser.parse_args()

    try:
        csv_files = get_csv_files(args.input_directory)
        if not csv_files:
            raise FileNotFoundError(
                f"No CSV files found in dashboard output folder: {args.input_directory}"
            )

        # A dry run deliberately does not require configuration or credentials.
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        dataset_id = os.getenv("BIGQUERY_DATASET", "").strip()
        if args.dry_run:
            load_csv_files(
                csv_files,
                project_id or "<project>",
                dataset_id or "<dataset>",
                dry_run=True,
            )
            return
        if not project_id or not dataset_id:
            raise ValueError(
                "Set GOOGLE_CLOUD_PROJECT and BIGQUERY_DATASET before loading."
            )
        load_csv_files(csv_files, project_id, dataset_id)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        LOGGER.error("%s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
