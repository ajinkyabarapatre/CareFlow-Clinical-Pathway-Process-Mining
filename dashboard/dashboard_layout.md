\# CareFlow Dashboard Layout (Draft)



\## Page 1: Overview

+-------------------------------------------------------------+

| Title: CareFlow - ER Patient Flow                           |

+----------------+----------------+---------------+-----------+

| Avg Wait Time  | Loop-back %    | Cases Per Day | Non-      |

| (KPI card)     | (KPI card)     | (KPI card)    | compliant |

|                |                |               | (KPI card)|

+----------------+----------------+---------------+-----------+

| Bottleneck chart: avg wait between steps   | Slicers:       |

| (bar chart, longest wait on top)           | - Doctor       |

|                                            | - Age group    |

|                                            | - Gender       |

|                                            | - Date         |

+--------------------------------------------+----------------+



\## Page 2: Patient Process Map

\- Process flow diagram (Registration, Triage, Doctor, X-Ray, Discharge)

\- Arrows show how many patients move between steps

\- Loop-back arrow (X-Ray back to Triage) highlighted in red



\## Page 3: Insights and Action

\- Top 3 findings (example: 40% patients sent back to Triage after X-Ray)

\- Recommended action (example: update the intake form)

\- Table of non-compliant paths



\## Data needed (from Members 1, 2, 3)

\- event\_log table (case\_id, activity\_name, timestamp, resource)

\- transitions table (from\_activity, to\_activity, wait\_minutes)

\- case\_paths / conformance table (actual path, is\_compliant)

