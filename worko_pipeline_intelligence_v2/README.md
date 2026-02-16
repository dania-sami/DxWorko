# Worko Pipeline Intelligence Engine

Hi, I am Dania.

I built this dashboard as a product style prototype to make pipeline health visible at a glance. It focuses on the signals a recruiter and operations team use to stay proactive, conversion, time in stage, availability readiness, time to hire, and a quick view of delay impact.

It runs locally and includes demo datasets so you can open it and see everything working immediately.

## What you can do

Select one role or view all roles  
View stage distribution and conversion rates  
Measure average time in each stage  
Estimate average time to hire based on historical hires  
Review candidate availability readiness over time  
Calculate a simple delay impact estimate

## Project structure

app.py is the Streamlit app  
src contains the calculations and loaders  
data contains sample CSV files

## How to run

1 Create a virtual environment

python3 -m venv .venv  
source .venv/bin/activate

2 Install dependencies

pip install -r requirements.txt

3 Start the app

streamlit run app.py

## Using your own data

Switch off demo data in the sidebar and upload two CSV files.

Roles CSV must include role_id  
Candidate events CSV must include candidate_id role_id stage stage_entered_at stage_exited_at

Optional columns that the demo also uses  
availability_date last_contacted_date skills location

## Notes

The calculations are intentionally simple so the logic stays transparent and easy to validate. The interface is built to read like a modern internal product, with clean spacing, consistent hierarchy, and role based views.

Regards,  
Dania Sami
