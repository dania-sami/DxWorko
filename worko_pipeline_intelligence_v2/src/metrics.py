from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd


STAGE_ORDER = ["sourced", "screened", "interview", "offer", "hired", "rejected"]


def _to_dt(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def normalize_events(df: pd.DataFrame) -> pd.DataFrame:
    required = {"candidate_id", "role_id", "stage", "stage_entered_at", "stage_exited_at"}
    missing = required.difference(set(df.columns))
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

    out = df.copy()
    out["stage"] = out["stage"].astype(str).str.strip().str.lower()
    out["stage_entered_at"] = _to_dt(out["stage_entered_at"])
    out["stage_exited_at"] = _to_dt(out["stage_exited_at"])
    return out


def stage_funnel(df: pd.DataFrame, role_id: str | None = None) -> pd.DataFrame:
    data = df
    if role_id:
        data = data[data["role_id"] == role_id]

    # One candidate can have multiple stage rows. Count unique candidates who reached each stage.
    reached = (
        data.groupby("stage")["candidate_id"]
        .nunique()
        .reindex(STAGE_ORDER, fill_value=0)
        .reset_index()
        .rename(columns={"candidate_id": "candidates"})
    )

    # Conversion between successive non terminal stages
    conv = []
    for i in range(len(STAGE_ORDER) - 1):
        s_from = STAGE_ORDER[i]
        s_to = STAGE_ORDER[i + 1]
        a = int(reached.loc[reached["stage"] == s_from, "candidates"].iloc[0])
        b = int(reached.loc[reached["stage"] == s_to, "candidates"].iloc[0])
        rate = 0.0 if a == 0 else b / a
        conv.append({"from_stage": s_from, "to_stage": s_to, "conversion_rate": rate})
    conv_df = pd.DataFrame(conv)
    return reached, conv_df


def time_in_stage(df: pd.DataFrame, role_id: str | None = None) -> pd.DataFrame:
    data = df
    if role_id:
        data = data[data["role_id"] == role_id]

    tmp = data.copy()
    tmp = tmp[tmp["stage_exited_at"].notna()]
    tmp["days_in_stage"] = (tmp["stage_exited_at"] - tmp["stage_entered_at"]).dt.total_seconds() / 86400.0
    agg = (
        tmp.groupby("stage")["days_in_stage"]
        .agg(["count", "mean", "median"])
        .reindex(STAGE_ORDER, fill_value=0)
        .reset_index()
    )
    return agg


def time_to_fill(df: pd.DataFrame, role_id: str | None = None) -> Tuple[float, float]:
    """
    Returns:
      average_days_to_hire, hire_rate
    """
    data = df
    if role_id:
        data = data[data["role_id"] == role_id]

    # Identify hire completion time per candidate by looking for stage "hired" row
    hired = data[data["stage"] == "hired"][["candidate_id", "stage_entered_at"]].dropna()
    if hired.empty:
        return float("nan"), 0.0

    # For each hired candidate, find their first event time
    first_seen = (
        data.groupby("candidate_id")["stage_entered_at"]
        .min()
        .reset_index()
        .rename(columns={"stage_entered_at": "first_seen_at"})
    )
    merged = hired.merge(first_seen, on="candidate_id", how="left")
    merged["days_to_hire"] = (merged["stage_entered_at"] - merged["first_seen_at"]).dt.total_seconds() / 86400.0
    avg_days = float(merged["days_to_hire"].mean())
    hire_rate = float(hired["candidate_id"].nunique() / data["candidate_id"].nunique()) if data["candidate_id"].nunique() else 0.0
    return avg_days, hire_rate


def pipeline_sufficiency(target_hires: int, overall_hire_rate: float, current_pipeline: int) -> Dict[str, float]:
    """
    A practical rule:
      required_pipeline = target_hires / hire_rate
    """
    if overall_hire_rate <= 0:
        required = float("inf")
        suff = 0.0
    else:
        required = target_hires / overall_hire_rate
        suff = min(1.0, current_pipeline / required) if required > 0 else 1.0

    gap = max(0.0, required - current_pipeline) if math.isfinite(required) else float("inf")
    return {"required_pipeline": required, "sufficiency": suff, "pipeline_gap": gap}


def availability_distribution(events: pd.DataFrame, role_id: str | None = None) -> pd.DataFrame:
    data = events
    if role_id:
        data = data[data["role_id"] == role_id]

    if "availability_date" not in data.columns:
        return pd.DataFrame(columns=["availability_date", "candidates"])

    tmp = data.dropna(subset=["availability_date"]).copy()
    tmp["availability_date"] = pd.to_datetime(tmp["availability_date"], errors="coerce").dt.date
    tmp = tmp.dropna(subset=["availability_date"])
    # Count unique candidates by availability date
    dist = tmp.groupby("availability_date")["candidate_id"].nunique().reset_index().rename(columns={"candidate_id": "candidates"})
    return dist.sort_values("availability_date")


def revenue_risk(value_per_day_sek: float, days_delayed: float) -> float:
    if value_per_day_sek < 0 or days_delayed < 0:
        return 0.0
    return float(value_per_day_sek * days_delayed)
