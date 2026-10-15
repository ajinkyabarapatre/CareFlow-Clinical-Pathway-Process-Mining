\# CareFlow Dashboard KPIs



These are the main numbers our dashboard will show.



\## 1. Average Wait Time

\- Meaning: average time a patient waits from arrival to discharge

\- How: discharge time minus registration time, then average of all patients



\## 2. Average Time Between Steps

\- Meaning: how long patients wait between two steps (example: Triage to Doctor)

\- How: time of next step minus time of current step, averaged per pair of steps



\## 3. Loop-back Percentage

\- Meaning: % of patients sent back to an earlier step (example: X-Ray back to Triage)

\- How: patients with a loop-back divided by total patients x 100



\## 4. Longest Transition (Biggest Bottleneck)

\- Meaning: the step-to-step move with the highest average wait

\- How: sort the average time between steps from highest to lowest



\## 5. Cases Per Day

\- Meaning: number of patients visiting the ER each day

\- How: count of unique visit IDs per date



\## 6. Non-Compliant Cases

\- Meaning: patients who did not follow the ideal path

\- How: compare each patient's path with the ideal path (from Member 3's work)





\## KPIs we can build now from patients.csv

\- Average OPD waiting time: average of opd\_waiting\_time\_min, OPD patients only

\- Average room allocation time: average of room\_allocation\_time\_min, IPD and Emergency only

\- Patients per day: count of patient\_id for each admission\_date

\- Average patient rating: average of patient\_rating, ignoring blanks

\- Average treatment cost: average of treatment\_cost

\- Waiting time by disease: bar chart of opd\_waiting\_time\_min per disease



\## Filters (slicers)

\- Patient type, patient category, severity level, disease, doctor ID, gender, area, age group, date



\## KPIs that need the event log (later)

\- Loop-back percentage

\- Average time between steps

\- Longest transition (biggest bottleneck)

\- Non-compliant cases

