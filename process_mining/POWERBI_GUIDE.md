# Week 3 Power BI dashboard

## Build the dashboard data

From the repository root in Windows PowerShell, generate the six CSV tables:

```powershell
python .\process_mining\build_dashboard_tables.py
```

By default, the script reads `process_mining\sample_event_log.csv` and writes
the files to `process_mining\output\powerbi\`. You can provide a different
event log or output folder:

```powershell
python .\process_mining\build_dashboard_tables.py `
  --input .\path\to\event_log.csv `
  --output-directory .\process_mining\output\powerbi
```

The event log uses the established `case_id`, `activity`, and `timestamp`
columns. All exported headers are snake_case. `start_time` and `end_time` are
UTC ISO 8601 timestamps.

## Connect Power BI Desktop to BigQuery

1. Generate the CSVs, then load them to BigQuery with the command below.
2. In Power BI Desktop, select **Get Data -> Google BigQuery**.
3. Sign in with an account that can access the configured Google Cloud project
   and dataset.
4. Select the project and dataset, then select the generated `pm_` tables.
5. Choose **Load** (or **Transform Data** first if you need to adjust types).

Import these six tables:

| BigQuery table | Use |
| --- | --- |
| `pm_process_map_edges` | Directed activity transitions, distinct case counts, and average waits. |
| `pm_process_map_nodes` | Activity event/case counts and average time before the next step. |
| `pm_case_summary` | Case dates, duration, event count, loop-back flag, and path. |
| `pm_variant_summary` | Case count, share of cases, and mean duration for each path. |
| `pm_kpi_summary` | One-row overall KPIs and the highest-wait transition. |
| `pm_hourly_arrivals` | Cases grouped by UTC arrival hour and average duration. |

## Suggested visuals

- **KPI cards:** `total_cases`, `total_events`,
  `avg_case_duration_minutes`, `median_case_duration_minutes`, and
  `pct_cases_with_loopback` from `pm_kpi_summary`.
- **Process flow visual:** use `from_activity` and `to_activity` from
  `pm_process_map_edges`; size edges by `case_count` and show
  `avg_wait_minutes` in tooltips.
- **Bottlenecks bar chart:** use `from_activity` and `to_activity` as the
  transition label and `avg_wait_minutes` as the value, sorted descending.
- **Variants table:** show `path_variant`, `case_count`, `pct_of_cases`, and
  `avg_duration_minutes` from `pm_variant_summary`.
- **Hourly arrivals line chart:** use `hour_of_day` on the X axis and
  `case_count` on the Y axis; optionally add average duration as a second
  series or tooltip.

For detailed transition percentiles and loop-back transition counts, the
existing `export_for_powerbi.py` outputs remain available under
`process_mining\output\`. This dashboard build does not perform Week 4
conformance checking.

## Load the CSVs to BigQuery

Set the project and dataset in the current PowerShell session. BigQuery
authentication uses the normal Google Cloud authentication flow; no
credentials are stored in the repository.

```powershell
$env:GOOGLE_CLOUD_PROJECT = 'your-project-id'
$env:BIGQUERY_DATASET = 'your_dataset'
python .\process_mining\load_outputs_to_bigquery.py --dry-run
python .\process_mining\load_outputs_to_bigquery.py
```

The loader uses Application Default Credentials when it performs a real load.
Every CSV in the dashboard output folder becomes a `pm_<csv-name>` table, and
each load uses `WRITE_TRUNCATE`. Use `--input-directory` to load a different
folder. `--dry-run` only lists the planned loads and does not require project,
dataset, or credential configuration.
