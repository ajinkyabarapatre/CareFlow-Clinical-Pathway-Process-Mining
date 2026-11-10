🏥 CareFlow – Clinical Pathway Process Mining

📌 About the Project

CareFlow is a healthcare data analytics and process mining project focused on understanding patient journeys and hospital operations.

The main goal of this project is to analyze hospital data, understand how patients move through different healthcare services, identify delays and bottlenecks, and discover opportunities to improve hospital workflows.

I am developing this project using Python and Data Science techniques, starting with data collection, data cleaning, and exploratory data analysis before moving towards process mining.

🎯 Project Objectives

- Understand patient admission and discharge patterns.
- Analyze patient information and doctor details.
- Identify missing and inconsistent data.
- Study department-wise patient distribution.
- Analyze disease-wise treatment costs.
- Understand patient waiting times.
- Discover clinical pathways using process mining.
- Identify bottlenecks in hospital operations.
- Present meaningful insights through data visualization.

🛠️ Technologies Used

Technology| Purpose
Python| Programming
Pandas| Data cleaning and manipulation
NumPy| Numerical operations
PM4Py| Process mining
Streamlit| Interactive dashboard
Jupyter Notebook| Development and analysis
Git & GitHub| Version control

📂 Dataset Information

The project currently uses two datasets.

1. Doctors Dataset ("doctors.csv")

Contains information about hospital doctors. 

- Doctor ID
- Doctor Name
- Specialization
- Department
- Doctor Type
- Experience Years
- Consultation Fee
- Doctor Shift
- Maximum Patients Per Day

2. Patients Dataset ("patients.csv")

Contains patient and hospital visit information.

- Patient ID
- Patient Category
- Patient Type
- Visit Type
- Gender
- Age
- Blood Group
- Disease
- Severity Level
- Admission Date
- Discharge Date
- Doctor ID
- Treatment Cost
- Payment Method
- Insurance
- Patient Status
- OPD Waiting Time
- Patient Rating

🔄 Project Workflow

The project follows these main steps:

1. Data Collection
2. Data Loading
3. Data Integration
4. Data Cleaning
5. Missing Value Treatment
6. Data Validation
7. Feature Engineering
8. Exploratory Data Analysis (EDA)
9. Event Log Preparation
10. Process Discovery using PM4Py
11. Clinical Pathway Analysis
12. Bottleneck Identification
13. Dashboard Development

📊 Current Project Progress

Completed Work

- Loaded doctors and patients datasets using Pandas.
- Integrated both datasets using "doctor_id".
- Performed initial data inspection.
- Identified missing values.
- Removed unnecessary columns.
- Detected and removed 56 duplicate records.
- Performed initial statistical analysis.
- Analyzed department-wise patient counts.
- Analyzed average treatment costs by disease.

Work in Progress

- Missing value treatment.
- Invalid data identification.
- Date and timestamp validation.
- Patient ID validation.
- Data quality checks.

Upcoming Work

- Feature engineering.
- Advanced exploratory data analysis.
- Data visualization.
- Clinical event log creation.
- Process discovery using PM4Py.
- Patient pathway analysis.
- Bottleneck analysis.
- Interactive Streamlit dashboard.

📈 Initial Dataset Information

After merging the datasets and removing duplicate complete rows:

Description| Value
Total Records| 40,544
Total Columns| 25
Duplicate Rows Remaining| 0
Doctors Dataset| doctors.csv
Patients Dataset| patients.csv

These values represent the current data preparation stage and may change during validation.

📁 Repository Structure

CareFlow-Clinical-Pathway-Process-Mining/m1-data-generation
│
├── README.md
├── doctors.csv
├── patients.csv
├── data.ipynb
│
└── (Additional modules and outputs
    will be added during development)

⚙️ Installation and Setup

Step 1: Clone the repository

git clone YOUR_REPOSITORY_URL

Step 2: Open the project folder

cd CareFlow-Clinical-Pathway-Process-Mining

Step 3: Install required libraries

pip install pandas numpy matplotlib seaborn pm4py streamlit

Step 4: Start Jupyter Notebook

jupyter notebook

Open "data.ipynb" to explore the data preparation and analysis work.

💡 Expected Outcomes

By the end of this project, CareFlow aims to provide:

- Better understanding of patient journeys.
- Insights into hospital department performance.
- Analysis of patient waiting times.
- Identification of clinical workflow bottlenecks.
- Visualization of patient treatment pathways.
- Data-driven insights into hospital operations.

Project: CareFlow – Clinical Pathway Process Mining

---

⭐ If you find this project interesting, feel free to explore the repository and share your feedback.

This project is currently under development.
