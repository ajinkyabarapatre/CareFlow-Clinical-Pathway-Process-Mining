-- View: one row for each valid, consecutive activity transition.
CREATE OR REPLACE VIEW `project.dataset.vw_transition_times` AS
WITH ordered_events AS (
  -- Find the next activity and timestamp in each case.
  SELECT
    Case_ID,
    TRIM(CAST(Activity_Name AS STRING)) AS from_activity,
    Timestamp AS event_timestamp,
    LEAD(Activity_Name) OVER (PARTITION BY Case_ID ORDER BY Timestamp) AS to_activity,
    LEAD(Timestamp) OVER (PARTITION BY Case_ID ORDER BY Timestamp) AS next_timestamp
  FROM `project.dataset.event_log`
),
transitions AS (
  -- Drop each case's last event and any negative wait.
  SELECT
    CAST(TRIM(CAST(Case_ID AS STRING)) AS STRING) AS case_id,
    from_activity,
    TRIM(CAST(to_activity AS STRING)) AS to_activity,
    TIMESTAMP_DIFF(next_timestamp, event_timestamp, MICROSECOND) / 60000000.0 AS wait_minutes
  FROM ordered_events
  WHERE to_activity IS NOT NULL
    AND TIMESTAMP_DIFF(next_timestamp, event_timestamp, MICROSECOND) >= 0
)
SELECT case_id, from_activity, to_activity, wait_minutes
FROM transitions;

-- View: summarize waits and rank each observed transition by average wait.
CREATE OR REPLACE VIEW `project.dataset.vw_bottleneck_summary` AS
WITH pair_metrics AS (
  -- Calculate counts, wait percentiles, and rank for each transition.
  SELECT
    from_activity,
    to_activity,
    COUNT(*) AS transition_count,
    AVG(wait_minutes) AS avg_wait_minutes,
    APPROX_QUANTILES(wait_minutes, 100)[OFFSET(50)] AS median_wait_minutes,
    APPROX_QUANTILES(wait_minutes, 100)[OFFSET(90)] AS p90_wait_minutes,
    MAX(wait_minutes) AS max_wait_minutes,
    ROW_NUMBER() OVER (ORDER BY AVG(wait_minutes) DESC, from_activity, to_activity) AS bottleneck_rank
  FROM `project.dataset.vw_transition_times`
  GROUP BY from_activity, to_activity
)
SELECT * FROM pair_metrics;

-- View: count transitions that return to an activity already seen in the case.
CREATE OR REPLACE VIEW `project.dataset.vw_loopbacks` AS
WITH ordered_events AS (
  -- Find each next activity and list activities already reached in the case.
  SELECT
    Case_ID,
    Activity_Name,
    Timestamp AS event_timestamp,
    LEAD(Activity_Name) OVER (PARTITION BY Case_ID ORDER BY Timestamp) AS next_activity_name,
    LEAD(Timestamp) OVER (PARTITION BY Case_ID ORDER BY Timestamp) AS next_timestamp,
    ARRAY_AGG(Activity_Name) OVER (
      PARTITION BY Case_ID ORDER BY Timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS seen_activities
  FROM `project.dataset.event_log`
),
loopback_transitions AS (
  -- Keep valid transitions whose destination appeared earlier in the case.
  SELECT
    transition.Case_ID,
    TRIM(CAST(transition.Activity_Name AS STRING)) AS from_activity,
    TRIM(CAST(transition.next_activity_name AS STRING)) AS to_activity
  FROM ordered_events AS transition
  WHERE transition.next_activity_name IS NOT NULL
    AND TIMESTAMP_DIFF(transition.next_timestamp, transition.event_timestamp, MICROSECOND) >= 0
    AND transition.next_activity_name IN UNNEST(transition.seen_activities)
),
loopback_counts AS (
  -- Count loop-back transitions and distinct cases for each activity pair.
  SELECT
    from_activity,
    to_activity,
    COUNT(*) AS loopback_count,
    COUNT(DISTINCT Case_ID) AS cases_affected
  FROM loopback_transitions
  GROUP BY from_activity, to_activity
),
case_population AS (
  -- Count all cases so each pair's affected-case percentage has a denominator.
  SELECT COUNT(DISTINCT Case_ID) AS total_case_count
  FROM `project.dataset.event_log`
)
SELECT
  loopbacks.from_activity,
  loopbacks.to_activity,
  loopbacks.loopback_count,
  loopbacks.cases_affected,
  population.total_case_count,
  SAFE_DIVIDE(100.0 * loopbacks.cases_affected, population.total_case_count) AS percent_cases_affected
FROM loopback_counts AS loopbacks
CROSS JOIN case_population AS population;
