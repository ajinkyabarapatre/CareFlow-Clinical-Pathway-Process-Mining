-- Calculate comparable directly-follows waiting-time metrics for every pair.
-- Replace the example table path with the BigQuery event-log table.
-- Output column names and order match bottleneck_analysis.py's CSV contract.
-- Ties use activity text for deterministic ordering because no event ID is required.
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
    CAST(TRIM(CAST(case_id AS STRING)) AS STRING) AS case_id,
    TRIM(CAST(activity AS STRING)) AS activity,
    timestamp AS event_timestamp,
    LEAD(TRIM(CAST(activity AS STRING))) OVER (
      PARTITION BY CAST(TRIM(CAST(case_id AS STRING)) AS STRING)
      ORDER BY timestamp, TRIM(CAST(activity AS STRING))
    ) AS next_activity,
    LEAD(timestamp) OVER (
      PARTITION BY CAST(TRIM(CAST(case_id AS STRING)) AS STRING)
      ORDER BY timestamp, TRIM(CAST(activity AS STRING))
    ) AS next_timestamp
  FROM `project.dataset.event_log`
),
transitions AS (
  SELECT
    activity AS from_activity,
    next_activity AS to_activity,
    TIMESTAMP_DIFF(next_timestamp, event_timestamp, MICROSECOND)
      / 3600000000.0 AS waiting_time_hours
  FROM ordered_events
  WHERE next_activity IS NOT NULL
),
pair_metrics AS (
  SELECT
    from_activity,
    to_activity,
    COUNT(*) AS transition_count,
    AVG(waiting_time_hours) AS mean_waiting_time_hours,
    MAX(waiting_time_hours) AS max_waiting_time_hours
  FROM transitions
  GROUP BY from_activity, to_activity
),
pair_percentiles AS (
  SELECT DISTINCT
    from_activity,
    to_activity,
    PERCENTILE_CONT(waiting_time_hours, 0.5) OVER (
      PARTITION BY from_activity, to_activity
    ) AS median_waiting_time_hours,
    PERCENTILE_CONT(waiting_time_hours, 0.9) OVER (
      PARTITION BY from_activity, to_activity
    ) AS p90_waiting_time_hours
  FROM transitions
),
ranked_metrics AS (
  SELECT
    pair_metrics.from_activity,
    pair_metrics.to_activity,
    pair_metrics.transition_count,
    pair_metrics.mean_waiting_time_hours,
    pair_percentiles.median_waiting_time_hours,
    pair_metrics.max_waiting_time_hours,
    pair_percentiles.p90_waiting_time_hours,
    ROW_NUMBER() OVER (
      ORDER BY
        pair_metrics.mean_waiting_time_hours DESC,
        pair_metrics.from_activity,
        pair_metrics.to_activity
    ) AS bottleneck_rank
  FROM pair_metrics
  JOIN pair_percentiles USING (from_activity, to_activity)
)
SELECT
  from_activity,
  to_activity,
  transition_count,
  mean_waiting_time_hours,
  median_waiting_time_hours,
  max_waiting_time_hours,
  p90_waiting_time_hours,
  bottleneck_rank,
  bottleneck_rank <= 3 AS is_bottleneck
FROM ranked_metrics
ORDER BY bottleneck_rank;
