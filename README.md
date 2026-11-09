# CareFlow: Clinical Pathway Process Mining

CareFlow explores how patients move through hospital care and where delays
may happen. The project uses patient data, process mining, and dashboard
planning to make patient journeys easier to understand.

## Project contents

- `patients.csv` and `doctors.csv`: project datasets.
- `data.ipynb`: Jupyter notebook for exploring the data.
- `process_mining/discovery.py`: uses PM4Py to discover a process map and
  save a table of transitions.
- `dashboard/` and `docs/`: dashboard plans, KPI definitions, and project
  documentation.

## Run process discovery

Install Python dependencies:

```bash
python -m pip install pandas pm4py
```

From the project root, run:

```bash
python process_mining/discovery.py
```

If `process_mining/event_log.csv` is not present, the script creates a small
example event log so the discovery step can be tried. It then saves
`process_mining/process_map.png` and `process_mining/process_edges.csv`.

The event log needs columns for patient ID, activity, and timestamp. The
script expects them to be named `patient_id`, `activity`, and `timestamp`.
The discovery script does not currently convert `patients.csv` into an event
log.

## Dashboard

The `dashboard/` folder documents the planned Power BI pages and KPIs. The
Power BI report itself is not included in this repository.

## Important note

This project is for learning and workflow analysis. Process maps and
waiting-time results depend on the input data and should not be treated as
clinical advice or used to make patient-care decisions.
