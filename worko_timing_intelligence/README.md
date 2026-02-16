# Timing Intelligence and Candidate Readiness

Hi, I am Dania.

This project is a product style prototype that ranks candidates by fit and readiness, then recommends the next action. It is built for proactive recruiting workflows where timing matters as much as skill match.

It runs locally and includes demo datasets so you can open it and see everything working immediately.

## What you can do

Select a role and set required skills  
Adjust scoring weights to match your recruiting strategy  
Generate a ranked shortlist with an explainability view  
Create a simple outreach plan with recommended next touch dates  
Download the shortlist as a CSV

## Project structure

app.py is the Streamlit app  
src contains the scoring logic and data loader  
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

Roles CSV must include role_id role_title target_start_date  
Candidates CSV must include candidate_id candidate_name role_id skills availability_date last_contacted_date

Optional columns supported  
engagement open_to_roles preferred_work_mode location years_experience

Regards,  
Dania Sami
