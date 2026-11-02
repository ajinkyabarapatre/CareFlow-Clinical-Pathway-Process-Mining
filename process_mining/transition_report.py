"""
transition_report.py
Week 3 - Member 3: Bottleneck Calculations (simple pandas version)

What it does:
1. Reads the hospital event log (Case_ID, Activity_Name, Timestamp)
2. Finds the waiting time between each step and the next step
3. Ranks the slowest transitions (bottlenecks)
4. Finds loop-backs (patient returns to a step already done)
5. Calculates how long each patient stayed in total
6. Saves the results as CSV files for Power BI

Run:  python process_mining/transition_report.py
"""

import os
import pandas as pd

# ---------- Settings (change here if your column names differ) ----------
INPUT_FILE = os.path.join("process_mining", "sample_event_log.csv")
OUTPUT_DIR = os.path.join("process_mining", "output")
CASE_COL = "Case_ID"
ACTIVITY_COL = "Activity_Name"
TIME_COL = "Timestamp"
TOP_N = 10


def load_event_log(path):
    """Read the CSV, convert time to datetime, sort by patient and time."""
    df = pd.read_csv(path)
    df[TIME_COL] = pd.to_datetime(df[TIME_COL])
    df = df.sort_values([CASE_COL, TIME_COL]).reset_index(drop=True)
    return df


def build_transitions(df):
    """Make one row for every move from one step to the next step
    of the same patient, with the waiting time in minutes."""
    df = df.copy()

    # shift(-1) looks at the next row inside the same patient
    df["next_activity"] = df.groupby(CASE_COL)[ACTIVITY_COL].shift(-1)
    df["next_time"] = df.groupby(CASE_COL)[TIME_COL].shift(-1)

    # the last event of each patient has no next step, so remove it
    transitions = df.dropna(subset=["next_activity"]).copy()

    # waiting time in minutes
    seconds = (transitions["next_time"] - transitions[TIME_COL]).dt.total_seconds()
    transitions["wait_minutes"] = seconds / 60

    # remove wrong data (negative time)
    transitions = transitions[transitions["wait_minutes"] >= 0]

    transitions = transitions.rename(
        columns={ACTIVITY_COL: "from_activity", "next_activity": "to_activity"}
    )
    return transitions[[CASE_COL, "from_activity", "to_activity", "wait_minutes"]]


def summarize_transitions(transitions):
    """Average, median, 90th percentile and max wait for each step pair."""
    keys = ["from_activity", "to_activity"]

    summary = (
        transitions.groupby(keys)["wait_minutes"]
        .agg(
            transition_count="count",
            avg_wait_minutes="mean",
            median_wait_minutes="median",
            max_wait_minutes="max",
        )
        .reset_index()
    )

    p90 = (
        transitions.groupby(keys)["wait_minutes"]
        .quantile(0.9)
        .reset_index(name="p90_wait_minutes")
    )
    summary = summary.merge(p90, on=keys)

    # share of each transition out of all transitions
    total = summary["transition_count"].sum()
    summary["pct_of_all_transitions"] = summary["transition_count"] / total * 100

    summary = summary.round(2)
    # slowest first
    summary = summary.sort_values("avg_wait_minutes", ascending=False)
    return summary.reset_index(drop=True)


def find_loopbacks(df):
    """Find patients who go back to a step they already did,
    for example X-Ray -> Triage."""
    rows = []
    total_cases = df[CASE_COL].nunique()

    for case_id, group in df.groupby(CASE_COL):
        seen = set()
        previous = None
        for activity in group[ACTIVITY_COL]:
            # already seen before, and not just a repeated same step
            if activity in seen and previous is not None and activity != previous:
                rows.append(
                    {
                        CASE_COL: case_id,
                        "from_activity": previous,
                        "to_activity": activity,
                    }
                )
            seen.add(activity)
            previous = activity

    columns = ["from_activity", "to_activity", "loopback_count", "pct_of_cases"]
    if not rows:
        return pd.DataFrame(columns=columns)

    loops = pd.DataFrame(rows)
    result = (
        loops.groupby(["from_activity", "to_activity"])
        .agg(loopback_count=(CASE_COL, "count"), cases_affected=(CASE_COL, "nunique"))
        .reset_index()
    )
    result["pct_of_cases"] = (result["cases_affected"] / total_cases * 100).round(2)
    result = result.drop(columns="cases_affected")
    return result.sort_values("loopback_count", ascending=False).reset_index(drop=True)


def case_durations(df):
    """Total time each patient spent from first to last event."""
    result = (
        df.groupby(CASE_COL)
        .agg(
            start_time=(TIME_COL, "min"),
            end_time=(TIME_COL, "max"),
            num_events=(ACTIVITY_COL, "count"),
        )
        .reset_index()
    )
    seconds = (result["end_time"] - result["start_time"]).dt.total_seconds()
    result["total_duration_minutes"] = (seconds / 60).round(2)
    return result


def sanity_check(df, transitions):
    """Total transitions should be total events minus number of patients."""
    expected = len(df) - df[CASE_COL].nunique()
    actual = len(transitions)
    if expected == actual:
        print(f"Check OK: {actual} transitions = {len(df)} events - {df[CASE_COL].nunique()} cases")
    else:
        print(f"Warning: expected {expected} transitions but found {actual}")


def main():
    df = load_event_log(INPUT_FILE)
    print(f"Loaded {len(df)} events for {df[CASE_COL].nunique()} cases\n")

    transitions = build_transitions(df)
    sanity_check(df, transitions)

    summary = summarize_transitions(transitions)
    loopbacks = find_loopbacks(df)
    durations = case_durations(df)

    print(f"\nTop {TOP_N} bottlenecks (slowest average wait):")
    print(summary.head(TOP_N).to_string(index=False))

    print("\nLoop-backs:")
    if loopbacks.empty:
        print("No loop-backs found")
    else:
        print(loopbacks.to_string(index=False))

    print(f"\nAverage patient stay: {durations['total_duration_minutes'].mean():.2f} minutes")

    # save CSV files for Power BI
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    summary.to_csv(os.path.join(OUTPUT_DIR, "transition_summary.csv"), index=False)
    loopbacks.to_csv(os.path.join(OUTPUT_DIR, "loopback_summary.csv"), index=False)
    durations.to_csv(os.path.join(OUTPUT_DIR, "case_durations.csv"), index=False)
    print(f"\nSaved 3 CSV files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()