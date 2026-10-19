# CareFlow Clinical Pathway Process Mining

## Member 3: activity-transition bottlenecks

`process_mining/bottleneck_analysis.py` writes mean, median, maximum, and
90th-percentile waiting times for every directly-follows activity pair. Pairs
are ranked by mean waiting time, with the top three flagged as bottlenecks.
Run it from the repository root (the sample event log is used by default):

```powershell
python .\process_mining\bottleneck_analysis.py
```

The results are written to `process_mining/output/bottlenecks.csv`, with a
mean-wait performance DFG at `process_mining/output/performance_dfg.png` and a
top-10 transition bar chart at
`process_mining/output/top_10_slowest_transitions.png`. Pass `--input` to
analyze a different CSV. The SQL equivalent is in
`sql/04_bottleneck_metrics.sql`; its metric and ranking column names match the
Python CSV.

`process_mining/bottlenecks.py` converts the event log to a PM4Py event log and
dataframe, then calculates average, median, and maximum waiting time in hours,
case count, and transition count for every consecutive activity pair. It ranks
transitions by average waiting time and writes the ranked results and top-10
chart to `process_mining/outputs/`.

Install the project dependencies from the repository root:

```powershell
python -m pip install -r requirements.txt
```

The input CSV must contain `case_id`, `activity`, and `timestamp` columns.
Timestamps must be ISO-8601; timestamps without a timezone are interpreted as
UTC. Missing or invalid timestamps are reported with their CSV row number.
Events with equal timestamps are ordered by activity and then source row, so
their waiting time is zero. If `department` and/or `patient_group` columns are
present, the output also includes breakdowns using the source event's group.

Analyze a patient event log from the repository root:

```powershell
python .\process_mining\bottlenecks.py --input .\path\to\event_log.csv
```

By default, the script writes `process_mining/outputs/bottlenecks.csv` and
`process_mining/outputs/bottlenecks.png`. Override either output path as needed:

```powershell
python .\process_mining\bottlenecks.py --input .\path\to\event_log.csv `
  --output .\path\to\bottlenecks.csv `
  --chart-output .\path\to\bottlenecks.png
```

Run the synthetic self-check, including the PM4Py conversion and output checks:

```powershell
python .\process_mining\bottlenecks.py --verify
```

The equivalent BigQuery top-10 query is in `sql/05_bottlenecks.sql`. Replace
the example table path there with the event-log table. The checked-in
`process_mining/outputs/bottlenecks_sample.csv` contains synthetic results only;
provide the patient event log to produce real results.

## Member 3: clinical-pathway conformance

`process_mining/conformance_check.py` replays each case against the ideal
`Admission -> Triage -> Diagnosis -> Treatment -> Discharge` pathway and writes
per-case fitness, conformance, and deviation flags to
`process_mining/output/conformance_results.csv`. Run it from the repository
root:

```powershell
python -m pip install pm4py pandas
python .\process_mining\conformance_check.py
```

The input CSV (`process_mining/sample_event_log.csv`) must contain `case_id`,
`activity`, and `timestamp`; events are ordered by timestamp, then activity.
Token-replay fitness of `1.0` indicates a perfect replay. Lower scores reflect
missing or extra token behavior; they are not a literal percentage of correct
activities or a measure of clinical severity. Conformance is determined by an
exact match to the ideal activity sequence, while the CSV identifies skipped,
repeated, and out-of-order steps. `sql/06_conformance_summary.sql` provides the
matching BigQuery conforming/non-conforming case counts; replace its example
table path with the event-log table.

1234

## Process discovery

`process_mining/process_discovery.py` reads the sample event log, orders events
by timestamp, converts them to a PM4Py event log, and discovers a frequency
directly-follows graph (DFG) and an Inductive Miner Petri net. It prints the
number of cases, activities, and variants, and writes the visualizations to
`process_mining/output/dfg.png` and `process_mining/output/petri_net.png`.

Run from the repository root:

```powershell
python .\process_mining\process_discovery.py
```

## Major patient paths

`process_mining/major_paths.py` reports the five most frequent patient-path
variants, their case counts, and their percentage of all cases. It writes the
table to `process_mining/output/top_variants.csv`, and saves a DFG containing
the most frequent paths to `process_mining/output/major_paths.png`. The script
also prints a plain-English summary of those pathways.

Run from the repository root:

```powershell
python .\process_mining\major_paths.py
```
