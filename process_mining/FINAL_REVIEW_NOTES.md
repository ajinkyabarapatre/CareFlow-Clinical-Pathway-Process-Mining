# Week 4 Final Review Notes

## Project

The project examines timestamped clinical activity events to understand observed care pathways, waiting times, and deviations from an expected sequence.
The local solution uses PM4Py and Python scripts to discover process maps, rank pathway variants and bottlenecks, check conformance, and export dashboard data.
As Member 3, I implemented the process-mining work in `process_mining/` and the related BigQuery SQL work in `sql/04-06`.

## Pipeline

```text
Simulator -> BigQuery -> dbt -> PM4Py (Member 3) -> Power BI
```

The diagram shows the intended project flow; the local runner executes the PM4Py analysis and export scripts on the bundled sample.
BigQuery and Power BI connections require project-specific configuration and were not part of the local pipeline run.

## Member 3 Deliverables

| Script | What it does | Output file(s) | Status |
|---|---|---|---|
| `run_pipeline.py` | Runs the local analysis steps and records each step's status. | `output/pipeline_summary.csv`, `output/pipeline_run.log` | done |
| `process_discovery.py` | Summarizes the event log and discovers a directly-follows graph and Petri net. | `output/discovery_summary.csv`, `output/dfg.png`, `output/petri_net.png` | done |
| `major_paths.py` | Ranks observed activity sequences. | `output/top_variants.csv`, `output/major_paths.png` | done |
| `bottleneck_analysis.py` | Calculates elapsed time between consecutive activities. | `output/bottlenecks.csv`, `output/performance_dfg.png`, `output/top_10_slowest_transitions.png` | done |
| `conformance_check.py` | Compares each observed case with the configured ideal path. | `output/conformance_results.csv`, `output/conformance_summary.csv` | done |
| `generate_charts.py` | Builds KPI and variant tables plus charts. | `output/charts/kpi_summary.csv`, `output/charts/variant_table.csv`, chart PNG files | done |
| `export_for_powerbi.py` | Exports transition, loop-back, and conformance tables. | `output/bottleneck_transitions.csv`, `output/loopbacks.csv`, `output/non_compliant_cases.csv`, `output/conformance_summary.csv` | done |
| `bottlenecks.py` | Alternate grouped transition analysis. | `output/ranked_bottlenecks.csv`, `output/ranked_bottlenecks.png` | in progress |
| `conformance_report.py` | Produces a separate per-case pathway comparison. | `output/conformance_report_cases.csv`, `output/conformance_report_summary.csv` | in progress |
| `build_dashboard_tables.py` | Builds CSV tables for dashboard reporting. | CSV files in `output/powerbi/` | in progress |
| `dashboard_app.py` | Serves an interactive Streamlit dashboard. | Interactive dashboard; no local output file | in progress |
| `load_outputs_to_bigquery.py` | Loads dashboard CSVs into configured BigQuery tables. | BigQuery tables; no local output file | in progress |
| `transition_report.py` | Writes transition, loop-back, and case-duration summaries. | `output/transition_summary.csv`, `output/loopback_summary.csv`, `output/case_durations.csv` | in progress |

`done` means the script's step passed in the full local pipeline run.
`in progress` means the standalone script or external-service integration was not verified in that run.

## Key Results

The figures below come from the generated files in `process_mining/output/` and describe only the bundled demonstration log.

- Cases: **4** (`discovery_summary.csv`)
- Events: **20** (`discovery_summary.csv`)
- Activities: **5** (`discovery_summary.csv`)
- Variants: **4** (`discovery_summary.csv`)
- Average case duration: **2.0 hours** (`discovery_summary.csv`)
- Longest average wait: a tie at **45 minutes** for `Treatment -> Discharge` and `Admission -> Diagnosis` (`bottlenecks.csv`)
- Cases with a loop-back: **25%**; the reported loop-back is `Triage -> Triage` (`charts/kpi_summary.csv`, `loopbacks.csv`)
- Compliant cases: **25%** (`conformance_summary.csv`)
- Non-compliant cases: **75%** (`conformance_summary.csv`)
- Each of the four observed variants occurs once (**25%** each) (`top_variants.csv`)

## Verification

The initial verification was completed before any documentation changes.

- `python -m pytest`: **43 passed**.
- `python process_mining\run_pipeline.py`: exited successfully.
- Pipeline steps passed: discovery, major paths, bottlenecks, conformance, charts, and Power BI export.
- No working Python code or tests needed changes because both requested checks passed.

## Demo Steps

1. Open `sample_event_log.csv` and point out its case, activity, and timestamp fields.
2. Run `python process_mining\run_pipeline.py` from the repository root.
3. Open `output/dfg.png` and `output/petri_net.png`.
4. Show the top rows of `output/bottlenecks.csv`, explaining the 45-minute tie.
5. Show `output/conformance_summary.csv` and the compliant/non-compliant split.
6. Run `python -m pytest` and show the passing test summary.
7. Open the GitHub branch and show the project files and final review notes.

## Likely Viva Questions

1. **What is process mining?** It uses timestamped event logs to discover and analyze real process flows.
2. **What fields does this event log need?** Each event needs a `case_id`, `activity`, and `timestamp`.
3. **What does the directly-follows graph show?** It shows which activities occur consecutively and how often.
4. **What does the Petri net add?** It represents possible process behavior as a formal process model.
5. **What is a variant?** A variant is one distinct ordered sequence of activities for a case.
6. **How is a bottleneck measured here?** By elapsed time between consecutive events, ranked by average wait.
7. **What is a loop-back?** A repeated activity in a case, such as the reported `Triage -> Triage` transition.
8. **How is conformance decided?** Each observed path is checked against the configured ideal sequence.
9. **Why are some cases non-compliant?** The sample includes a skipped step, a repeated step, and an ordering deviation.
10. **Can these results guide clinical policy?** No; the sample is small demonstration data and needs validation on representative data.

## Limitations

- The event log is simulated demonstration data, not a validated operational hospital extract.
- The sample is small; individual cases can substantially affect its percentages and averages.
- Conformance uses one fixed ideal path and may treat legitimate clinical variations as deviations.
- The local pipeline does not itself provision or connect a BigQuery project, dbt environment, or Power BI report.
- `generate_charts.py` uses the bundled sample log rather than a custom input passed to the pipeline.

## Future Work

- Validate event definitions, timestamps, case identifiers, and the ideal pathway with clinical and data owners.
- Run the analysis on a larger, approved, representative event-log extract.
- Test the unverified standalone reports, dashboard, and BigQuery integration with suitable project configuration.
- Review the tied longest waits and observed deviations with care teams before suggesting workflow changes.
- Add monitoring and rerun comparisons as new validated event data becomes available.
