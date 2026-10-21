# CareFlow Clinical Pathway Process Mining

## Overview

CareFlow's process-mining work examines timestamped patient activity events.
It reconstructs observed pathways, summarizes common activity sequences,
measures time between consecutive activities, and checks traces against one
explicitly defined ideal pathway.

Member 3's implementation is in `process_mining/` and `sql/04-06`.
The Python scripts use PM4Py and pandas, and the SQL scripts are BigQuery SQL.
The analysis outputs are written under `process_mining/output/`.

The checked-in sample event log is a small demonstration dataset. Its cases
include a complete ideal sequence as well as a missing activity, a repeated
activity, and an activity-order deviation. The sample therefore exercises
several of the current analysis paths; it is not a specification for every
possible clinical pathway.

This repository contains scripts and query text, not a configured BigQuery
project, a Power BI report, or credentials for either service. Set the
BigQuery table path in a query before running it against a real table.

## Member 3 scope

| Week | Task | Script | Output |
| --- | --- | --- | --- |
| Week 2 | Discover the observed directly-follows graph and an Inductive Miner Petri net. | `process_mining/process_discovery.py` | `process_mining/output/dfg.png`; `process_mining/output/petri_net.png` |
| Mid-review | Rank frequent patient activity variants and visualize their combined directly-follows graph. | `process_mining/major_paths.py` | `process_mining/output/top_variants.csv`; `process_mining/output/major_paths.png` |
| Week 3 | Calculate directly-follows waiting-time metrics and flag the three highest-mean transitions. | `process_mining/bottleneck_analysis.py` | `process_mining/output/bottlenecks.csv`; `process_mining/output/performance_dfg.png`; `process_mining/output/top_10_slowest_transitions.png` |
| Supporting analysis | Calculate ranked bottleneck metrics with optional `department` and `patient_group` breakdowns; provide a synthetic verification mode. | `process_mining/bottlenecks.py` | `process_mining/output/ranked_bottlenecks.csv`; `process_mining/output/ranked_bottlenecks.png` |
| Week 4 | Replay each case against the fixed ideal pathway; flag compliance and export per-case deviations and token-replay fitness. | `process_mining/conformance_check.py`; `sql/06_conformance_summary.sql` | `process_mining/output/conformance_results.csv`; BigQuery summary rows |
| BigQuery support | Calculate transition metrics and summarize compliant cases with ranked deviation types. | `sql/04_bottleneck_metrics.sql`; `sql/05_bottlenecks.sql`; `sql/06_conformance_summary.sql` | BigQuery query result sets; no local output file is written by the SQL files. |

The supporting-analysis row documents the alternate bottleneck analyzer.
The BigQuery-support row lists the SQL versions that complement the dated
Python assignment work.

## Folder tree

```text
CareFlow-Clinical-Pathway-Process-Mining/
|-- README.md
|-- requirements.txt
|-- process_mining/
|   |-- sample_event_log.csv
|   |-- process_discovery.py
|   |-- major_paths.py
|   |-- bottleneck_analysis.py
|   |-- bottlenecks.py
|   |-- conformance_check.py
|   `-- output/
|       |-- dfg.png
|       |-- petri_net.png
|       |-- discovery_summary.csv
|       |-- major_paths.png
|       |-- top_variants.csv
|       |-- bottlenecks.csv
|       |-- bottlenecks_sample.csv
|       |-- performance_dfg.png
|       |-- top_10_slowest_transitions.png
|       `-- conformance_results.csv
|-- tests/
|   `-- test_process_mining.py
`-- sql/
    |-- 04_bottleneck_metrics.sql
    |-- 05_bottlenecks.sql
    `-- 06_conformance_summary.sql
```

The output directory is named `output` (singular). New generated analysis
files belong in `process_mining/output/`; do not create a second output
directory for this work.

The files shown below `output/` are the output files currently present in the
repository. `ranked_bottlenecks.csv` and `ranked_bottlenecks.png` are not in
that current listing; they are the default paths used by `bottlenecks.py`
when that script runs.

## Setup

### Python environment

Run the following commands from the repository root in Windows PowerShell.
The repository dependency manifest is `requirements.txt`.

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell does not recognize `py`, use an installed `python` command
instead:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The scripts and tests use Python packages listed in `requirements.txt`:

| Package | Role in the repository |
| --- | --- |
| `pm4py` | Event-log conversion, process discovery, and conformance replay. |
| `pandas` | CSV event-log handling, ordering, grouping, and tabular outputs. |
| `matplotlib` | PNG charts and graph rendering. |
| `networkx` | DFG and Petri-net graph layouts used in `process_discovery.py`. |
| `pytest` | Focused automated checks for variants, timing metrics, and conformance exports. |

The manifest does not pin package versions or state a supported Python
version. Use a Python installation compatible with the packages installed
from the manifest.

To leave the virtual environment after running the scripts:

```powershell
deactivate
```

### Graphviz on Windows

The current graph renderers in `process_discovery.py` use NetworkX and
Matplotlib. Their docstrings explicitly note that they do not require the
Graphviz executable. Graphviz is therefore optional for the scripts
documented here.

If another PM4Py rendering path or a local workflow you use requires the
Graphviz command-line tools, download the Windows package from
[graphviz.org/download](https://graphviz.org/download/), install it, and add
its `bin` directory (commonly `C:\Program Files\Graphviz\bin`) to the
Windows `PATH`. Open a new PowerShell window and check that Windows can find
the executable:

```powershell
dot -V
```

A missing `dot` command does not by itself prevent the current NetworkX /
Matplotlib DFG and Petri-net rendering paths from running.

### Dependencies

Install the repository's dependencies from the root directory:

```powershell
pip install -r requirements.txt
```

To verify that the active interpreter can import the listed top-level
packages:

```powershell
python -c "import matplotlib, networkx, pandas, pm4py; print('Imports OK')"
```

Activate `.venv` before installing or running the project so that `pip` and
`python` use the same environment.

### Run the tests

From the repository root, run the focused synthetic tests with:

```powershell
python -m pytest -q tests\test_process_mining.py
```

The tests check variant ranking and coverage, transition wait statistics,
timestamp-row error reporting, conformance deviation labels, and the CSV
output column contracts. They use synthetic cases and do not require patient
data.

## Input CSV format

The Python event-log readers require these three CSV columns:

| Column | Required | Meaning in these scripts |
| --- | --- | --- |
| `case_id` | Yes | Identifies the case whose events form one trace. |
| `activity` | Yes | Activity label recorded for one event. |
| `timestamp` | Yes | Event time; parsed as a timestamp and used to order events. |

The header spelling is significant. The Python readers reject missing
required columns, empty case identifiers, empty activity values, empty
timestamps, and timestamps that cannot be parsed. Timestamp errors identify
the CSV row number (including the header) and the invalid value.

The sample file uses ISO-8601 UTC timestamps with a trailing `Z`. This is a
valid example of the expected structure:

```csv
case_id,activity,timestamp
case-001,Admission,2026-10-01T08:00:00Z
case-001,Triage,2026-10-01T08:15:00Z
case-001,Diagnosis,2026-10-01T08:45:00Z
case-001,Treatment,2026-10-01T09:15:00Z
case-001,Discharge,2026-10-01T10:00:00Z
case-002,Admission,2026-10-02T08:00:00Z
case-002,Triage,2026-10-02T08:15:00Z
case-002,Treatment,2026-10-02T09:15:00Z
case-002,Discharge,2026-10-02T10:00:00Z
```

For `bottlenecks.py`, the CSV may also include `department` and
`patient_group`. When either column exists, the script calculates
dimension-specific rows in addition to the ungrouped (`all`) rows. Empty
dimension values are labeled `Unspecified` by that script.

The other Python scripts require the three core columns; they do not use
`department` or `patient_group` for their outputs.

### Input ordering

The event readers sort each case's events by timestamp before interpreting
the sequence. The bottleneck scripts also use activity text and source row
order to make same-timestamp ordering deterministic.

When two events have the same timestamp, their measured elapsed time is zero.
The ordering of tied events can affect which directly-follows transition is
counted, so use meaningful event times and stable activity labels.

### Ideal sequence used for conformance

The current Python conformance model and the SQL conformance query use this
fixed ideal sequence:

```text
Admission -> Triage -> Diagnosis -> Treatment -> Discharge
```

The sample log has exactly four cases. Only `case-001` follows that full
sequence once and in order. The conformance checker also records a skipped
activity, a repeated activity, or an out-of-order activity when applicable.

This is the pathway encoded in the current files, not a configurable model
loaded from a separate pathway definition. The conformance CSV reports every
applicable deviation label: `skipped`, `repeated`, `out_of_order`, and
`extra_activity`. Multiple labels are separated with semicolons; a compliant
case has `deviation_type` set to `none`.

## How to run each script

Run commands from the repository root after activating the environment.
The examples use PowerShell's `.\` path syntax.

### Discover the process: `process_discovery.py`

```powershell
python .\process_mining\process_discovery.py
python .\process_mining\process_discovery.py --input .\path\to\event_log.csv
```

The sample CSV is the default. `--input` can point to another CSV using the
same required columns. The script reports case, event, activity, variant,
and case-duration metrics; it writes the metrics to
`process_mining/output/discovery_summary.csv` as well as the frequency DFG
and Inductive Miner Petri-net images.

### Summarize major paths: `major_paths.py`

```powershell
python .\process_mining\major_paths.py
python .\process_mining\major_paths.py --input .\path\to\event_log.csv --top 8 --coverage 0.9
```

The script defaults to the sample event log, a maximum of five variants,
and a cumulative coverage target of `0.8` (80%). Selection stops when either
the coverage target is reached or the `--top` limit is reached. The CSV
reports rank, complete variant, case count, and percentage of all cases.
The graph is discovered only from cases belonging to the selected variants.

Set `--coverage` to a fraction greater than zero and at most one. If the top-N
limit is reached before the target, the script says so in its plain-English
summary.

### Measure bottlenecks: `bottleneck_analysis.py`

Use the checked-in sample by default:

```powershell
python .\process_mining\bottleneck_analysis.py
```

The optional `--input` argument selects a different CSV event log:

```powershell
python .\process_mining\bottleneck_analysis.py `
  --input .\path\to\event_log.csv
```

The script calculates transition counts and mean, median, maximum, and
90th-percentile waiting times in hours. It ranks all observed activity
pairs by mean wait and marks the first three rows with `is_bottleneck`.
It writes the ranked CSV, a performance DFG with mean waits, and a chart of
up to ten slowest transitions.

This script's output paths are fixed under `process_mining/output/`; it does
not expose output-path arguments.

### Run the alternate bottleneck analyzer: `bottlenecks.py`

This script requires `--input` unless `--verify` is used:

```powershell
python .\process_mining\bottlenecks.py `
  --input .\process_mining\sample_event_log.csv
```

Its optional arguments choose the two output locations. The defaults remain
inside the single `process_mining/output/` folder:

```powershell
python .\process_mining\bottlenecks.py `
  --input .\process_mining\sample_event_log.csv `
  --output .\process_mining\output\ranked_bottlenecks.csv `
  --chart-output .\process_mining\output\ranked_bottlenecks.png
```

This analyzer reports average, median, and maximum waiting times, case and
transition counts, and a rank for each transition in each available scope.
It includes `department` and `patient_group` scopes when those columns are
present. The CSV contains the complete set of ranked rows; the PNG charts up
to ten ungrouped transitions.

The `--verify` option runs the script's built-in synthetic checks and does
not require a patient event-log file:

```powershell
python .\process_mining\bottlenecks.py --verify
```

`--verify` cannot be combined with `--input`. It checks representative
metrics, same-time event handling, grouping, PM4Py conversion, and temporary
CSV / PNG output generation.

The verification outputs are created in a temporary directory, not in
`process_mining/output/`.

### Check conformance: `conformance_check.py`

```powershell
python .\process_mining\conformance_check.py
python .\process_mining\conformance_check.py --input .\path\to\event_log.csv
```

The sample CSV is the default. Use `--input` to choose another event log.
The script constructs the ideal Petri net in code and performs PM4Py
token-based replay. The output CSV has one flat row per case with
`case_id`, `fitness_score`, `is_compliant`, `deviation_type`,
`trace_variant`, and `duration_hours`.

`fitness_score` is a token-replay fitness value: **1.0 means perfect replay;
it is not a percentage**. `is_compliant` is stricter: it is true only when
the complete activity sequence exactly matches the ideal pathway and PM4Py
reports a fit replay. Fitness is not a measure of clinical severity.

### Run BigQuery SQL files

The SQL is not launched by the Python scripts. Open the desired query in a
BigQuery SQL editor, replace every applicable placeholder table path
(`project.dataset.event_log`) with the fully qualified event-log table, and
run the query there.

The SQL queries use the required `case_id`, `activity`, and `timestamp`
fields and contain an assertion that fails when those values are null or
blank. Check that your BigQuery table has the expected column names and
types before running the query.

## Outputs

All local generated analysis files belong under
`process_mining/output/`.

| Output | Created by | Contents |
| --- | --- | --- |
| `process_mining/output/dfg.png` | `process_discovery.py` | Frequency DFG with observed start and end activity counts and edge frequencies. |
| `process_mining/output/petri_net.png` | `process_discovery.py` | Petri net discovered with PM4Py's Inductive Miner. |
| `process_mining/output/discovery_summary.csv` | `process_discovery.py` | One-row counts and average / maximum case duration in hours. |
| `process_mining/output/top_variants.csv` | `major_paths.py` | Up to five ranked variants with case counts and percentages. |
| `process_mining/output/major_paths.png` | `major_paths.py` | Frequency DFG discovered from cases in the leading variants. |
| `process_mining/output/bottlenecks.csv` | `bottleneck_analysis.py` | All observed transition pairs, waiting-time metrics, rank, and top-three flag. |
| `process_mining/output/performance_dfg.png` | `bottleneck_analysis.py` | Performance DFG with mean transition waits displayed in hours. |
| `process_mining/output/top_10_slowest_transitions.png` | `bottleneck_analysis.py` | Horizontal chart of up to ten transitions with the largest mean waits. |
| `process_mining/output/ranked_bottlenecks.csv` | `bottlenecks.py` | Ranked transition metrics for all and any available dimension scopes. |
| `process_mining/output/ranked_bottlenecks.png` | `bottlenecks.py` | Horizontal chart of up to ten ungrouped transitions. |
| `process_mining/output/conformance_results.csv` | `conformance_check.py` | Flat per-case fitness, compliance flag, deviation types, variant, and duration in hours. |

The output directory currently includes `bottlenecks_sample.csv`, which is
an example table with `from_activity`, `to_activity`, average and median
waiting time, case count, and transition count. It is not a default output
name used by either current bottleneck script.

### Interpreting the metrics

Transition waiting time is the elapsed time between consecutive events in
one case. The scripts express that interval in hours.

The `transition_count` field counts observed occurrences of an activity
pair. It is not necessarily the same as the number of distinct cases.

`case_count` is included by `bottlenecks.py` and `sql/05_bottlenecks.sql`;
it counts distinct cases contributing that transition.

The pandas bottleneck script marks the three transitions with the highest
mean wait as `is_bottleneck = True`. It still writes the ranked metrics for
all transitions.

The alternate Python analyzer ranks within each scope (`all`,
`department`, or `patient_group`) and uses average, median, and maximum wait
to sort ties before activity names.

The BigQuery files use their own specified output fields and ranking rules.
Review the query file used to interpret a returned result set; field names
and top-N behavior are not identical across the two Python bottleneck
implementations and the two SQL bottleneck queries.

## Methodology

### Directly-Follows Graph (DFG)

A directly-follows edge `A -> B` represents an event for activity `B`
immediately following activity `A` in the timestamp-ordered trace for a
case.

The discovery script uses PM4Py's discovered DFG and draws it with
NetworkX and Matplotlib. Its edge labels show frequency counts; node labels
also show start and end counts when those counts are present.

The major-path script first builds activity tuples by case, counts identical
tuples, selects up to five most common variants, and then discovers a DFG
over the events for cases in those variants.

The bottleneck scripts use the same consecutive-event concept to calculate
waiting time. A DFG edge can appear frequently but have short waits, or
appear less frequently and have long waits; frequency and duration are
different measures.

The performance DFG from `bottleneck_analysis.py` displays the mean
waiting-time performance value on each edge. It is a different view from
the frequency DFG created by `process_discovery.py`.

### Petri net

`process_discovery.py` calls PM4Py's Inductive Miner Petri-net discovery on
the sample event log. The generated model is inferred from the observed
event log; it is not the ideal model used by the conformance checker.

`conformance_check.py` separately builds a linear Petri net with one
transition for each activity in the fixed ideal sequence. Its purpose is to
provide a reference trace for token replay, not to discover a model from
the sample.

### Bottleneck metrics

For each case, events are ordered and consecutive events form transition
observations. For an observation, waiting time is the difference between
the next event timestamp and the current event timestamp.

`bottleneck_analysis.py` aggregates waits for each `(from_activity,
to_activity)` pair and reports:

| Field | Meaning |
| --- | --- |
| `transition_count` | Number of observed consecutive event pairs for the activity pair. |
| `mean_waiting_time_hours` | Arithmetic mean elapsed time in hours. |
| `median_waiting_time_hours` | Median elapsed time in hours. |
| `max_waiting_time_hours` | Maximum observed elapsed time in hours. |
| `p90_waiting_time_hours` | 90th percentile using pandas' linear quantile interpolation. |
| `bottleneck_rank` | Rank sorted by descending mean wait, then activity names. |
| `is_bottleneck` | `True` for the first three ranked transitions, otherwise `False`. |

`bottlenecks.py` outputs average, median, and maximum wait, plus the count of
cases and transition observations. It ranks independently for `all` and
each available optional dimension value.

`sql/04_bottleneck_metrics.sql` reports mean, median, maximum, and 90th
percentile waits, transition count, rank, and a boolean for the top three.
`sql/05_bottlenecks.sql` reports the top ten by average wait, with median
and maximum values and case / transition counts.

These measures identify long observed intervals. They do not, by
themselves, establish why a wait occurred or whether a wait is clinically
inappropriate.

### Conformance and fitness

The Python conformance checker token-replays each trace against the
five-activity ideal Petri net. It writes the PM4Py `trace_fitness` value to
`fitness_score`, and computes `is_compliant` using both replay fit and exact
sequence equality. The CSV also includes `trace_variant` and
`duration_hours`.

A fitness value of `1.0` means a perfect replay of that trace against the
model. It is a fitness score, **not a percentage**. For example, `0.8`
must not be described as “80% of the activities were correct.”

The overall fitness printed by the script is the arithmetic mean of the
per-trace fitness scores. It is not a clinical severity rating.

The `deviation_type` field lists all detected deviation labels: missing
activities (`skipped`), repeated ideal activities (`repeated`), activity
order reversals (`out_of_order`), and activities outside the ideal pathway
(`extra_activity`). Labels are semicolon-separated if a trace has multiple
deviation types; a fully compliant trace uses `none`.

The SQL conformance query applies exact sequence matching and returns a
compliance summary plus ranked counts by deviation type. It does not
calculate token-replay fitness.

## SQL files

The three SQL files are BigQuery Standard SQL scripts. Each uses
`project.dataset.event_log` as an example table path; replace that path with
the target table before execution.

### `sql/04_bottleneck_metrics.sql`

This query first asserts that `case_id`, `activity`, and `timestamp` are
populated. It then orders events within each case and pairs each event with
its next event.

The result includes one row per observed activity transition, along with
transition count, mean / median / maximum / 90th-percentile waiting time,
rank, and `is_bottleneck`. The boolean is true for ranks one through three.

The median and 90th percentile are calculated with `PERCENTILE_CONT`.
Waiting-time units in the result are hours.

### `sql/05_bottlenecks.sql`

This query also validates the required columns and derives consecutive
activity pairs in case order. It ranks by average waiting time, then by
median and maximum waiting time, followed by activity names for stable
tie-breaking.

Only the first ten ranked activity pairs are returned. Output fields include
rank, from / to activity, average / median / maximum waiting time in hours,
distinct case count, and transition count.

The comments in the SQL describe how the query could be extended with
`department` and `patient_group` dimensions; the current query does not
include those dimensions in its result.

### `sql/06_conformance_summary.sql`

This query validates the required columns, orders each case's activity
array by timestamp and activity text, and compares it with the exact ideal
sequence.

The result contains one `compliance_summary` row with total, compliant, and
non-compliant case counts, followed by ranked `deviation_type` rows. Each
case contributes at most once to each applicable deviation category. SQL
does not calculate token-replay fitness; use the Python per-case CSV for
fitness scores and Power BI detail.

## Power BI import

No Power BI project or report file is present in this repository. Use the
generated CSVs and PNGs as source material for a report you create.

### Import local CSV outputs

1. Run the desired Python script from the repository root.
2. In Power BI Desktop, use **Get data** and select the text/CSV source.
3. Browse to a CSV under `process_mining/output/`.
4. Inspect the detected headers and data types in the preview.
5. Load the table or transform it in Power Query before loading.

Useful CSV tables include:

| CSV | Useful fields |
| --- | --- |
| `top_variants.csv` | `rank`, `variant`, `case_count`, `percentage`. |
| `bottlenecks.csv` | `from_activity`, `to_activity`, transition count, waiting-time measures, rank, and top-three flag. |
| `ranked_bottlenecks.csv` | Scope, group value, rank, transition names, average / median / maximum waits, and counts. |
| `conformance_results.csv` | `case_id`, `fitness_score`, `is_compliant`, `deviation_type`, `trace_variant`, and `duration_hours`. |

The `bottlenecks.csv` schema and `ranked_bottlenecks.csv` schema differ.
Choose the one that matches the script you ran and inspect its header row.

### Import BigQuery results

Run a SQL file in BigQuery after replacing its example table path. The
repository does not provide BigQuery connection settings or credentials.
Use the BigQuery result set or export the query results to CSV, then import
the resulting data into Power BI using the method approved for your
environment.

The SQL query result is not automatically written into the local
`process_mining/output/` directory.

### Use generated images

PNG files can be opened separately or added to a report as image assets.
They are static visualizations; their labels and values do not filter with
Power BI slicers.

Use `dfg.png` for a frequency graph, `petri_net.png` for the discovered
Petri net, `major_paths.png` for frequent variants, and the bottleneck
charts for waiting-time views.

### Interpret Power BI fields

Keep waiting-time columns in hours unless you explicitly convert them.
Retain the original column name or clearly label the converted unit.

Treat `fitness_score` as a replay fitness value from 0 to 1 in this output,
not as a percent-correct measure. Use `is_compliant` for the exact
conformance classification made by the Python script.

For `ranked_bottlenecks.csv`, use `group_by` and `group_value` to distinguish
the ungrouped rows from optional dimension-level rows.

## Troubleshooting

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| `python` or `py` is not recognized. | Python is not installed or its launcher is not available in this PowerShell session. | Install or select an available Python interpreter, then retry `py --version` or `python --version`. |
| `ModuleNotFoundError` for PM4Py, pandas, Matplotlib, NetworkX, or pytest. | Dependencies were not installed into the active interpreter. | Activate `.venv` and run `pip install -r requirements.txt`. |
| The imports work in one terminal but not another. | The two terminals are using different Python environments. | Activate `.\.venv\Scripts\Activate.ps1` in the terminal used to run the script. |
| PowerShell blocks virtual-environment activation. | The current PowerShell execution-policy configuration blocks the activation script. | Use an approved local execution-policy approach or run the environment's Python executable directly as `.\.venv\Scripts\python.exe`. |
| `Event log is missing required columns`. | The CSV header does not include one or more required exact names. | Use `case_id`, `activity`, and `timestamp` as the CSV headers. |
| The script reports an empty `case_id` or `activity`. | At least one row has a blank required identifier or activity. | Correct or remove the invalid row in the source CSV and rerun. |
| Timestamp parsing fails. | A timestamp is blank or is not parseable by the Python reader. | Provide parseable timestamps, preferably ISO-8601 values like `2026-10-01T08:00:00Z`. |
| The timestamp error names one or more CSV rows. | The timestamp field is blank or cannot be parsed in those rows. | Check each reported row number (the header is row 1), correct the timestamp, and rerun. |
| A transition chart has no bars. | The input may contain no consecutive events in a case, so there are no transitions to aggregate. | Check that cases have events and that `case_id` values group the intended event sequences. |
| Same-time events lead to an unexpected transition. | Tied event timestamps require a deterministic ordering rule. | Review the tied activity labels and source-row order; the scripts use activity and/or row order to break ties. |
| `bottlenecks.py` says to provide `--input`. | This script requires an input path unless run in verification mode. | Pass `--input .\process_mining\sample_event_log.csv` or use `--verify`. |
| `--verify` reports it cannot be combined with `--input`. | The verification option intentionally uses its own synthetic input. | Run `python .\process_mining\bottlenecks.py --verify` without `--input`. |
| `dot` is not recognized. | Graphviz is not installed or its `bin` folder is not on `PATH`. | Graphviz is optional for the current NetworkX / Matplotlib output; install and configure it only if another workflow needs `dot`. |
| A BigQuery `ASSERT` fails. | The source table contains null or blank required values, or the configured table path is wrong. | Verify the table path and inspect the `case_id`, `activity`, and `timestamp` values. |
| BigQuery reports an invalid table path. | The example `project.dataset.event_log` placeholder was not replaced. | Replace it in the SQL with the fully qualified target table path. |
| SQL column names are not found. | The BigQuery source schema differs from the fields expected by the query. | Confirm the table contains `case_id`, `activity`, and `timestamp`; update the source mapping deliberately if needed. |
| A Power BI CSV import shows unexpected data types. | Automatic type detection inferred a type different from the intended representation. | Review the preview and explicitly set types in Power Query before loading. |
| A local CSV does not reflect the latest analysis. | The CSV has not been regenerated since the source or script changed. | Rerun the corresponding Python script and reload or refresh the CSV in Power BI. |

## Git workflow: `m3-process-mining`

The working branch for this scope is `m3-process-mining`. Check the current
branch and working tree before making changes:

```powershell
git status --short
git branch --show-current
```

Switch to the branch when it already exists locally:

```powershell
git switch m3-process-mining
```

If starting from a different branch and the branch does not yet exist
locally, create it from the current commit:

```powershell
git switch -c m3-process-mining
```

Review the changes and whitespace before staging:

```powershell
git diff --check
git diff -- README.md
```

Stage only the files intended for the change. For a documentation-only
change:

```powershell
git add README.md
git diff --cached --check
git diff --cached -- README.md
```

Commit the documentation change after reviewing the staged diff:

```powershell
git commit -m "Document Member 3 process mining workflow"
```

Update the branch from its remote before publishing:

```powershell
git pull origin m3-process-mining
git push -u origin m3-process-mining
```

Before staging generated outputs, inspect `git status --short` and select
only the files intended for the commit. The scripts write generated files
inside `process_mining/output/`; avoid accidentally staging unrelated local
files.
