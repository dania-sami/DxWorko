from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_io import load_demo_data
from src.scoring import compute_candidate_score, next_touch_recommendation


APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"

st.set_page_config(page_title="Timing Intelligence", page_icon="🧭", layout="wide")

CSS = """
<style>
:root {
  --card-bg: rgba(255, 255, 255, 0.04);
  --card-border: rgba(255, 255, 255, 0.10);
  --muted: rgba(255, 255, 255, 0.70);
}
.block-container { padding-top: 2.25rem; padding-bottom: 3rem; }
.small-muted { color: var(--muted); font-size: 0.92rem; }
.card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 16px 18px;
}
.card h3 { margin: 0 0 0.25rem 0; font-size: 1.0rem; font-weight: 600; }
.kpi { font-size: 2.2rem; font-weight: 700; line-height: 1.1; margin-top: 0.35rem; }
.kpi-sub { color: var(--muted); font-size: 0.9rem; margin-top: 0.25rem; }
.hr { height: 1px; background: rgba(255,255,255,0.08); margin: 18px 0; }
.section-title { font-size: 1.15rem; font-weight: 650; margin: 0 0 8px 0; }
.pill {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.03);
  color: rgba(255,255,255,0.85);
  font-size: 0.86rem;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown("## Timing Intelligence and Candidate Readiness")
st.markdown('<div class="small-muted">A decision support view that ranks candidates by fit and readiness, then recommends the next action.</div>', unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _read_csv(upload) -> pd.DataFrame:
    return pd.read_csv(upload)

today = pd.Timestamp.today().normalize()

with st.sidebar:
    st.subheader("Data")
    use_demo = st.toggle("Use demo data", value=True)
    roles_upload = st.file_uploader("Roles CSV", type=["csv"], disabled=use_demo)
    cand_upload = st.file_uploader("Candidates CSV", type=["csv"], disabled=use_demo)

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.subheader("Role requirements")
    req_skills_text = st.text_area("Required skills", value="SQL, Python, AWS, Airflow, PostgreSQL")
    min_exp = st.slider("Minimum years of experience", 0, 10, 2)

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.subheader("Weights")
    w_skill = st.slider("Skill match", 0, 10, 6)
    w_avail = st.slider("Availability", 0, 10, 6)
    w_fresh = st.slider("Freshness", 0, 10, 4)
    w_eng = st.slider("Engagement", 0, 10, 4)
    w_open = st.slider("Openness", 0, 10, 3)
    w_mode = st.slider("Work mode match", 0, 10, 2)

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.subheader("Filters")
    only_ready = st.toggle("Show candidates ready by target start", value=False)
    show_tables = st.toggle("Show details table", value=True)

weights = {
    "skill_match": float(w_skill),
    "availability": float(w_avail),
    "freshness": float(w_fresh),
    "engagement": float(w_eng),
    "openness": float(w_open),
    "work_mode_match": float(w_mode),
}

req_skills = {s.strip().lower() for s in req_skills_text.split(",") if s.strip()}

if use_demo:
    roles_df, cand_df = load_demo_data(DATA_DIR)
else:
    if roles_upload is None or cand_upload is None:
        st.info("Upload both CSV files or switch on demo data.")
        st.stop()
    roles_df = _read_csv(roles_upload)
    cand_df = _read_csv(cand_upload)

if "role_id" not in roles_df.columns or "role_id" not in cand_df.columns:
    st.error("Both files must include role_id.")
    st.stop()

role_options = roles_df["role_id"].astype(str).tolist()
role_pick = st.selectbox("Select role", options=role_options, index=0)

role = roles_df[roles_df["role_id"].astype(str) == str(role_pick)].iloc[0]
target_start = pd.to_datetime(role.get("target_start_date"), errors="coerce")

scope = cand_df[cand_df["role_id"].astype(str) == str(role_pick)].copy()
scope["availability_date"] = pd.to_datetime(scope["availability_date"], errors="coerce")
scope["last_contacted_date"] = pd.to_datetime(scope["last_contacted_date"], errors="coerce")
scope["days_until_available"] = (scope["availability_date"] - today).dt.days
scope["days_since_contact"] = (today - scope["last_contacted_date"]).dt.days

if "years_experience" in scope.columns:
    scope = scope[scope["years_experience"].fillna(0).astype(int) >= int(min_exp)]

if only_ready and pd.notna(target_start):
    scope = scope[scope["availability_date"].fillna(target_start) <= target_start]

rows = []
for _, cand in scope.iterrows():
    score, parts, expl = compute_candidate_score(
        candidate=cand,
        role=role,
        role_required_skills=req_skills,
        weights=weights,
        today=today,
    )
    label, cadence_days = next_touch_recommendation(score, cand["last_contacted_date"], today)
    next_touch = (today + pd.Timedelta(days=int(cadence_days))).date().isoformat()

    rows.append({
        "candidate_id": cand.get("candidate_id", ""),
        "candidate_name": cand.get("candidate_name", ""),
        "score": score,
        "action": label,
        "next_touch_date": next_touch,
        "skill_match": parts["skill_match"],
        "availability": parts["availability"],
        "freshness": parts["freshness"],
        "engagement": parts["engagement"],
        "openness": parts["openness"],
        "work_mode_match": parts["work_mode_match"],
        "availability_date": cand["availability_date"].date().isoformat() if pd.notna(cand["availability_date"]) else "",
        "last_contacted_date": cand["last_contacted_date"].date().isoformat() if pd.notna(cand["last_contacted_date"]) else "",
        "preferred_work_mode": cand.get("preferred_work_mode", ""),
        "location": cand.get("location", ""),
        "years_experience": int(cand.get("years_experience", 0)) if pd.notna(cand.get("years_experience", 0)) else 0,
        "explanation": expl,
    })

ranked = pd.DataFrame(rows)
if ranked.empty:
    st.warning("No candidates match the current filters.")
    st.stop()

ranked = ranked.sort_values(["score", "years_experience"], ascending=[False, False]).reset_index(drop=True)

# headline KPIs
top = ranked.head(1).iloc[0]
top_score = f"{top['score']*100:.0f}%"
target_txt = target_start.date().isoformat() if pd.notna(target_start) else "Not set"

c1, c2, c3, c4 = st.columns(4, gap="large")
with c1:
    st.markdown(f"<div class='card'><h3>Role</h3><div class='kpi'>{role.get('role_title','')}</div><div class='kpi-sub'>Target start {target_txt}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='card'><h3>Candidates in scope</h3><div class='kpi'>{len(ranked)}</div><div class='kpi-sub'>After filters and experience</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='card'><h3>Best readiness score</h3><div class='kpi'>{top_score}</div><div class='kpi-sub'>{top['candidate_name']}</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='card'><h3>Recommended next action</h3><div class='kpi'>{top['action']}</div><div class='kpi-sub'>Next touch {top['next_touch_date']}</div></div>", unsafe_allow_html=True)

st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

tab_rank, tab_explain, tab_actions = st.tabs(["Ranked shortlist", "Explainability", "Outreach plan"])

with tab_rank:
    st.markdown("<div class='section-title'>Top candidates</div>", unsafe_allow_html=True)
    show = ranked[["candidate_name","score","action","next_touch_date","availability_date","years_experience","location"]].head(25).copy()
    show["score"] = (show["score"] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(show, use_container_width=True, hide_index=True)

    fig = px.histogram(ranked, x="score", nbins=20, title=None)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        "Download ranked shortlist CSV",
        data=ranked.to_csv(index=False).encode("utf-8"),
        file_name=f"ranked_shortlist_{role_pick}.csv",
        mime="text/csv",
    )

with tab_explain:
    st.markdown("<div class='section-title'>Why candidates are ranked this way</div>", unsafe_allow_html=True)
    pick_name = st.selectbox("Pick a candidate", options=ranked["candidate_name"].tolist(), index=0)
    cand_row = ranked[ranked["candidate_name"] == pick_name].iloc[0]

    st.markdown(f"<span class='pill'>Readiness score {(cand_row['score']*100):.0f}%</span> <span class='pill'>{cand_row['action']}</span>", unsafe_allow_html=True)
    st.write(cand_row["explanation"])

    parts = pd.DataFrame([{
        "Signal": "Skill match",
        "Value": cand_row["skill_match"],
    },{
        "Signal": "Availability",
        "Value": cand_row["availability"],
    },{
        "Signal": "Freshness",
        "Value": cand_row["freshness"],
    },{
        "Signal": "Engagement",
        "Value": cand_row["engagement"],
    },{
        "Signal": "Openness",
        "Value": cand_row["openness"],
    },{
        "Signal": "Work mode match",
        "Value": cand_row["work_mode_match"],
    }])

    fig = px.bar(parts, x="Signal", y="Value", title=None)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
    st.plotly_chart(fig, use_container_width=True)

    if show_tables:
        detail_cols = ["candidate_id","candidate_name","score","action","next_touch_date","availability_date","last_contacted_date","preferred_work_mode","years_experience","location","explanation"]
        view = ranked[detail_cols].copy()
        view["score"] = (view["score"] * 100).round(0).astype(int).astype(str) + "%"
        st.dataframe(view, use_container_width=True, hide_index=True)

with tab_actions:
    st.markdown("<div class='section-title'>Suggested outreach cadence</div>", unsafe_allow_html=True)
    plan = ranked[["candidate_name","action","next_touch_date","availability_date","location","years_experience"]].head(40).copy()
    st.dataframe(plan, use_container_width=True, hide_index=True)

    st.markdown("<div class='small-muted'>This plan helps keep the pipeline warm and prioritizes candidates who match both timing and fit.</div>", unsafe_allow_html=True)
