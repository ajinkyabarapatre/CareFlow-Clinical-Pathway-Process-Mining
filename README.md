# CareFlow Clinical Pathway Process Mining

## Member 3: activity-transition bottlenecks

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
