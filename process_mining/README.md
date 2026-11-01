# Week 3: Bottleneck calculations and Power BI export

`bottleneck_analysis.py` is the primary Week 3 calculator. It sorts events
within each case by timestamp and activity, then calculates one row for every
observed directly-follows activity pair. Equal timestamps are ordered by
activity name, with input order as a final tie-breaker.

The input CSV must contain `case_id`, `activity`, and `timestamp` columns. The
BigQuery loader also accepts `Case_ID`, `Activity_Name`, and `Timestamp`.
Required values must be populated, timestamps must be valid, and consecutive
events must not have negative durations.

## Run the Week 3 workflow

From the repository root in Windows PowerShell, run the analysis and then
export its results for Power BI:

```powershell
python .\process_mining\bottleneck_analysis.py
python .\process_mining\export_for_powerbi.py
```

To analyze a different CSV:

```powershell
python .\process_mining\bottleneck_analysis.py `
  --input .\path\to\event_log.csv
python .\process_mining\export_for_powerbi.py
```

To use a BigQuery table instead of the bundled sample, set the table name
without putting credentials in the repository:

```powershell
$env:CAREFLOW_BIGQUERY_TABLE = 'project.dataset.event_log'
python .\process_mining\bottleneck_analysis.py
python .\process_mining\export_for_powerbi.py
```

The BigQuery query uses the configured Google Cloud authentication and the
table columns `Case_ID`, `Activity_Name`, and `Timestamp`.

The analysis validates that transition counts equal events minus cases, rejects
negative event gaps, and checks its mean waits against PM4Py's performance
directly-follows graph before writing the results. It ranks the ten slowest
transitions by average wait.

## Outputs

All files are written to `process_mining/output/`:

| File | Contents |
| --- | --- |
| `bottlenecks.csv` | Full calculated metrics, including wait percentiles, ranks, and loop-back counts. |
| `bottleneck_transitions.csv` | Power BI transition table with activity names, transition count, wait metrics in minutes, and rank. |
| `loopbacks.csv` | Only loop-back transitions, with count and percentage of cases affected. A repeated activity such as `Triage -> Triage` is included. |
| `performance_dfg.png` | PM4Py performance directly-follows graph, labeled with mean waiting time. |
| `top_10_slowest_transitions.png` | Chart of the highest-average-wait transitions. |

The Power BI CSVs have headers and no index column. Run the exporter after
changing the input log to refresh both CSVs.

## BigQuery SQL

Run [`../sql/05_bottleneck_transitions.sql`](../sql/05_bottleneck_transitions.sql)
in BigQuery. It contains a transition-time query using `LEAD()` partitioned by
`Case_ID`, followed by a loop-back query. Replace
`project.dataset.event_log` with the deployed table path. Equal timestamps are
ordered by activity name, matching the Python analysis.

## Findings from the checked-in sample

The sample contains 20 events across 4 cases, so it has 16 directly-follows
transitions. Its highest-average-wait transitions are:

1. `Treatment -> Discharge`: 4 transitions, 45 minutes average.
2. `Admission -> Diagnosis`: 1 transition, 45 minutes average.
3. `Triage -> Treatment`: 2 transitions, 37.5 minutes average.
4. `Diagnosis -> Treatment`: 2 transitions, 30 minutes average.
5. `Triage -> Diagnosis`: 2 transitions, 27.5 minutes average.
6. `Admission -> Triage`: 3 transitions, 15 minutes average.
7. `Diagnosis -> Triage`: 1 transition, 15 minutes average.
8. `Triage -> Triage`: 1 transition, 5 minutes average; it is a loop-back in 1
   of 4 cases (25%).

For the standalone legacy calculator, run
`python .\process_mining\bottlenecks.py --verify` to run its synthetic checks,
or pass it an input CSV to write its separate ranked chart and CSV:

```powershell
python .\process_mining\bottlenecks.py `
  --input .\process_mining\sample_event_log.csv
```

The other existing process-mining scripts can be run separately from the
repository root:

```powershell
python .\process_mining\process_discovery.py
python .\process_mining\major_paths.py
```

These are not required for the Week 3 bottleneck or Power BI workflow. The
primary Week 3 outputs come from the two commands in that workflow above.

This workflow covers Week 3 only; it does not run or modify conformance
checking.

## Power BI dashboard tables and BigQuery

`build_dashboard_tables.py` builds six dashboard tables from the same
`case_id`, `activity`, and `timestamp` event-log columns used by the discovery
and bottleneck scripts. From the repository root in Windows PowerShell, run:

```powershell
python .\process_mining\build_dashboard_tables.py
```

The default sample log is `process_mining\sample_event_log.csv`; the six
snake_case CSV files are written to `process_mining\output\powerbi\`. To use
another event log, pass `--input .\path\to\event_log.csv`.

The new `load_outputs_to_bigquery.py` loads every CSV in that folder to a
`pm_`-prefixed BigQuery table, replacing existing table contents. Set
`GOOGLE_CLOUD_PROJECT` and `BIGQUERY_DATASET`, then preview or run the load:

```powershell
$env:GOOGLE_CLOUD_PROJECT = 'your-project-id'
$env:BIGQUERY_DATASET = 'your_dataset'
python .\process_mining\load_outputs_to_bigquery.py --dry-run
python .\process_mining\load_outputs_to_bigquery.py
```

The real load uses Google Cloud Application Default Credentials. The dry run
does not require authentication. See
[`POWERBI_GUIDE.md`](POWERBI_GUIDE.md) for table definitions and suggested
Power BI visuals. The dashboard tables are a Week 3 deliverable and do not
perform conformance checking.
