-- Rank the ten slowest activity transitions by average waiting time.
-- Replace the table path with the BigQuery event-log table.
-- Equal timestamps are ordered by activity; their waiting time is zero.
-- NULL or blank required values fail the assertion rather than being skipped.
ASSERT (
  SELECT COUNTIF(
    case_id IS NULL
    OR TRIM(CAST(case_id AS STRING)) = ''
    OR activity IS NULL
    OR TRIM(CAST(activity AS STRING)) = ''
    OR timestamp IS NULL
  ) = 0
  FROM `project.dataset.event_log`
) AS 'case_id, activity, and timestamp must be populated';

WITH ordered_events AS (
  SELECT
    CAST(case_id AS STRING) AS case_id,
    TRIM(CAST(activity AS STRING)) AS activity,
    timestamp AS event_timestamp,
    LEAD(TRIM(CAST(activity AS STRING))) OVER (
      PARTITION BY case_id
      ORDER BY timestamp, TRIM(CAST(activity AS STRING))
    ) AS next_activity,
    LEAD(timestamp) OVER (
      PARTITION BY case_id
      ORDER BY timestamp, TRIM(CAST(activity AS STRING))
    ) AS next_timestamp
  FROM `project.dataset.event_log`
),
transitions AS (
  SELECT
    case_id,
    activity AS from_activity,
    next_activity AS to_activity,
    TIMESTAMP_DIFF(next_timestamp, event_timestamp, MICROSECOND)
      / 3600000000.0 AS waiting_time_hours
  FROM ordered_events
  WHERE next_activity IS NOT NULL
),
aggregates AS (
  SELECT
    from_activity,
    to_activity,
    AVG(waiting_time_hours) AS avg_waiting_time_hours,
    MAX(waiting_time_hours) AS max_waiting_time_hours,
    COUNT(DISTINCT case_id) AS case_count,
    COUNT(*) AS transition_count
  FROM transitions
  GROUP BY from_activity, to_activity
),
medians AS (
  SELECT DISTINCT
    from_activity,
    to_activity,
    PERCENTILE_CONT(waiting_time_hours, 0.5) OVER (
      PARTITION BY from_activity, to_activity
    ) AS median_waiting_time_hours
  FROM transitions
),
ranked AS (
  SELECT
    aggregates.*,
    medians.median_waiting_time_hours,
    ROW_NUMBER() OVER (
      ORDER BY
        aggregates.avg_waiting_time_hours DESC,
        medians.median_waiting_time_hours DESC,
        aggregates.max_waiting_time_hours DESC,
        aggregates.from_activity,
        aggregates.to_activity
    ) AS bottleneck_rank
  FROM aggregates
  JOIN medians USING (from_activity, to_activity)
)
SELECT
  bottleneck_rank,
  from_activity,
  to_activity,
  ROUND(avg_waiting_time_hours, 3) AS avg_waiting_time_hours,
  ROUND(median_waiting_time_hours, 3) AS median_waiting_time_hours,
  ROUND(max_waiting_time_hours, 3) AS max_waiting_time_hours,
  case_count,
  transition_count
FROM ranked
WHERE bottleneck_rank <= 10
ORDER BY bottleneck_rank;

-- Python also emits department and patient_group breakdowns when present.
-- To get an equivalent SQL breakdown, carry the source-event dimension through
-- ordered_events and add it to the GROUP BY/PERCENTILE_CONT partitions.
