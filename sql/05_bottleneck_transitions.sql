-- Week 3: transition waiting-time metrics and activity loop-backs.
-- The repository does not include a dbt project or configured BigQuery table.
-- Keep this table path aligned with the other SQL scripts and replace it with
-- the deployed event-log table when running against BigQuery.

ASSERT (
  SELECT COUNTIF(
    Case_ID IS NULL
    OR TRIM(CAST(Case_ID AS STRING)) = ''
    OR Activity_Name IS NULL
    OR TRIM(CAST(Activity_Name AS STRING)) = ''
    OR Timestamp IS NULL
  ) = 0
  FROM `project.dataset.event_log`
) AS 'Case_ID, Activity_Name, and Timestamp must be populated';

ASSERT (
  SELECT COUNTIF(
    next_timestamp IS NOT NULL
    AND TIMESTAMP_DIFF(next_timestamp, event_timestamp, MICROSECOND) < 0
  ) = 0
  FROM (
    SELECT
      Timestamp AS event_timestamp,
      LEAD(Timestamp) OVER (
        PARTITION BY Case_ID
        ORDER BY Timestamp
      ) AS next_timestamp
    FROM `project.dataset.event_log`
  )
) AS 'Consecutive event timestamps must not move backwards';

-- Query 1: one row per directly-follows activity pair.
WITH ordered_events AS (
  -- Normalize the model columns and find the next event inside each case.
  SELECT
    CAST(TRIM(CAST(Case_ID AS STRING)) AS STRING) AS case_id,
    TRIM(CAST(Activity_Name AS STRING)) AS activity_name,
    Timestamp AS event_timestamp,
    LEAD(Activity_Name) OVER (
      PARTITION BY Case_ID
      ORDER BY Timestamp
    ) AS next_activity_name,
    LEAD(Timestamp) OVER (
      PARTITION BY Case_ID
      ORDER BY Timestamp
    ) AS next_timestamp
  FROM `project.dataset.event_log`
),
transitions AS (
  -- Exclude each case's final event and negative elapsed times.
  SELECT
    activity_name AS from_activity,
    TRIM(CAST(next_activity_name AS STRING)) AS to_activity,
    TIMESTAMP_DIFF(next_timestamp, event_timestamp, MICROSECOND)
      / 60000000.0 AS wait_minutes
  FROM ordered_events
  WHERE next_activity_name IS NOT NULL
    AND TIMESTAMP_DIFF(next_timestamp, event_timestamp, MICROSECOND) >= 0
),
pair_aggregates AS (
  -- Calculate additive metrics for each observed transition.
  SELECT
    from_activity,
    to_activity,
    COUNT(*) AS transition_count,
    AVG(wait_minutes) AS avg_wait_minutes,
    MAX(wait_minutes) AS max_wait_minutes
  FROM transitions
  GROUP BY from_activity, to_activity
),
pair_percentiles AS (
  -- Calculate the continuous median and 90th percentile for each pair.
  SELECT DISTINCT
    from_activity,
    to_activity,
    PERCENTILE_CONT(wait_minutes, 0.5) OVER (
      PARTITION BY from_activity, to_activity
    ) AS median_wait_minutes,
    PERCENTILE_CONT(wait_minutes, 0.9) OVER (
      PARTITION BY from_activity, to_activity
    ) AS p90_wait_minutes
  FROM transitions
),
pair_metrics AS (
  -- Add each pair's share of all valid consecutive transitions.
  SELECT
    aggregates.from_activity,
    aggregates.to_activity,
    aggregates.transition_count,
    aggregates.avg_wait_minutes,
    percentiles.median_wait_minutes,
    percentiles.p90_wait_minutes,
    aggregates.max_wait_minutes,
    100.0 * aggregates.transition_count
      / SUM(aggregates.transition_count) OVER () AS pct_of_all_transitions
  FROM pair_aggregates AS aggregates
  JOIN pair_percentiles AS percentiles
    USING (from_activity, to_activity)
)
SELECT
  from_activity,
  to_activity,
  transition_count,
  avg_wait_minutes,
  median_wait_minutes,
  p90_wait_minutes,
  max_wait_minutes,
  pct_of_all_transitions
FROM pair_metrics
ORDER BY avg_wait_minutes DESC, transition_count DESC, from_activity, to_activity;

-- Query 2: count returns to any activity previously seen in the same case.
ASSERT (
  SELECT COUNTIF(
    Case_ID IS NULL
    OR TRIM(CAST(Case_ID AS STRING)) = ''
    OR Activity_Name IS NULL
    OR TRIM(CAST(Activity_Name AS STRING)) = ''
    OR Timestamp IS NULL
  ) = 0
  FROM `project.dataset.event_log`
) AS 'Case_ID, Activity_Name, and Timestamp must be populated';

WITH ordered_events AS (
  -- Number events in case order and attach each event's immediate successor.
  SELECT
    CAST(TRIM(CAST(Case_ID AS STRING)) AS STRING) AS case_id,
    TRIM(CAST(Activity_Name AS STRING)) AS activity_name,
    Timestamp AS event_timestamp,
    ROW_NUMBER() OVER (
      PARTITION BY Case_ID
      ORDER BY Timestamp
    ) AS event_number,
    LEAD(Activity_Name) OVER (
      PARTITION BY Case_ID
      ORDER BY Timestamp
    ) AS next_activity_name,
    LEAD(Timestamp) OVER (
      PARTITION BY Case_ID
      ORDER BY Timestamp
    ) AS next_timestamp
  FROM `project.dataset.event_log`
),
transitions AS (
  -- Keep consecutive events with nonnegative durations.
  SELECT
    case_id,
    event_number,
    activity_name AS from_activity,
    TRIM(CAST(next_activity_name AS STRING)) AS to_activity
  FROM ordered_events
  WHERE next_activity_name IS NOT NULL
    AND TIMESTAMP_DIFF(next_timestamp, event_timestamp, MICROSECOND) >= 0
),
loop_back_transitions AS (
  -- A transition loops back when its destination occurred earlier in its case.
  SELECT DISTINCT
    transition.case_id,
    transition.event_number,
    transition.from_activity,
    transition.to_activity
  FROM transitions AS transition
  JOIN ordered_events AS previous_event
    ON previous_event.case_id = transition.case_id
    AND previous_event.event_number < transition.event_number
    AND previous_event.activity_name = transition.to_activity
),
loop_back_counts AS (
  -- Count loop-back transitions and distinct affected cases per activity pair.
  SELECT
    from_activity,
    to_activity,
    COUNT(*) AS transition_count,
    COUNT(DISTINCT case_id) AS case_count
  FROM loop_back_transitions
  GROUP BY from_activity, to_activity
),
case_population AS (
  -- Use every case in the input log as the denominator for affected-case %.
  SELECT COUNT(DISTINCT Case_ID) AS total_case_count
  FROM `project.dataset.event_log`
)
SELECT
  loop_backs.from_activity,
  loop_backs.to_activity,
  loop_backs.transition_count,
  loop_backs.case_count,
  population.total_case_count,
  100.0 * loop_backs.case_count / population.total_case_count
    AS pct_of_cases_affected
FROM loop_back_counts AS loop_backs
CROSS JOIN case_population AS population
ORDER BY loop_backs.transition_count DESC, loop_backs.case_count DESC,
  loop_backs.from_activity, loop_backs.to_activity;
