# CareFlow: Clinical Pathway Process Mining

CareFlow is a project about understanding how patients move through hospital
care. It explores how process mining can turn timestamped activity records into
a process map, helping a team see the order of care steps and where delays or
repeated steps may occur.

The repository includes patient and doctor datasets, a notebook for exploring
the data, an initial PM4Py process-discovery script, and documentation for a
planned Power BI dashboard.

> **Important:** This repository contains patient-related data. Do not publish
> real or identifiable patient information. The process map created by the
> current discovery script uses a small generated example if no event log is
> available; it is not an analysis of `patients.csv`.

## Project goals

- Explore the available patient data and understand its fields.
- Represent care journeys as event logs with a case, activity, and timestamp.
- Use process mining to visualize how activities follow one another.
- Identify potential waiting-time bottlenecks and repeated or unusual steps.
- Plan a dashboard that can help explain results to project stakeholders.

Process maps and waiting-time metrics are intended to support analysis and
discussion. They are not clinical advice and should not be used by themselves
to make patient-care decisions.

## What's in this repository?

| Path | Description |
| --- | --- |
| `patients.csv` | Patient dataset described in the project data dictionary. |
| `doctors.csv` | Doctor dataset. |
| `data.ipynb` | Jupyter notebook for exploring project data. |
| `process_mining/discovery.py` | Initial PM4Py script that discovers activity transitions and saves a process map. |
| `dashboard/` | Draft dashboard layout, KPI definitions, and available screenshots. |
| `docs/` | Project report, data dictionary, setup notes, and progress documentation. |

## How process discovery works

Process mining needs an **event log**: a table with one row for each recorded
event in a patient journey. Each event needs:

| Field | Meaning | Example |
| --- | --- | --- |
| `patient_id` | Identifier that groups events into one journey | `P1` |
| `activity` | The care step that occurred | `Triage` |
| `timestamp` | When that step occurred | `2026-01-01 08:30:00` |

The discovery script reads `process_mining/event_log.csv`. If that file does
not exist, it creates a small example event log so the script can be run and
demonstrated. It then uses PM4Py to count directly-following activity pairs
and save:

- `process_mining/process_edges.csv` — transition counts, such as how often
  one activity directly follows another.
- `process_mining/process_map.png` — a visual process map.

The current script does **not** create an event log from `patients.csv`.
Preparing that event log from the project data is a separate data-preparation
step. See the project documentation for the planned event-log fields and
activity names.

## Run process discovery

You need Python and the `pandas` and `pm4py` packages. From the repository
root, install them with:

```bash
python -m pip install pandas pm4py
```

Run the discovery script from the repository root:

```bash
python process_mining/discovery.py
```

If you already have an event log, place it at
`process_mining/event_log.csv` with the required column names:
`patient_id`, `activity`, and `timestamp`. The script reads this file instead
of creating the example. Timestamps should be valid date/time values so
events can be sorted in the correct order.

The script writes its outputs inside `process_mining/`. The repository's
`.gitignore` excludes CSV files, so generated CSV outputs may not appear in
Git status.

## Dashboard and project documentation

The `dashboard/` directory describes a planned Power BI dashboard. The
documentation discusses an overview page, waiting-time analysis, a patient
process map, and findings/action pages. It also defines proposed KPIs such as
average waiting time, time between activities, loop-back percentage, and
non-compliant cases.

The Power BI report file is not included in this repository. Dashboard plans
and KPI definitions are documentation; they do not mean that every proposed
metric or dashboard page is currently implemented.

Useful project documents:

- [`docs/data_dictionary.md`](docs/data_dictionary.md) — dataset fields and
  known data-quality notes.
- [`docs/project_report.md`](docs/project_report.md) — project background,
  methods, and team roles.
- [`docs/documentation.md`](docs/documentation.md) — project summary.
- [`docs/setup_notes.md`](docs/setup_notes.md) — Power BI setup notes.
- [`docs/weekly_progress.md`](docs/weekly_progress.md) — progress notes.
- [`dashboard/dashboard_layout.md`](dashboard/dashboard_layout.md) — draft
  dashboard pages and data needs.
- [`dashboard/kpi_definitions.md`](dashboard/kpi_definitions.md) — KPI
  definitions and source fields.

## Project context and limitations

The project documentation describes `patients.csv` as a dataset with about
40,600 rows and 21 columns, including patient category, admission and
discharge dates, doctor, treatment cost, and waiting-time fields. It also
records missing values and duplicate rows that need consideration during data
preparation. Refer to the data dictionary for the documented details.

The available patient records contain dates rather than a complete sequence
of timestamped care activities. A process-mining event log must be prepared
before the real patient pathways can be analyzed. If event times are
simulated, resulting waiting-time metrics should be clearly identified as
simulated and not interpreted as observed hospital performance.

Before sharing data or findings:

- Remove or protect personal and identifying information.
- Confirm data quality and how missing or duplicate records are handled.
- Verify that timestamps and activity names reflect the intended process.
- Review pathway definitions and conclusions with appropriate project and
  clinical stakeholders.
- Treat results as descriptive analysis, not proof that a particular
  workflow change will improve care.

## Team workflow

The project report describes four areas of team contribution: data
generation, BigQuery/dbt data preparation, PM4Py process mining, and
dashboard/documentation. Team changes are developed on separate Git branches
and brought together through pull requests.

## License and data use

No license or permission to redistribute patient data is specified here.
Check the repository's data permissions and applicable privacy requirements
before reusing or sharing its datasets.
