# Interactive process-mining dashboard

## Install and run

From the repository root in Windows PowerShell, install the project
dependencies and start Streamlit:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run process_mining/dashboard_app.py
```

The app opens with `process_mining/sample_event_log.csv`. Enter another CSV
path in the sidebar to use a different event log. Input files must contain
`case_id`, `activity`, and `timestamp` columns; `Case_ID`, `Activity_Name`, and
`Timestamp` aliases are also accepted. Doctor and common demographic columns
are detected and get their own filters when present.

## Dashboard tabs

- **Overview:** total cases and events, average case duration, loop-back share,
  and compliant/non-compliant case shares.
- **Process map:** frequency directly-follows graph and an Inductive Miner
  Petri net. The checked-in `output/dfg.png` and `output/petri_net.png` are
  used for the unfiltered sample; other selections are rendered temporarily.
- **Bottlenecks:** the ten transitions with the highest average waiting time,
  shown as a bar chart and a detail table.
- **Variants:** each `path_variant`, its `case_count`, and `pct_of_cases`.
- **Conformance:** non-compliant cases with their `deviation_type`, plus a
  chart showing the count of each deviation.
- **Case drill-down:** select a `Case_ID` to inspect its timestamped activity
  timeline.

Activity, case, and detected doctor/demographic filters are available in the
sidebar and apply across the dashboard.

## Power BI CSV mapping

The existing exporter files under `process_mining/output/` feed the following
common visuals. Run the existing generators first if a CSV is missing.

| CSV | Suggested Power BI visual |
| --- | --- |
| `output/powerbi/kpi_summary.csv` | Cards for cases, events, duration, and loop-back rate |
| `output/powerbi/process_map_edges.csv` | Process-flow edges; use `avg_wait_minutes` in tooltips |
| `output/powerbi/process_map_nodes.csv` | Process-map nodes sized by event or case count |
| `output/powerbi/case_summary.csv` | Case table, durations, and loop-back segmentation |
| `output/powerbi/variant_summary.csv` | Path variants table or bar chart by `case_count` / `pct_of_cases` |
| `output/powerbi/hourly_arrivals.csv` | Hourly-arrivals chart |
| `output/bottleneck_transitions.csv` | Bottleneck bar chart using `avg_wait_minutes` |
| `output/loopbacks.csv` | Loop-back transition table or bar chart |
| `output/non_compliant_cases.csv` | Non-compliant cases table, segmented by `deviation_type` |
| `output/conformance_summary.csv` | Compliance and deviation KPI cards |

Build the six Power BI dashboard tables with:

```powershell
python process_mining/build_dashboard_tables.py
```

Export the bottleneck and conformance tables with:

```powershell
python process_mining/export_for_powerbi.py
```

The Streamlit app calculates its current views from the selected event log by
calling the existing process-mining helpers; it does not require the Power BI
CSV exports to be present.
