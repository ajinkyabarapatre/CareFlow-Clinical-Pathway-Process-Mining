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

