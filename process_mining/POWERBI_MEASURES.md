# Power BI measures

Import the three `vw_` views from BigQuery. Use the existing `pm_case_summary`
table for case counts and its `has_loopback` flag.

```DAX
Total Cases = DISTINCTCOUNT('pm_case_summary'[case_id])
Avg Wait Minutes = AVERAGE('vw_transition_times'[wait_minutes])
Max Wait Minutes = MAX('vw_transition_times'[wait_minutes])
% Cases With Loopback =
    DIVIDE(CALCULATE(DISTINCTCOUNT('pm_case_summary'[case_id]),
        'pm_case_summary'[has_loopback] = TRUE()), [Total Cases], 0)

Top Bottleneck =
VAR SlowestTransition =
    TOPN(1, 'vw_bottleneck_summary',
        'vw_bottleneck_summary'[avg_wait_minutes], DESC,
        'vw_bottleneck_summary'[from_activity], ASC,
        'vw_bottleneck_summary'[to_activity], ASC)
RETURN
    CONCATENATEX(SlowestTransition,
        'vw_bottleneck_summary'[from_activity] & " -> "
            & 'vw_bottleneck_summary'[to_activity])
```

## Recommended visuals

- KPI cards for Total Cases, Avg Wait Minutes, Max Wait Minutes, and loopbacks.
- Bar chart of the top 10 transitions by `avg_wait_minutes`.
- Process flow visual using `from_activity` and `to_activity`.
