\# Data Dictionary - CareFlow



\## 1. Source file: patients.csv

\- One row per patient, 40,600 rows, 21 columns

\- It is not an event log yet. It has only dates (no time of day) and two waiting-time columns.

\- Member 1 will build the event log (case\_id, activity\_name, timestamp) from it.



\## 2. Columns

\- patient\_id: unique patient ID (will be the case ID)

\- patient\_category: Appointment, Walk-in or Emergency

\- patient\_type: OPD or IPD

\- visit\_type: new patient or follow-up

\- gender: Male or Female

\- age: age in years

\- blood\_group: patient blood group

\- area: area where the patient lives

\- disease: diagnosis

\- severity\_level: how serious the case is

\- referral\_source: how the patient came (Self, Doctor Referral, Emergency)

\- admission\_date: date of admission (no time)

\- discharge\_date: date of discharge (no time)

\- doctor\_id: doctor who treated the patient

\- treatment\_cost: cost of treatment

\- payment\_method: how the patient paid

\- insurance: Yes or No

\- patient\_status: outcome, for example Recovered

\- opd\_waiting\_time\_min: waiting time for OPD patients, in minutes

\- room\_allocation\_time\_min: time to get a room (IPD and Emergency), in minutes

\- patient\_rating: patient feedback score



\## 3. Known data problems

\- patient\_rating: 2,048 missing values

\- discharge\_date: 491 missing values

\- blood\_group: 284 missing values

\- area: 275 missing values

\- payment\_method: 256 missing values

\- 3 duplicate rows

\- Cleaning will be done by Member 1 and Member 2.

\- Question: are blank discharge dates patients who are still admitted?



\## 4. Event log (to be created by Member 1)

\- case\_id: from patient\_id

\- activity\_name: steps created for each patient

\- timestamp: admission date plus waiting times (time of day is simulated)

\- resource: doctor\_id



\## 5. Activity names the team will use

Registration, Triage, Doctor Consultation, Room Allocation, Treatment, Discharge

