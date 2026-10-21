-- Summarize exact compliance and rank common deviation types.
-- Replace the example table path with the BigQuery event-log table.
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

WITH case_traces AS (
  SELECT
    CAST(TRIM(CAST(case_id AS STRING)) AS STRING) AS case_id,
    ARRAY_AGG(
      TRIM(CAST(activity AS STRING))
      ORDER BY timestamp, TRIM(CAST(activity AS STRING))
    ) AS activities
  FROM `project.dataset.event_log`
  GROUP BY case_id
),
case_flags AS (
  SELECT
    case_id,
    ARRAY_LENGTH(activities) = 5
      AND activities[SAFE_OFFSET(0)] = 'Admission'
      AND activities[SAFE_OFFSET(1)] = 'Triage'
      AND activities[SAFE_OFFSET(2)] = 'Diagnosis'
      AND activities[SAFE_OFFSET(3)] = 'Treatment'
      AND activities[SAFE_OFFSET(4)] = 'Discharge' AS is_exact_path,
    'Admission' NOT IN UNNEST(activities)
      OR 'Triage' NOT IN UNNEST(activities)
      OR 'Diagnosis' NOT IN UNNEST(activities)
      OR 'Treatment' NOT IN UNNEST(activities)
      OR 'Discharge' NOT IN UNNEST(activities) AS has_skipped,
    (SELECT COUNTIF(activity = 'Admission') FROM UNNEST(activities) AS activity) > 1
      OR (SELECT COUNTIF(activity = 'Triage') FROM UNNEST(activities) AS activity) > 1
      OR (SELECT COUNTIF(activity = 'Diagnosis') FROM UNNEST(activities) AS activity) > 1
      OR (SELECT COUNTIF(activity = 'Treatment') FROM UNNEST(activities) AS activity) > 1
      OR (SELECT COUNTIF(activity = 'Discharge') FROM UNNEST(activities) AS activity) > 1
      AS has_repeated,
    EXISTS (
      SELECT 1
      FROM UNNEST(activities) AS earlier_activity WITH OFFSET AS earlier_offset
      JOIN UNNEST(activities) AS later_activity WITH OFFSET AS later_offset
        ON earlier_offset < later_offset
      WHERE
        CASE earlier_activity
          WHEN 'Admission' THEN 0
          WHEN 'Triage' THEN 1
          WHEN 'Diagnosis' THEN 2
          WHEN 'Treatment' THEN 3
          WHEN 'Discharge' THEN 4
        END
        >
        CASE later_activity
          WHEN 'Admission' THEN 0
          WHEN 'Triage' THEN 1
          WHEN 'Diagnosis' THEN 2
          WHEN 'Treatment' THEN 3
          WHEN 'Discharge' THEN 4
        END
    ) AS has_out_of_order,
    EXISTS (
      SELECT 1
      FROM UNNEST(activities) AS activity
      WHERE activity NOT IN (
        'Admission', 'Triage', 'Diagnosis', 'Treatment', 'Discharge'
      )
    ) AS has_extra_activity
  FROM case_traces
),
classified_cases AS (
  SELECT
    *,
    is_exact_path
      AND NOT has_skipped
      AND NOT has_repeated
      AND NOT has_out_of_order
      AND NOT has_extra_activity AS is_compliant
  FROM case_flags
),
deviation_counts AS (
  SELECT
    deviation_type,
    COUNT(*) AS case_count
  FROM classified_cases
  CROSS JOIN UNNEST([
    IF(has_skipped, 'skipped', NULL),
    IF(has_repeated, 'repeated', NULL),
    IF(has_out_of_order, 'out_of_order', NULL),
    IF(has_extra_activity, 'extra_activity', NULL)
  ]) AS deviation_type
  WHERE deviation_type IS NOT NULL
  GROUP BY deviation_type
),
ranked_deviations AS (
  SELECT
    deviation_type,
    case_count,
    ROW_NUMBER() OVER (
      ORDER BY case_count DESC, deviation_type
    ) AS deviation_rank
  FROM deviation_counts
),
compliance_summary AS (
  SELECT
    COUNT(*) AS total_cases,
    COUNTIF(is_compliant) AS compliant_cases,
    COUNTIF(NOT is_compliant) AS non_compliant_cases
  FROM classified_cases
)
SELECT
  'compliance_summary' AS result_type,
  CAST(NULL AS STRING) AS deviation_type,
  total_cases AS case_count,
  compliant_cases,
  non_compliant_cases,
  CAST(NULL AS INT64) AS deviation_rank
FROM compliance_summary
UNION ALL
SELECT
  'deviation_type' AS result_type,
  deviation_type,
  case_count,
  CAST(NULL AS INT64) AS compliant_cases,
  CAST(NULL AS INT64) AS non_compliant_cases,
  deviation_rank
FROM ranked_deviations
ORDER BY result_type, deviation_rank;
