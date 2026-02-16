from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.metrics import (
    availability_distribution,
    normalize_events,
    pipeline_sufficiency,
    revenue_risk,
    stage_funnel,
    time_in_stage,
    time_to_fill,
)
from src.sample_data import load_demo_data


APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"

st.set_page_config(page_title="Worko Pipeline Intelligence", page_icon="📊", layout="wide")

CSS = """
<style>
:root {
  --card-bg: rgba(255, 255, 255, 0.04);
  --card-border: rgba(255, 255, 255, 0.10);
  --muted: rgba(255, 255, 255, 0.70);
}
.block-container { padding-top: 2.25rem; padding-bottom: 3rem; }
h1 { letter-spacing: -0.02em; }
.small-muted { color: var(--muted); font-size: 0.92rem; }
.card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 16px 18px;
}
.card h3 { margin: 0 0 0.25rem 0; font-size: 1.0rem; font-weight: 600; }
.card p { margin: 0; color: var(--muted); font-size: 0.9rem; }
.kpi { font-size: 2.2rem; font-weight: 700; line-height: 1.1; margin-top: 0.35rem; }
.kpi-sub { color: var(--muted); font-size: 0.9rem; margin-top: 0.25rem; }
.hr { height: 1px; background: rgba(255,255,255,0.08); margin: 18px 0; }
.section-title { font-size: 1.15rem; font-weight: 650; margin: 0 0 8px 0; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown("## Worko Pipeline Intelligence")
st.markdown('<div class="small-muted">A practical dashboard for pipeline health, conversion, and time to fill.</div>', unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _read_csv(upload) -> pd.DataFrame:
    return pd.read_csv(upload)

with st.sidebar:
    st.subheader("Data")
    use_demo = st.toggle("Use demo data", value=True)

    roles_upload = st.file_uploader("Roles CSV", type=["csv"], disabled=use_demo)
    events_upload = st.file_uploader("Candidate events CSV", type=["csv"], disabled=use_demo)

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.subheader("Revenue impact")
    value_per_day = st.number_input("Estimated value per day SEK", min_value=0, value=7000, step=500)
    days_delayed = st.number_input("Delay in days", min_value=0, value=14, step=1)

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.subheader("Display")
    show_tables = st.toggle("Show tables", value=False)
    compact = st.toggle("Compact layout", value=False)

if use_demo:
    roles_df, events_df = load_demo_data(DATA_DIR)
else:
    if roles_upload is None or events_upload is None:
        st.info("Upload both CSV files or switch on demo data.")
        st.stop()
    roles_df = _read_csv(roles_upload)
    events_df = _read_csv(events_upload)

try:
    events_df = normalize_events(events_df)
except Exception as e:
    st.error(f"Could not read events file: {e}")
    st.stop()

roles_df = roles_df.copy()
if "role_id" not in roles_df.columns:
    st.error("Roles CSV must include role_id")
    st.stop()

role_options = roles_df["role_id"].astype(str).tolist()
role_pick = st.selectbox("Select role", options=["All roles"] + role_options, index=0)
role_id = None if role_pick == "All roles" else role_pick

avg_days, hire_rate = time_to_fill(events_df, role_id=role_id)
pipeline_size = int(events_df[events_df["role_id"] == role_id]["candidate_id"].nunique()) if role_id else int(events_df["candidate_id"].nunique())

if role_id:
    role_row = roles_df[roles_df["role_id"] == role_id].iloc[0]
    target_hires = int(role_row.get("target_hires", 1))
    vpd = float(role_row.get("estimated_value_per_day_sek", value_per_day))
    role_title = str(role_row.get("role_title", role_id))
    dept = str(role_row.get("department", ""))
else:
    target_hires = int(roles_df.get("target_hires", pd.Series([1])).sum()) if "target_hires" in roles_df.columns else 1
    vpd = float(value_per_day)
    role_title = "All roles"
    dept = ""

suff = pipeline_sufficiency(target_hires=target_hires, overall_hire_rate=hire_rate, current_pipeline=pipeline_size)
impact = revenue_risk(vpd, float(days_delayed))

gap_txt = "No gap" if math.isfinite(suff["pipeline_gap"]) and suff["pipeline_gap"] <= 0 else (f"{suff['pipeline_gap']:.0f}".replace(",", " ") if math.isfinite(suff["pipeline_gap"]) else "Unknown")
avg_txt = "No hires yet" if math.isnan(avg_days) else f"{avg_days:.1f} days"

cols = st.columns(4, gap="large" if not compact else "small")
with cols[0]:
    st.markdown(
        f"""
        <div class="card">
          <h3>Pipeline size</h3>
          <div class="kpi">{pipeline_size}</div>
          <div class="kpi-sub">Unique candidates in scope</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with cols[1]:
    st.markdown(
        f"""
        <div class="card">
          <h3>Hire rate</h3>
          <div class="kpi">{hire_rate*100:.1f}%</div>
          <div class="kpi-sub">Hired divided by total candidates</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with cols[2]:
    st.markdown(
        f"""
        <div class="card">
          <h3>Average time to hire</h3>
          <div class="kpi">{avg_txt}</div>
          <div class="kpi-sub">From first touch to hired</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with cols[3]:
    st.markdown(
        f"""
        <div class="card">
          <h3>Pipeline sufficiency</h3>
          <div class="kpi">{suff['sufficiency']*100:.0f}%</div>
          <div class="kpi-sub">Gap {gap_txt} candidates</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

tab_overview, tab_funnel, tab_timing, tab_revenue = st.tabs(["Overview", "Funnel", "Timing", "Revenue"])

with tab_overview:
    left, right = st.columns([1.2, 0.8], gap="large" if not compact else "small")

    with left:
        st.markdown("<div class='section-title'>Stage distribution</div>", unsafe_allow_html=True)
        reached_df, conv_df = stage_funnel(events_df, role_id=role_id)
        fig = px.bar(reached_df, x="stage", y="candidates", title=None)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
        st.plotly_chart(fig, use_container_width=True)

        if show_tables:
            st.dataframe(reached_df, use_container_width=True)

    with right:
        st.markdown("<div class='section-title'>Role context</div>", unsafe_allow_html=True)
        ctx = {
            "Role": role_title,
            "Department": dept if dept else "Not set",
            "Target hires": target_hires,
            "Value per day SEK": f"{vpd:,.0f}".replace(",", " "),
        }
        ctx_df = pd.DataFrame([ctx]).T.reset_index()
        ctx_df.columns = ["Field", "Value"]
        st.dataframe(ctx_df, use_container_width=True, hide_index=True)

        st.markdown("<div class='section-title'>Availability readiness</div>", unsafe_allow_html=True)
        dist = availability_distribution(events_df, role_id=role_id)
        if dist.empty:
            st.info("No availability data found.")
        else:
            fig2 = px.line(dist, x="availability_date", y="candidates", title=None)
            fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=260)
            st.plotly_chart(fig2, use_container_width=True)

with tab_funnel:
    st.markdown("<div class='section-title'>Conversions</div>", unsafe_allow_html=True)
    reached_df, conv_df = stage_funnel(events_df, role_id=role_id)

    c1, c2 = st.columns([0.9, 1.1], gap="large" if not compact else "small")
    with c1:
        fig = px.bar(reached_df, x="stage", y="candidates", title=None)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        conv_show = conv_df.copy()
        conv_show["conversion_rate"] = (conv_show["conversion_rate"] * 100).round(1).astype(str) + "%"
        st.dataframe(conv_show, use_container_width=True, hide_index=True)

    st.markdown("<div class='small-muted'>Use this view to spot where candidates drop off and where process improvements could unlock more hires.</div>", unsafe_allow_html=True)

with tab_timing:
    st.markdown("<div class='section-title'>Time in stage</div>", unsafe_allow_html=True)
    tis = time_in_stage(events_df, role_id=role_id)
    fig = px.bar(tis, x="stage", y="mean", title=None)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360)
    st.plotly_chart(fig, use_container_width=True)

    if show_tables:
        st.dataframe(tis, use_container_width=True)

    st.markdown("<div class='section-title'>Availability distribution</div>", unsafe_allow_html=True)
    dist = availability_distribution(events_df, role_id=role_id)
    if dist.empty:
        st.info("No availability data found.")
    else:
        fig2 = px.line(dist, x="availability_date", y="candidates", title=None)
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300)
        st.plotly_chart(fig2, use_container_width=True)

with tab_revenue:
    st.markdown("<div class='section-title'>Delay impact</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([0.9, 1.1], gap="large" if not compact else "small")
    with c1:
        impact_txt = f"{impact:,.0f} SEK".replace(",", " ")
        st.markdown(
            f"""
            <div class="card">
              <h3>Estimated impact</h3>
              <div class="kpi">{impact_txt}</div>
              <div class="kpi-sub">Based on the assumptions in the sidebar</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown("<div class='small-muted'>This estimate is meant as a quick decision aid. It helps teams reason about the cost of delay and prioritize pipeline building for roles with higher impact.</div>", unsafe_allow_html=True)

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Role table</div>", unsafe_allow_html=True)
    if role_id:
        st.dataframe(roles_df[roles_df["role_id"] == role_id], use_container_width=True, hide_index=True)
    else:
        st.dataframe(roles_df, use_container_width=True, hide_index=True)

st.caption("Tip: Replace the demo CSV files with your own exports to reuse this dashboard.")
