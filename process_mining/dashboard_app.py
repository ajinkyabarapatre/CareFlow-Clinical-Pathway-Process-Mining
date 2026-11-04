"""Interactive Streamlit dashboard for clinical pathway process-mining results."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd
import plotly.express as px
import pm4py
import streamlit as st

if __package__:
    from .bottleneck_analysis import calculate_metrics, load_event_log
    from .build_dashboard_tables import build_dashboard_tables
    from .conformance_check import analyze_conformance
    from .process_discovery import save_dfg_image, save_petri_net_image
else:
    from bottleneck_analysis import calculate_metrics, load_event_log
    from build_dashboard_tables import build_dashboard_tables
    from conformance_check import analyze_conformance
    from process_discovery import save_dfg_image, save_petri_net_image


PROCESS_MINING_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_EVENT_LOG = PROCESS_MINING_DIRECTORY / "sample_event_log.csv"
OUTPUT_DIRECTORY = PROCESS_MINING_DIRECTORY / "output"
DEMOGRAPHIC_COLUMN_HINTS = (
    "age",
    "gender",
    "sex",
    "race",
    "ethnicity",
    "demographic",
    "marital",
    "insurance",
    "payer",
    "language",
    "postal",
    "zip",
    "nationality",
    "religion",
    "education",
    "employment",
)


def load_dashboard_event_log(input_path: Path | str) -> pd.DataFrame:
    """Load and validate an event log using the existing bottleneck loader."""
    dataframe, _ = load_event_log(input_path)
    return dataframe


def build_dashboard_view_data(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Reuse the project analyzers to build tables for the interactive views."""
    tables = build_dashboard_tables(dataframe)
    bottleneck_metrics = calculate_metrics(dataframe)
    conformance_records, conformance_summary = analyze_conformance(dataframe)
    conformance_results = pd.DataFrame(conformance_records)
    return {
        "tables": tables,
        "bottleneck_metrics": bottleneck_metrics,
        "conformance_results": conformance_results,
        "conformance_summary": conformance_summary,
    }


def calculate_dashboard_kpis(dataframe: pd.DataFrame) -> dict[str, int | float]:
    """Return case, event, duration, loop-back, and compliance dashboard KPIs."""
    return _kpis_from_view_data(build_dashboard_view_data(dataframe))


def _kpis_from_view_data(view_data: dict[str, Any]) -> dict[str, int | float]:
    """Extract headline KPIs from tables already built for the dashboard."""
    table_kpis = view_data["tables"]["kpi_summary"].iloc[0]
    conformance = view_data["conformance_summary"]
    return {
        "total_cases": int(table_kpis["total_cases"]),
        "total_events": int(table_kpis["total_events"]),
        "avg_case_duration_minutes": float(
            table_kpis["avg_case_duration_minutes"]
        ),
        "pct_cases_with_loopback": float(
            table_kpis["pct_cases_with_loopback"]
        ),
        "pct_compliant": float(conformance["pct_compliant"]),
        "pct_non_compliant": float(conformance["pct_non_compliant"]),
    }


def _column_filter_options(dataframe: pd.DataFrame, column: str) -> list[str]:
    """Return displayable filter choices, including a choice for missing values."""
    values = dataframe[column].dropna().astype(str).unique().tolist()
    options = sorted(values)
    if dataframe[column].isna().any():
        options.append("(Missing)")
    return options


def _is_optional_filter_column(column: str) -> bool:
    """Identify doctor and commonly used demographic columns by their names."""
    normalized = column.casefold()
    return "doctor" in normalized or "physician" in normalized or any(
        hint in normalized for hint in DEMOGRAPHIC_COLUMN_HINTS
    )


def _filter_by_values(
    dataframe: pd.DataFrame, column: str, selected_values: list[str]
) -> pd.DataFrame:
    """Keep rows matching selected values, preserving a selectable missing value."""
    if not selected_values:
        return dataframe.iloc[0:0].copy()

    include_missing = "(Missing)" in selected_values
    selected = [value for value in selected_values if value != "(Missing)"]
    matches = dataframe[column].astype("string").isin(selected)
    if include_missing:
        matches |= dataframe[column].isna()
    return dataframe.loc[matches].copy()


def _apply_sidebar_filters(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Render common and available metadata filters and return matching events."""
    st.sidebar.header("Filters")
    filtered = dataframe

    for column, label in (("activity", "Activity"), ("case_id", "Case_ID")):
        options = _column_filter_options(dataframe, column)
        selected = st.sidebar.multiselect(
            f"Filter by {label}",
            options,
            default=options,
            key=f"filter_{column}",
        )
        filtered = _filter_by_values(filtered, column, selected)

    optional_columns = [
        column
        for column in dataframe.columns
        if column not in {"case_id", "activity", "timestamp", "_source_order"}
        and _is_optional_filter_column(column)
    ]
    for column in optional_columns:
        options = _column_filter_options(dataframe, column)
        selected = st.sidebar.multiselect(
            f"Filter by {column.replace('_', ' ').title()}",
            options,
            default=options,
            key=f"filter_{column}",
        )
        filtered = _filter_by_values(filtered, column, selected)
    return filtered


def _make_event_log(dataframe: pd.DataFrame) -> Any:
    """Convert the currently filtered events into a PM4Py event log."""
    formatted = pm4py.format_dataframe(
        dataframe.copy(),
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )
    return pm4py.convert_to_event_log(formatted)


def _render_process_maps(dataframe: pd.DataFrame, use_saved_images: bool) -> None:
    """Show the DFG and Petri net, generating temporary images when needed."""
    dfg_tab, petri_tab = st.tabs(["DFG", "Petri net"])
    saved_dfg = OUTPUT_DIRECTORY / "dfg.png"
    saved_petri = OUTPUT_DIRECTORY / "petri_net.png"
    dfg_available = use_saved_images and saved_dfg.is_file()
    petri_available = use_saved_images and saved_petri.is_file()

    with TemporaryDirectory(prefix="careflow_dashboard_") as temporary_directory:
        temporary_path = Path(temporary_directory)
        dfg_path = saved_dfg if dfg_available else temporary_path / "dfg.png"
        petri_path = (
            saved_petri if petri_available else temporary_path / "petri_net.png"
        )

        if not dfg_available or not petri_available:
            event_log = _make_event_log(dataframe)
            if not dfg_available:
                dfg, start_activities, end_activities = pm4py.discover_dfg(event_log)
                save_dfg_image(
                    dfg,
                    start_activities,
                    end_activities,
                    dfg_path,
                    "Frequency Directly-Follows Graph",
                )
            if not petri_available:
                net, initial_marking, final_marking = (
                    pm4py.discover_petri_net_inductive(event_log)
                )
                save_petri_net_image(
                    net, initial_marking, final_marking, petri_path
                )

        with dfg_tab:
            if dfg_path.is_file():
                st.image(str(dfg_path), width="stretch")
            else:
                st.info("The DFG image is not available for this event log.")
        with petri_tab:
            if petri_path.is_file():
                st.image(str(petri_path), width="stretch")
            else:
                st.info("The Petri-net image is not available for this event log.")


def _render_kpis(kpis: dict[str, int | float]) -> None:
    """Display the requested headline process and conformance metrics."""
    first_row = st.columns(3)
    first_row[0].metric("Total cases", f"{kpis['total_cases']:,}")
    first_row[1].metric("Total events", f"{kpis['total_events']:,}")
    first_row[2].metric(
        "Average case duration", f"{kpis['avg_case_duration_minutes']:.1f} min"
    )

    second_row = st.columns(3)
    second_row[0].metric(
        "Cases with loop-back", f"{kpis['pct_cases_with_loopback']:.1f}%"
    )
    second_row[1].metric("Compliant cases", f"{kpis['pct_compliant']:.1f}%")
    second_row[2].metric(
        "Non-compliant cases", f"{kpis['pct_non_compliant']:.1f}%"
    )


def _render_dashboard(dataframe: pd.DataFrame, source_is_default: bool) -> None:
    """Render dashboard tabs from the selected, filtered event log."""
    if dataframe.empty:
        st.info("No events match the selected filters.")
        return

    view_data = build_dashboard_view_data(dataframe)
    tables: dict[str, pd.DataFrame] = view_data["tables"]
    bottlenecks: pd.DataFrame = view_data["bottleneck_metrics"]
    conformance: pd.DataFrame = view_data["conformance_results"]

    _render_kpis(_kpis_from_view_data(view_data))
    overview_tab, process_tab, bottleneck_tab, variants_tab, conformance_tab, case_tab = (
        st.tabs(
            [
                "Overview",
                "Process map",
                "Bottlenecks",
                "Variants",
                "Conformance",
                "Case drill-down",
            ]
        )
    )

    with overview_tab:
        st.subheader("Process discovery summary")
        st.dataframe(tables["kpi_summary"], hide_index=True, width="stretch")
        st.caption(
            "The case and transition metrics use the existing process-mining "
            "analysis helpers."
        )

    with process_tab:
        _render_process_maps(
            dataframe,
            use_saved_images=source_is_default and len(dataframe) == 20,
        )

    with bottleneck_tab:
        st.subheader("10 slowest transitions by average wait")
        top_bottlenecks = bottlenecks.head(10).copy()
        if top_bottlenecks.empty:
            st.info("No transitions are available for the selected events.")
        else:
            top_bottlenecks["transition"] = (
                top_bottlenecks["from_activity"]
                + " → "
                + top_bottlenecks["to_activity"]
            )
            chart = px.bar(
                top_bottlenecks.sort_values("avg_wait_minutes"),
                x="avg_wait_minutes",
                y="transition",
                orientation="h",
                labels={
                    "avg_wait_minutes": "Average wait (minutes)",
                    "transition": "Transition",
                },
            )
            st.plotly_chart(chart, width="stretch")
            st.dataframe(
                top_bottlenecks.drop(columns="transition"),
                hide_index=True,
                width="stretch",
            )

    with variants_tab:
        st.subheader("Path variants")
        st.dataframe(
            tables["variant_summary"][
                ["path_variant", "case_count", "pct_of_cases"]
            ],
            hide_index=True,
            width="stretch",
        )

    with conformance_tab:
        st.subheader("Non-compliant cases")
        non_compliant = conformance.loc[
            ~conformance["is_compliant"].astype(bool),
            ["Case_ID", "deviation_type", "actual_path", "missing_steps", "extra_steps"],
        ]
        if non_compliant.empty:
            st.success("All selected cases follow the ideal pathway.")
        else:
            st.dataframe(non_compliant, hide_index=True, width="stretch")
            deviation_counts = (
                non_compliant["deviation_type"]
                .value_counts()
                .rename_axis("deviation_type")
                .reset_index(name="case_count")
            )
            chart = px.bar(
                deviation_counts,
                x="deviation_type",
                y="case_count",
                labels={
                    "deviation_type": "Deviation type",
                    "case_count": "Cases",
                },
            )
            st.plotly_chart(chart, width="stretch")

    with case_tab:
        st.subheader("Case timeline")
        case_ids = sorted(dataframe["case_id"].astype(str).unique().tolist())
        selected_case = st.selectbox("Select a Case_ID", case_ids)
        timeline = dataframe.loc[
            dataframe["case_id"].astype(str).eq(selected_case),
            ["timestamp", "activity"],
        ].sort_values("timestamp", kind="stable")
        timeline = timeline.rename(
            columns={"timestamp": "Timestamp", "activity": "Activity"}
        )
        st.dataframe(timeline, hide_index=True, width="stretch")


def main() -> None:
    """Run the Streamlit dashboard application."""
    st.set_page_config(page_title="CareFlow Process Mining", layout="wide")
    st.title("CareFlow Clinical Pathway Process Mining")
    st.sidebar.header("Event log")
    input_text = st.sidebar.text_input(
        "Event log CSV path",
        value=str(DEFAULT_EVENT_LOG),
        help="Enter a CSV path. Relative paths are resolved from the repository root.",
    )
    input_path = Path(input_text).expanduser()
    if not input_path.is_absolute():
        input_path = PROCESS_MINING_DIRECTORY.parent / input_path

    if not input_path.is_file():
        st.error(f"Event-log CSV not found: {input_path}")
        st.info(
            "Check the path above. The default sample file is "
            f"`{DEFAULT_EVENT_LOG.name}`."
        )
        return

    try:
        event_dataframe = load_dashboard_event_log(input_path)
    except (OSError, ValueError, pd.errors.ParserError, UnicodeDecodeError) as error:
        st.error(f"Could not load the event log: {error}")
        return

    filtered_dataframe = _apply_sidebar_filters(event_dataframe)
    source_is_default = input_path.resolve() == DEFAULT_EVENT_LOG.resolve()
    try:
        _render_dashboard(filtered_dataframe, source_is_default)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        st.error(f"Could not build the dashboard for this event log: {error}")


if __name__ == "__main__":
    main()
