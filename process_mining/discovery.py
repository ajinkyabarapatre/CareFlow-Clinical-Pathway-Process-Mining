import os
import pandas as pd
import pm4py

LOG_PATH = "process_mining/event_log.csv"

# If you don't have the real data yet, make a small sample so you can test
if not os.path.exists(LOG_PATH):
    paths = {
        "P1": ["Registration", "Triage", "Consultation", "Lab Test", "Discharge"],
        "P2": ["Registration", "Triage", "Consultation", "Discharge"],
        "P3": ["Registration", "Triage", "Consultation", "Lab Test", "Consultation", "Discharge"],
        "P4": ["Registration", "Triage", "Consultation", "Lab Test", "Discharge"],
    }
    rows = []
    for patient, acts in paths.items():
        t = pd.Timestamp("2026-01-01 08:00")
        for a in acts:
            rows.append({"patient_id": patient, "activity": a, "timestamp": t})
            t += pd.Timedelta(minutes=30)
    pd.DataFrame(rows).to_csv(LOG_PATH, index=False)
    print("Sample event_log.csv created (replace it with the real data later)")

# 1. Load the data
df = pd.read_csv(LOG_PATH)

# 2. Rename columns to what PM4Py expects (change the left side to match your real CSV)
df = df.rename(columns={
    "patient_id": "case:concept:name",
    "activity": "concept:name",
    "timestamp": "time:timestamp",
})
df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
df = pm4py.format_dataframe(df)

# 3. Discover the process
dfg, start_acts, end_acts = pm4py.discover_dfg(df)

# 4. Save the table of steps and how often they happen
edges = pd.DataFrame(
    [(a, b, n) for (a, b), n in dfg.items()],
    columns=["from_activity", "to_activity", "count"],
).sort_values("count", ascending=False)
edges.to_csv("process_mining/process_edges.csv", index=False)

# 5. Save the picture
pm4py.save_vis_dfg(dfg, start_acts, end_acts, "process_mining/process_map.png")
print("Done! Check process_mining/process_map.png")