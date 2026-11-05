# Final Findings Report

## Objective

Summarize the observed clinical pathway, identify transitions with the longest
average waits, and compare each case with the configured ideal pathway. The
findings describe the checked-in sample event log and should not be treated as
estimates for the hospital population.

## Data

The generated `discovery_summary.csv` reports **4 cases**, **20 events**,
**5 activities**, and **4 variants**. The chart KPI summary reports that
**25%** of cases contained a loop-back.

## Method

- **PM4Py discovery:** `process_discovery.py` converted the event log to a
  PM4Py event log and discovered a directly-follows graph and an Inductive
  Miner Petri net. It also wrote the case, event, activity, and variant
  counts to `discovery_summary.csv`.
- **Bottleneck calculation:** `bottleneck_analysis.py` grouped consecutive
  activity pairs and calculated their average waiting times. Its ranked
  `bottlenecks.csv` contains the transition metrics; `bottleneck_transitions.csv`
  is the Power BI transition export.
- **Conformance checking:** `conformance_check.py` compared each observed
  sequence with the configured ideal path:
  `Admission -> Triage -> Diagnosis -> Treatment -> Discharge`.

## Key Findings

- **Main path:** `top_variants.csv` ranks
  `Admission -> Diagnosis -> Triage -> Treatment -> Discharge` first, observed
  in **1 case (25%)**. This is not a unique leading path: all **4 variants**
  occur once each (**25%** apiece).
- **Top three bottlenecks by average wait:**
  1. `Treatment -> Discharge`: **45 minutes** across 4 transitions.
  2. `Admission -> Diagnosis`: **45 minutes** across 1 transition.
  3. `Triage -> Treatment`: **37.5 minutes** across 2 transitions.
- **Loop-backs:** **25%** of cases included a repeated activity. The loop-back
  output identifies `Triage -> Triage` in 1 case.
- **Conformance:** **25% compliant** and **75% non-compliant** (1 and 3 cases,
  respectively). There is no single most frequent deviation: skipped step,
  loop-back/repeated step, and wrong order each occur once.
- The KPI summary's selected top-bottleneck label is
  `Admission -> Diagnosis` at **45 minutes**. The detailed bottleneck table
  shows that `Treatment -> Discharge` has the same average wait, so the
  longest average wait is a tie.

## Business Recommendation

Review the handoffs around `Treatment -> Discharge` and
`Admission -> Diagnosis`, beginning with the cases and timestamp records behind
those transitions. In parallel, reinforce the intended order of triage before
diagnosis and review why triage was repeated. Treat these as targeted
investigation areas, not evidence for staffing or policy changes: the sample
contains only four cases and the observed waits are not representative.

## Limitations

- The checked-in event log is simulated demonstration data, not a validated
  extract of hospital operations.
- The sample is small: it contains only four cases, so percentages and average
  waits are sensitive to individual traces.
- Conformance is measured against one ideal path, which assumes
  `Admission -> Triage -> Diagnosis -> Treatment -> Discharge` is appropriate
  for every case. Legitimate clinical variations may be labeled as deviations.
- The four variants tie for frequency; the report does not imply a uniquely
  dominant pathway.

## Next Steps

1. Validate activity names, timestamps, case identifiers, and the ideal path
   with clinical and data owners.
2. Run the pipeline on a representative, approved event-log extract.
3. Review the longest-wait transitions and each deviation with care teams,
   then test any proposed workflow change against subsequent data.
4. Re-run the process-mining pipeline and compare the resulting transition,
   conformance, and KPI CSVs.
