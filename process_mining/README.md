# Week 3: Bottleneck calculations

This module calculates elapsed time between consecutive activities in each
case. It accepts the sample CSV column names (`case_id`, `activity`,
`timestamp`) and the dbt event-log names (`Case_ID`, `Activity_Name`,
`Timestamp`). The repository currently has no dbt model or configured
BigQuery table, so the Python command uses the checked-in CSV fallback.

## Run

From the repository root in Windows PowerShell, activate the repository
environment and run:

```powershell
.\.venv\Scripts\Activate.ps1
python .\process_mining\bottleneck_analysis.py
```

To read a different CSV file instead of the bundled sample:

```powershell
python .\process_mining\bottleneck_analysis.py `
  --input .\path\to\event_log.csv
```

To query a BigQuery table instead of the CSV fallback, set the table name in
`CAREFLOW_BIGQUERY_TABLE` or pass it explicitly:

```powershell
$env:CAREFLOW_BIGQUERY_TABLE = 'project.dataset.event_log'
python .\process_mining\bottleneck_analysis.py --bigquery-table `project.dataset.event_log`
```

The input must contain one of each corresponding pair of column names:
`case_id` or `Case_ID`, `activity` or `Activity_Name`, and `timestamp` or
`Timestamp`. Case IDs and activities must be populated, timestamps must be
valid, and consecutive event timestamps must increase strictly. The script
checks the calculated transition count against `events - cases`, rejects any
negative transition durations, and verifies the mean transition waits against
PM4Py's performance DFG before writing its results.

## Outputs

All generated files go under `process_mining/output/`:

| File | Contents |
| --- | --- |
| `bottleneck_transitions.csv` | Power BI-friendly one-row-per-transition table with transition counts, average/median/90th-percentile/maximum waits in minutes, percentage of all transitions, and rank. |
| `performance_dfg.png` | Performance directly-follows graph with mean elapsed time shown on each edge. |
| `bottlenecks.csv` | Compatibility export containing the existing ranked metrics in hours and the additional minute and percentage fields. |
| `top_10_slowest_transitions.png` | Existing chart of up to ten transitions with the highest average wait. |

The query file `sql/05_bottleneck_transitions.sql` contains a BigQuery query
for the same transition metrics and a second result set for returns to
previously visited activities, including affected-case percentages. Like the
other SQL files, it uses the repository's existing placeholder
`project.dataset.event_log`; replace that table path with the deployed table
before execution. It expects `Case_ID`, `Activity_Name`, and `Timestamp`.

## Findings from the checked-in sample

The sample has four cases. The script prints the ten highest-mean transitions
to the console after verifying the output. The top bottleneck transition(s)
from that sample are:

- `Treatment -> Discharge`: 4 occurrences, average wait 45 minutes.
- `Admission -> Diagnosis`: 1 occurrence, average wait 45 minutes.
- `Triage -> Treatment`: 2 occurrences, average wait 37.5 minutes.

The sample contains 20 events and 4 cases, giving 16 consecutive transitions;
all 16 were counted, had positive durations, and agreed with PM4Py's
performance DFG means.

Re-run the command above after changing the sample or its event-log input to
refresh the findings and generated output files. This work covers Week 3
bottleneck calculations only; it does not implement or change conformance
checking.
