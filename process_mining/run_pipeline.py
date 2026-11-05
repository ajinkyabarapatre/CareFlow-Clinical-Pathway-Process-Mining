"""Run the process-mining scripts in order and summarize their results."""

import argparse
import csv
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
PROJECT_DIRECTORY = SCRIPT_DIRECTORY.parent
OUTPUT_DIRECTORY = SCRIPT_DIRECTORY / "output"
DEFAULT_INPUT = SCRIPT_DIRECTORY / "sample_event_log.csv"
LOGGER = logging.getLogger("process_mining.pipeline")
SUMMARY_COLUMNS = ("step", "status", "seconds", "output_files_found")


@dataclass(frozen=True)
class PipelineStep:
    """Describe one existing script and the files it is expected to create."""

    name: str
    script_path: Path
    expected_output_files: tuple[Path, ...]
    accepts_input: bool = True


@dataclass(frozen=True)
class StepResult:
    """Store the status and outputs recorded for one pipeline step."""

    step: str
    status: str
    seconds: float
    output_files_found: str


PIPELINE_STEPS = [
    PipelineStep(
        "discovery",
        SCRIPT_DIRECTORY / "process_discovery.py",
        (
            OUTPUT_DIRECTORY / "discovery_summary.csv",
            OUTPUT_DIRECTORY / "dfg.png",
            OUTPUT_DIRECTORY / "petri_net.png",
        ),
    ),
    PipelineStep(
        "major_paths",
        SCRIPT_DIRECTORY / "major_paths.py",
        (
            OUTPUT_DIRECTORY / "top_variants.csv",
            OUTPUT_DIRECTORY / "major_paths.png",
        ),
    ),
    PipelineStep(
        "bottlenecks",
        SCRIPT_DIRECTORY / "bottleneck_analysis.py",
        (
            OUTPUT_DIRECTORY / "bottlenecks.csv",
            OUTPUT_DIRECTORY / "performance_dfg.png",
            OUTPUT_DIRECTORY / "top_10_slowest_transitions.png",
        ),
    ),
    PipelineStep(
        "conformance",
        SCRIPT_DIRECTORY / "conformance_check.py",
        (
            OUTPUT_DIRECTORY / "conformance_results.csv",
            OUTPUT_DIRECTORY / "conformance_summary.csv",
        ),
    ),
    PipelineStep(
        "charts",
        SCRIPT_DIRECTORY / "generate_charts.py",
        (
            OUTPUT_DIRECTORY / "charts" / "kpi_summary.csv",
            OUTPUT_DIRECTORY / "charts" / "variant_table.csv",
            OUTPUT_DIRECTORY / "charts" / "top_bottlenecks.png",
            OUTPUT_DIRECTORY / "charts" / "path_variants.png",
            OUTPUT_DIRECTORY / "charts" / "stay_time_per_case.png",
            OUTPUT_DIRECTORY / "charts" / "activity_counts.png",
        ),
        accepts_input=False,
    ),
    PipelineStep(
        "powerbi",
        SCRIPT_DIRECTORY / "export_for_powerbi.py",
        (
            OUTPUT_DIRECTORY / "bottleneck_transitions.csv",
            OUTPUT_DIRECTORY / "loopbacks.csv",
            OUTPUT_DIRECTORY / "non_compliant_cases.csv",
            OUTPUT_DIRECTORY / "conformance_summary.csv",
        ),
        accepts_input=False,
    ),
]


def configure_logging(output_directory: Path = OUTPUT_DIRECTORY) -> None:
    """Write pipeline messages to both the console and the run log."""
    output_directory.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    for handler in LOGGER.handlers[:]:
        LOGGER.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    LOGGER.addHandler(console_handler)

    file_handler = logging.FileHandler(
        output_directory / "pipeline_run.log", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)
    LOGGER.propagate = False


def _display_output_paths(paths: list[Path]) -> str:
    """Format found output paths as project-relative names when possible."""
    displayed_paths = []
    for path in paths:
        try:
            displayed_paths.append(str(path.resolve().relative_to(PROJECT_DIRECTORY)))
        except ValueError:
            displayed_paths.append(str(path))
    return "; ".join(displayed_paths)


def _check_outputs(step: PipelineStep) -> tuple[list[Path], list[Path]]:
    """Separate non-empty expected files from missing or empty files."""
    found = []
    missing = []
    for path in step.expected_output_files:
        if path.is_file() and path.stat().st_size > 0:
            found.append(path)
        else:
            missing.append(path)
    return found, missing


def _log_process_output(step_name: str, stdout: str, stderr: str) -> None:
    """Forward captured script output to the pipeline logger."""
    for line in stdout.splitlines():
        LOGGER.info("[%s] %s", step_name, line)
    for line in stderr.splitlines():
        LOGGER.warning("[%s stderr] %s", step_name, line)


def run_pipeline(
    input_path: Path,
    skip_steps: set[str] | None = None,
    stop_on_error: bool = False,
) -> list[StepResult]:
    """Run configured scripts and save a CSV summary of every step."""
    input_path = input_path.resolve()
    skip_steps = skip_steps or set()
    results: list[StepResult] = []
    stop_running = False

    for step in PIPELINE_STEPS:
        if not step.script_path.is_file():
            LOGGER.warning(
                "Skipping %s because its script does not exist: %s",
                step.name,
                step.script_path,
            )
            results.append(StepResult(step.name, "skipped", 0.0, ""))
            continue

        if step.name in skip_steps or stop_running:
            reason = (
                "requested with --skip"
                if step.name in skip_steps
                else "after an error"
            )
            LOGGER.info("Skipping %s (%s).", step.name, reason)
            results.append(StepResult(step.name, "skipped", 0.0, ""))
            continue

        command = [sys.executable, str(step.script_path)]
        if step.accepts_input:
            command.extend(["--input", str(input_path)])
        if (
            step.name == "charts"
            and input_path.resolve() != DEFAULT_INPUT.resolve()
        ):
            LOGGER.warning(
                "generate_charts.py does not accept --input; charts will use "
                "its bundled sample event log."
            )

        LOGGER.info("Starting %s: %s", step.name, command)
        start_time = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_DIRECTORY,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as error:
            elapsed = time.perf_counter() - start_time
            LOGGER.error("Could not run %s: %s", step.name, error)
            results.append(StepResult(step.name, "failed", elapsed, ""))
            stop_running = stop_on_error
            continue

        elapsed = time.perf_counter() - start_time
        _log_process_output(step.name, completed.stdout, completed.stderr)
        found, missing = _check_outputs(step)
        output_files_found = _display_output_paths(found)

        if completed.returncode != 0:
            LOGGER.error(
                "%s exited with return code %s.", step.name, completed.returncode
            )
            status = "failed"
        elif missing:
            LOGGER.error(
                "%s did not create non-empty expected output(s): %s",
                step.name,
                ", ".join(str(path) for path in missing),
            )
            status = "failed"
        else:
            LOGGER.info("%s passed in %.2f seconds.", step.name, elapsed)
            status = "passed"

        results.append(
            StepResult(step.name, status, elapsed, output_files_found)
        )
        if status == "failed" and stop_on_error:
            stop_running = True

    summary_path = OUTPUT_DIRECTORY / "pipeline_summary.csv"
    write_summary(results, summary_path)
    print_summary(results, summary_path)
    return results


def write_summary(results: list[StepResult], summary_path: Path) -> None:
    """Save step statuses, elapsed time, and discovered output paths."""
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "step": result.step,
                    "status": result.status,
                    "seconds": f"{result.seconds:.2f}",
                    "output_files_found": result.output_files_found,
                }
            )
    LOGGER.info("Pipeline summary saved to %s", summary_path)


def print_summary(results: list[StepResult], summary_path: Path) -> None:
    """Print a readable summary table and the saved CSV location."""
    print("step,status,seconds,output_files_found")
    for result in results:
        print(
            f"{result.step},{result.status},{result.seconds:.2f},"
            f"{result.output_files_found}"
        )
    print(f"Summary saved to: {summary_path}")


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line options, run the pipeline, and return its exit code."""
    parser = argparse.ArgumentParser(
        description="Run the process-mining workflow and summarize its outputs."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Event-log CSV (default: process_mining/sample_event_log.csv).",
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        choices=[step.name for step in PIPELINE_STEPS],
        default=[],
        help="Pipeline step names to skip.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Skip later steps after the first failed step.",
    )
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"event-log file does not exist: {args.input}")

    configure_logging()
    results = run_pipeline(args.input, set(args.skip), args.stop_on_error)
    return 1 if any(result.status == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
