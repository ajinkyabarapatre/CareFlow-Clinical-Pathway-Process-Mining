# CareFlow Clinical Pathway Process Mining

## Member 3: activity-transition bottlenecks

`process_mining/bottlenecks.py` calculates the average and median waiting time
between consecutive activities, along with the number of cases and observed
transitions for each activity pair. It reads a CSV with `case_id`, `activity`,
and `timestamp` columns. Timestamps should be ISO-8601; timestamps without an
explicit timezone are interpreted as UTC. Waiting times are reported in hours
and rounded to three decimal places.

Run the built-in synthetic-data self-check from the repository root:

```powershell
python .\process_mining\bottlenecks.py --verify
```

Analyze an event log and write the results to
`process_mining/outputs/bottlenecks.csv`:

```powershell
python .\process_mining\bottlenecks.py --input .\path\to\event_log.csv
```

To choose another output location, add `--output .\path\to\results.csv`.
The output directory is created automatically. No event-log data is included
in this repository; provide the project event log when running the analysis.
