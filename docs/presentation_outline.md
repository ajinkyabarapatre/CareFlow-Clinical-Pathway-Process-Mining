# Presentation Outline - CareFlow

New-Item -ItemType Directory -Force docs | Out-Null

if (-not (Test-Path docs\\presentation\_outline.md)) {

@'

\# Presentation Outline - CareFlow



Slide 1 - Title: CareFlow: Clinical Pathway Process Mining (team names, Infotact Solutions)

Slide 2 - Problem: ER waiting times are high, but the average wait time does not show what really happens to patients

Slide 3 - Objective: find hidden bottlenecks using process mining and show them in a dashboard that leads to an action

Slide 4 - Team and roles: Members 1 to 4 and their branches

Slide 5 - Tools: Python, BigQuery, dbt, PM4Py, Power BI, GitHub

Slide 6 - Dataset: patients.csv, 40,600 rows, 21 columns, problems found (missing values, duplicates, no time of day)

Slide 7 - Method: data preparation, event log, process discovery, bottleneck analysis, conformance checking

Slide 8 - Process map: screenshot from Member 3's work (to be added)

Slide 9 - Dashboard: Power BI screenshots, KPIs and filters

Slide 10 - Findings and recommended action (to be filled after analysis)

Slide 11 - Challenges: Git setup, missing event log, data quality

Slide 12 - Conclusion and next steps

'@ | Set-Content docs\\presentation\_outline.md

} else { Write-Host "presentation\_outline.md already exists - not overwritten" }

