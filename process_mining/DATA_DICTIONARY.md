# Process-mining output data dictionary

The descriptions below cover every CSV currently in `output/` and use the
files' actual headers. Types describe the values in those CSVs. A table visual
can show any of these fields; the visual column names a useful primary visual.

| File | Column name | Data type | Meaning in simple words | Power BI visual |
|---|---|---|---|---|
| `bottlenecks.csv` | `from_activity` | text | Activity before the transition. | Process flow |
| `bottlenecks.csv` | `to_activity` | text | Activity after the transition. | Process flow |
| `bottlenecks.csv` | `transition_count` | integer | Number of times this transition occurs. | Bar chart |
| `bottlenecks.csv` | `mean_waiting_time_hours` | number | Average wait between the two activities, in hours. | Bar chart |
| `bottlenecks.csv` | `median_waiting_time_hours` | number | Middle wait between the two activities, in hours. | Table |
| `bottlenecks.csv` | `max_waiting_time_hours` | number | Longest wait between the two activities, in hours. | Table |
| `bottlenecks.csv` | `p90_waiting_time_hours` | number | Wait at the 90th percentile, in hours. | Table |
| `bottlenecks.csv` | `bottleneck_rank` | integer | Rank of this transition by average wait. | Bar chart |
| `bottlenecks.csv` | `is_bottleneck` | boolean | Whether this transition is marked as a bottleneck. | KPI card |
| `bottlenecks.csv` | `avg_wait_minutes` | number | Average wait between activities, in minutes. | Bar chart |
| `bottlenecks.csv` | `median_wait_minutes` | number | Middle wait between activities, in minutes. | Table |
| `bottlenecks.csv` | `p90_wait_minutes` | number | Wait at the 90th percentile, in minutes. | Table |
| `bottlenecks.csv` | `max_wait_minutes` | number | Longest wait between activities, in minutes. | Table |
| `bottlenecks.csv` | `pct_of_all_transitions` | number | This transition's share of all transitions, as a percent. | Table |
| `bottlenecks.csv` | `loop_back_count` | integer | Number of loop-back transitions of this type. | Table |
| `bottlenecks.csv` | `loop_back_case_count` | integer | Cases containing this loop-back transition. | Table |
| `bottlenecks.csv` | `total_case_count` | integer | Total cases used for this transition's metrics. | KPI card |
| `bottlenecks.csv` | `pct_of_cases_affected` | number | Percent of cases affected by this transition. | KPI card |
| `bottlenecks.csv` | `is_loop_back` | boolean | Whether the transition returns to an earlier activity. | Process flow |
| `bottlenecks_sample.csv` | `from_activity` | text | Activity before the transition. | Process flow |
| `bottlenecks_sample.csv` | `to_activity` | text | Activity after the transition. | Process flow |
| `bottlenecks_sample.csv` | `avg_waiting_time_hours` | number | Average wait for this transition, in hours. | Bar chart |
| `bottlenecks_sample.csv` | `median_waiting_time_hours` | number | Middle wait for this transition, in hours. | Table |
| `bottlenecks_sample.csv` | `case_count` | integer | Cases that contain this transition. | Table |
| `bottlenecks_sample.csv` | `transition_count` | integer | Number of occurrences of this transition. | Bar chart |
| `bottleneck_transitions.csv` | `from_activity` | text | Activity before the transition. | Process flow |
| `bottleneck_transitions.csv` | `to_activity` | text | Activity after the transition. | Process flow |
| `bottleneck_transitions.csv` | `transition_count` | integer | Number of times this transition occurs. | Bar chart |
| `bottleneck_transitions.csv` | `avg_wait_minutes` | number | Average wait for this transition, in minutes. | Bar chart |
| `bottleneck_transitions.csv` | `median_wait_minutes` | number | Middle wait for this transition, in minutes. | Table |
| `bottleneck_transitions.csv` | `p90_wait_minutes` | number | Wait at the 90th percentile, in minutes. | Table |
| `bottleneck_transitions.csv` | `max_wait_minutes` | number | Longest wait for this transition, in minutes. | Table |
| `bottleneck_transitions.csv` | `bottleneck_rank` | integer | Rank of this transition by average wait. | Bar chart |
| `conformance_report_cases.csv` | `case_id` | text | Identifier for the patient case. | Table |
| `conformance_report_cases.csv` | `actual_path` | text | Activities recorded for the case, in order. | Table |
| `conformance_report_cases.csv` | `is_compliant` | boolean | Whether the case follows the required path. | KPI card |
| `conformance_report_cases.csv` | `deviation_type` | text | Main reason the case differs from the required path. | Bar chart |
| `conformance_report_cases.csv` | `missing_steps` | text | Required activities missing from the case. | Table |
| `conformance_report_cases.csv` | `extra_steps` | text | Unapproved activities found in the case. | Table |
| `conformance_report_summary.csv` | `total_cases` | integer | Number of cases checked. | KPI card |
| `conformance_report_summary.csv` | `compliant_cases` | integer | Number of cases that follow the required path. | KPI card |
| `conformance_report_summary.csv` | `non_compliant_cases` | integer | Number of cases that do not follow the required path. | KPI card |
| `conformance_report_summary.csv` | `pct_compliant` | number | Percent of cases that follow the required path. | KPI card |
| `conformance_report_summary.csv` | `pct_non_compliant` | number | Percent of cases that do not follow the required path. | KPI card |
| `conformance_report_summary.csv` | `compliant_count` | integer | Count of compliant cases. | KPI card |
| `conformance_report_summary.csv` | `skipped_step_count` | integer | Cases classified as missing a required step. | Bar chart |
| `conformance_report_summary.csv` | `extra_step_count` | integer | Cases classified as containing an extra step. | Bar chart |
| `conformance_report_summary.csv` | `loop_back_count` | integer | Cases classified as having a loop-back. | Bar chart |
| `conformance_report_summary.csv` | `wrong_order_count` | integer | Cases classified as having activities in the wrong order. | Bar chart |
| `conformance_results.csv` | `case_id` | text | Identifier for the patient case. | Table |
| `conformance_results.csv` | `fitness_score` | number | Token-replay fitness score for the case. | Table |
| `conformance_results.csv` | `is_compliant` | boolean | Whether the case follows the required path. | KPI card |
| `conformance_results.csv` | `deviation_type` | text | Type of difference from the required path. | Bar chart |
| `conformance_results.csv` | `trace_variant` | text | Ordered activity path for the case. | Process flow |
| `conformance_results.csv` | `duration_hours` | number | Elapsed time for the case, in hours. | Table |
| `discovery_summary.csv` | `cases` | integer | Number of patient cases in the event log. | KPI card |
| `discovery_summary.csv` | `events` | integer | Number of activity records in the event log. | KPI card |
| `discovery_summary.csv` | `activities` | integer | Number of distinct activities in the event log. | KPI card |
| `discovery_summary.csv` | `variants` | integer | Number of distinct activity paths. | KPI card |
| `discovery_summary.csv` | `average_case_duration_hours` | number | Average elapsed time per case, in hours. | KPI card |
| `discovery_summary.csv` | `max_case_duration_hours` | number | Longest elapsed time for a case, in hours. | KPI card |
| `loopbacks.csv` | `from_activity` | text | Activity before the loop-back. | Process flow |
| `loopbacks.csv` | `to_activity` | text | Activity reached by the loop-back. | Process flow |
| `loopbacks.csv` | `loopback_count` | integer | Number of times the loop-back occurs. | Bar chart |
| `loopbacks.csv` | `cases_affected` | integer | Number of cases with this loop-back. | Table |
| `loopbacks.csv` | `percent_cases_affected` | number | Percent of cases with this loop-back. | KPI card |
| `top_variants.csv` | `rank` | integer | Rank of the activity path by case count. | Bar chart |
| `top_variants.csv` | `variant` | text | Ordered activity path. | Process flow |
| `top_variants.csv` | `case_count` | integer | Number of cases with this path. | Bar chart |
| `top_variants.csv` | `percentage` | number | Percent of cases with this path. | Table |
| `charts/kpi_summary.csv` | `total_cases` | integer | Number of cases in the chart input. | KPI card |
| `charts/kpi_summary.csv` | `total_events` | integer | Number of events in the chart input. | KPI card |
| `charts/kpi_summary.csv` | `total_activities` | integer | Number of distinct activities. | KPI card |
| `charts/kpi_summary.csv` | `avg_stay_minutes` | number | Average case duration, in minutes. | KPI card |
| `charts/kpi_summary.csv` | `max_stay_minutes` | number | Longest case duration, in minutes. | KPI card |
| `charts/kpi_summary.csv` | `pct_cases_with_loopback` | number | Percent of cases with a loop-back. | KPI card |
| `charts/kpi_summary.csv` | `top_bottleneck` | text | Transition with the highest average wait. | KPI card |
| `charts/kpi_summary.csv` | `top_bottleneck_avg_wait` | number | Average wait for the top bottleneck, in minutes. | KPI card |
| `charts/variant_table.csv` | `path_variant` | text | Ordered activity path. | Process flow |
| `charts/variant_table.csv` | `case_count` | integer | Number of cases with this path. | Bar chart |
| `charts/variant_table.csv` | `pct_of_cases` | number | Percent of cases with this path. | Table |
| `charts/variant_table.csv` | `variant_id` | text | Label assigned to the path. | Table |
| `powerbi/case_summary.csv` | `case_id` | text | Identifier for the patient case. | Table |
| `powerbi/case_summary.csv` | `start_time` | datetime (UTC) | Time of the case's first event. | Table |
| `powerbi/case_summary.csv` | `end_time` | datetime (UTC) | Time of the case's last event. | Table |
| `powerbi/case_summary.csv` | `total_duration_minutes` | number | Elapsed time for the case, in minutes. | Table |
| `powerbi/case_summary.csv` | `num_events` | integer | Number of events in the case. | Table |
| `powerbi/case_summary.csv` | `has_loopback` | boolean | Whether the case contains a loop-back. | KPI card |
| `powerbi/case_summary.csv` | `path_variant` | text | Ordered activity path for the case. | Process flow |
| `powerbi/hourly_arrivals.csv` | `hour_of_day` | integer | Hour when cases arrive, from the event data. | Bar chart |
| `powerbi/hourly_arrivals.csv` | `case_count` | integer | Cases arriving in that hour. | Bar chart |
| `powerbi/hourly_arrivals.csv` | `avg_case_duration_minutes` | number | Average case duration for that arrival hour. | Table |
| `powerbi/kpi_summary.csv` | `total_cases` | integer | Number of cases in the event log. | KPI card |
| `powerbi/kpi_summary.csv` | `total_events` | integer | Number of events in the event log. | KPI card |
| `powerbi/kpi_summary.csv` | `avg_case_duration_minutes` | number | Average case duration, in minutes. | KPI card |
| `powerbi/kpi_summary.csv` | `median_case_duration_minutes` | number | Middle case duration, in minutes. | KPI card |
| `powerbi/kpi_summary.csv` | `pct_cases_with_loopback` | number | Percent of cases with a loop-back. | KPI card |
| `powerbi/kpi_summary.csv` | `top_bottleneck_transition` | text | Transition with the highest average wait. | KPI card |
| `powerbi/kpi_summary.csv` | `top_bottleneck_avg_wait_minutes` | number | Average wait for the top bottleneck, in minutes. | KPI card |
| `powerbi/process_map_edges.csv` | `from_activity` | text | Activity before the transition. | Process flow |
| `powerbi/process_map_edges.csv` | `to_activity` | text | Activity after the transition. | Process flow |
| `powerbi/process_map_edges.csv` | `case_count` | integer | Cases containing the transition. | Process flow |
| `powerbi/process_map_edges.csv` | `avg_wait_minutes` | number | Average wait for the transition, in minutes. | Process flow |
| `powerbi/process_map_nodes.csv` | `activity` | text | Name of the activity. | Process flow |
| `powerbi/process_map_nodes.csv` | `event_count` | integer | Number of events for the activity. | Bar chart |
| `powerbi/process_map_nodes.csv` | `case_count` | integer | Cases containing the activity. | Bar chart |
| `powerbi/process_map_nodes.csv` | `avg_time_in_step_minutes` | number | Average time attributed to the activity, in minutes. | Table |
| `powerbi/variant_summary.csv` | `path_variant` | text | Ordered activity path. | Process flow |
| `powerbi/variant_summary.csv` | `case_count` | integer | Number of cases with this path. | Bar chart |
| `powerbi/variant_summary.csv` | `pct_of_cases` | number | Percent of cases with this path. | Table |
| `powerbi/variant_summary.csv` | `avg_duration_minutes` | number | Average duration for this path, in minutes. | Table |

## Event log format

Each event-log row records one activity for one case. `Case_ID` identifies the
patient journey (called `case_id` in the checked-in sample CSV).
`Activity_Name` is the recorded step (called `activity` in the sample).
`Timestamp` is when that step occurred (called `timestamp` in the sample);
timestamps determine the order of events within a case.
