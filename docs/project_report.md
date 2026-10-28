# CareFlow: Clinical Pathway Process Mining - Project Report

## 1. Introduction
- Problem: hospital managers do not know why Emergency Room waiting times are high. Average wait time does not show the real steps a patient goes through.
- Goal: use process mining on timestamped hospital event data to find hidden bottlenecks and show them in a dashboard.

## 2. Team and Roles
- Member 1: data generation and loading (branch m1-data-generation)
- Member 2: BigQuery and dbt (branch m2-warehouse-dbt)
- Member 3: process mining (branch m3-process-mining)
- Member 4: dashboard and documentation (branch m4-dashboard-docs)

## 3. Tools Used
Python, Google BigQuery, dbt, PM4Py, Power BI, GitHub

## 4. Dataset
- patients.csv: one row per patient, 21 columns (see docs/data_dictionary.md)
- Data problems found: missing values and 3 duplicate rows
- It has dates only, so an event log with times has to be built from it

## 5. Method
### 5.1 Data preparation
(to be filled: cleaning and event log creation)
### 5.2 Process discovery
(to be filled: process map made with PM4Py, script process_mining/discovery.py)
### 5.3 Bottleneck analysis
(to be filled)
### 5.4 Conformance checking
(to be filled)

## 6. Dashboard
- Draft pages built in Power BI: KPI cards, waiting time by disease, filters
- KPI definitions: dashboard/kpi_definitions.md
- Layout plan: dashboard/dashboard_layout.md
(to be filled: final pages, screenshots, insights)

## 7. Findings and Recommended Action
(to be filled after the analysis is done)

## 8. Challenges
- Team Git setup at the start
- The dashboard depends on the event log from the data team
- Missing values in the dataset

## 9. Conclusion
(to be filled)
