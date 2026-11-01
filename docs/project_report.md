# CareFlow: Clinical Pathway Process Mining - Project Report

## \## 1. Introduction

## In hospitals, waiting time in the Emergency Room is a big problem. Managers usually look at the average waiting time, but an average does not show what really happens to a patient from the moment they arrive until they leave. Patients can be sent back to an earlier step, wait too long between steps, or skip steps, and an average hides all of this.

## 

## CareFlow is our project to solve this. We use process mining, which reads timestamped hospital event data (who did what, and when) and builds a map of the real patient journey. The aim is to find the hidden bottlenecks and show them in a dashboard, so the hospital can take a clear action, such as changing an intake form, to reduce waiting time.

## 

## \## 2. Team and Roles

## Our team has four members and one GitHub repository, with a separate branch for each member.

## \- Member 1: creates the data and loads it into the warehouse (branch m1-data-generation)

## \- Member 2: BigQuery and dbt data cleaning (branch m2-warehouse-dbt)

## \- Member 3: process mining with PM4Py (branch m3-process-mining)

## \- Member 4: dashboard and documentation (branch m4-dashboard-docs)

## Work is merged into the main branch using pull requests.

## 

## \## 3. Tools Used

## \- Python: scripts for data and process mining

## \- Google BigQuery: stores the event data

## \- dbt: cleans and standardises the data

## \- PM4Py: finds the process map from the event data

## \- Power BI: builds the dashboard

## \- GitHub: version control and teamwork

## 

## \## 4. Dataset

## We use a file called patients.csv with 40,600 rows, one row for each patient, and 21 columns (for example patient type, disease, severity level, doctor, admission date, waiting time and rating). The full list of columns is in docs/data\_dictionary.md.

## 

## We found some problems in the data: missing values in patient\_rating, discharge\_date, blood\_group, area and payment\_method, and 3 duplicate rows. The data also has dates but no time of day, and process mining needs timestamps for each step. So an event log with case ID, activity name and timestamp has to be created from this file, and the times will be simulated. The cleaning and event log creation are done by Member 1 and Member 2.



## 5. Method
### 5.1 Data preparation
The dataset has missing values and duplicate rows, and no time of day. Cleaning and creating the event log (case ID, activity name, timestamp) is done by Member 1 and Member 2. (to be filled when their work is pushed)

### 5.2 Process discovery
Member 3 wrote a Python script, process_mining/discovery.py, for process discovery. The script reads [file or table name] and uses the columns [case ID column], [activity column] and [timestamp column] as the event log. It then uses the PM4Py library to create [a directly-follows graph / a Petri net / other], which shows [how patients move from one step to the next]. The result is saved as [output file name]. [Optional: one sentence on what the map shows, but only if you can see the picture and know what it says.]
### 5.3 Bottleneck analysis
(to be filled: average and longest waiting time between steps)

### 5.4 Conformance checking
(to be filled: comparing actual patient paths with the ideal path)

## 6. Dashboard
We built the dashboard in Power BI Desktop. Because the event log was not ready, the draft pages use patients.csv. When the event log is ready, the process map and loop-back pages will use it.

### 6.1 Page 1: Overview
- Average OPD waiting time (card)
- Number of patients (card)
- Average patient rating (card)
- Average waiting time by disease (bar chart)
- Filters (slicers): patient type, severity level

![Dashboard page 1](../dashboard/screenshots/page1_draft.png)

### 6.2 KPIs
The KPIs and how they are calculated are written in dashboard/kpi_definitions.md. From patients.csv we can build: average OPD waiting time, average room allocation time, patients per day, average rating and average treatment cost. These need the event log: loop-back percentage, average time between steps, longest transition and non-compliant cases.

### 6.3 Planned pages
- Page 2: waiting time analysis by doctor, severity level and patient category
- Page 3: process map of patient flow with the loop-back highlighted
- Page 4: findings and the recommended action
The full plan is in dashboard/dashboard_layout.md.

### 6.4 Limitations
- The data has dates only, so times of day are simulated.
- The Power BI file is not stored in the repository because it contains patient data and the repository is public.

## 7. Findings and Recommended Action
(to be filled after the analysis is done)

## 8. Challenges
- Git setup problems at the start of the project
- A merge conflict in the .gitignore file, solved by keeping both sets of lines
- The dashboard depends on the event log from the data team
- Missing values and no time of day in the dataset

## 9. Conclusion
(to be filled at the end of the project)
