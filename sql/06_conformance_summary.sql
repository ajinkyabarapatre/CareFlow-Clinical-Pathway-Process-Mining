-- Count cases whose timestamp-ordered activity trace exactly matches the ideal path.
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
    CAST(case_id AS STRING) AS case_id,
    ARRAY_AGG(
      TRIM(CAST(activity AS STRING))
      ORDER BY timestamp, TRIM(CAST(activity AS STRING))
    ) AS activities
  FROM `project.dataset.event_log`
  GROUP BY case_id
),
classified_cases AS (
  SELECT
    case_id,
    ARRAY_LENGTH(activities) = 5
      AND activities[SAFE_OFFSET(0)] = 'Admission'
      AND activities[SAFE_OFFSET(1)] = 'Triage'
      AND activities[SAFE_OFFSET(2)] = 'Diagnosis'
      AND activities[SAFE_OFFSET(3)] = 'Treatment'
      AND activities[SAFE_OFFSET(4)] = 'Discharge' AS is_conforming
  FROM case_traces
)
SELECT
  COUNT(*) AS total_cases,
  COUNTIF(is_conforming) AS conforming_cases,
  COUNTIF(NOT is_conforming) AS non_conforming_cases
FROM classified_cases;
