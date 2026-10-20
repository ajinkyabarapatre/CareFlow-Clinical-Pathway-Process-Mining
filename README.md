# CareFlow Clinical Pathway Process Mining

This project analyzes hospital patient pathways using process mining to understand the as-is care flow, identify bottlenecks in activity transitions, and highlight cases that do not follow the expected clinical sequence. The work combines PM4Py-based analysis, SQL-based BigQuery summaries, and generated output files to support process review and improvement discussions.

## Member 3 scope

| Week | Task | Script |
| --- | --- | --- |
| Week 2 | Discover the as-is process, including the Directly-Follows Graph and Petri net | `process_mining/process_discovery.py` |
| Mid-review | Graph of major patient paths | `process_mining/major_paths.py` |
| Week 3 | Bottleneck analysis of waiting-time transitions | `process_mining/bottleneck_analysis.py` and `process_mining/bottlenecks.py` |

## Repository area

Member 3 work is centered on the Python process-mining scripts in `process_mining/` and the BigQuery SQL queries in `sql/`.

### Process mining scripts

#### `process_mining/process_discovery.py`
This script reads `process_mining/sample_event_log.csv`, validates the required `case_id`, `activity`, and `timestamp` columns, orders events by timestamp, and converts the event log to a PM4Py log. It discovers a frequency Directly-Follows Graph (DFG) and an Inductive Miner Petri net, then saves the images to `process_mining/output/dfg.png` and `process_mining/output/petri_net.png`. The script prints the number of cases, activities, and variants it found.

#### `process_mining/major_paths.py`
This script groups the event log by `case_id`, identifies the top five activity variants by frequency, and writes the results to `process_mining/output/top_variants.csv`. It then filters the event log to the most frequent variants and saves a DFG image at `process_mining/output/major_paths.png`. The console output summarizes each major patient path with its case count and percentage of total cases.

#### `process_mining/bottleneck_analysis.py`
This script reads the sample event log, validates the required columns, and calculates directly-follows waiting-time metrics for each activity transition. It computes `mean_waiting_time_hours`, `median_waiting_time_hours`, `max_waiting_time_hours`, and `p90_waiting_time_hours`, ranks the transitions by mean waiting time, and flags the top three as bottlenecks. It writes the output to `process_mining/output/bottlenecks.csv`, saves a mean-wait performance DFG to `process_mining/output/performance_dfg.png`, and creates a top-10 chart at `process_mining/output/top_10_slowest_transitions.png`.

#### `process_mining/bottlenecks.py`
This script validates and parses a CSV event log, converts it to a PM4Py event log, and calculates average, median, and maximum waiting times for each consecutive activity pair. It ranks transitions by average waiting time and writes a ranked CSV and chart. The script accepts `--input`, `--output`, and `--chart-output` arguments; the default output files are `process_mining/output/ranked_bottlenecks.csv` and `process_mining/output/ranked_bottlenecks.png`. It also supports `--verify` to run a synthetic check for duplicate-timestamp ordering, PM4Py conversion, grouping logic, and output generation. If `department` and/or `patient_group` columns are present, the output includes breakdowns for those dimension values.

#### `process_mining/conformance_check.py`
This script builds an ideal pathway model for `Admission -> Triage -> Diagnosis -> Treatment -> Discharge` and replays each case against it. It reads the event log, orders events by case and timestamp, calculates token-replay fitness, and creates a per-case output table in `process_mining/output/conformance_results.csv` with `case_id`, `activities`, `fitness_score`, `is_conforming`, and `deviations`. The script reports total, conforming, and non-conforming cases and the overall mean trace fitness.

### BigQuery SQL summaries

#### `sql/04_bottleneck_metrics.sql`
This query validates that `case_id`, `activity`, and `timestamp` are populated in the source table, orders events by case and timestamp, and calculates waiting-time metrics for each directly-follows pair. It outputs `from_activity`, `to_activity`, `transition_count`, `mean_waiting_time_hours`, `median_waiting_time_hours`, `max_waiting_time_hours`, `p90_waiting_time_hours`, `bottleneck_rank`, and `is_bottleneck` for the ranked transition pairs.

#### `sql/05_bottlenecks.sql`
This query ranks the ten slowest activity transitions by average waiting time, with a BigQuery assertion checking required `case_id`, `activity`, and `timestamp` fields. It includes `bottleneck_rank`, `from_activity`, `to_activity`, `avg_waiting_time_hours`, `median_waiting_time_hours`, `max_waiting_time_hours`, `case_count`, and `transition_count` in the result set. The comments note that the same logic can be expanded to include `department` and `patient_group` dimensions when available.

#### `sql/06_conformance_summary.sql`
This query validates the required event-log fields, builds a per-case ordered activity array, and counts whether each case exactly matches the ideal pathway sequence `Admission`, `Triage`, `Diagnosis`, `Treatment`, `Discharge`. The output returns `total_cases`, `conforming_cases`, and `non_conforming_cases` for the event log.

## Input data and output files

The process-mining scripts use the repository sample log at `process_mining/sample_event_log.csv` and store generated outputs in `process_mining/output/`.

Available outputs in the repository include:
- `process_mining/output/dfg.png`
- `process_mining/output/petri_net.png`
- `process_mining/output/major_paths.png`
- `process_mining/output/top_variants.csv`
- `process_mining/output/conformance_results.csv`
- `process_mining/output/bottlenecks_sample.csv`
- `process_mining/output/bottlenecks.csv`
- `process_mining/output/performance_dfg.png`
- `process_mining/output/top_10_slowest_transitions.png`

## Usage

From the repository root, the current scripts can be run as follows:

```powershell
python .\process_mining\process_discovery.py
python .\process_mining\major_paths.py
python .\process_mining\bottleneck_analysis.py
python .\process_mining\bottlenecks.py --input .\path\to\event_log.csv
python .\process_mining\bottlenecks.py --verify
python .\process_mining\conformance_check.py
```

The SQL files are designed for BigQuery event-log tables and require the example table path in each query to be updated to the target dataset and table.
