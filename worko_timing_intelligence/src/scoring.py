from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import pandas as pd


def _parse_skills(skills: str) -> set[str]:
    if not isinstance(skills, str):
        return set()
    return {s.strip().lower() for s in skills.split(",") if s.strip()}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a.intersection(b))
    union = len(a.union(b))
    return 0.0 if union == 0 else inter / union


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def days_between(d1: pd.Timestamp, d2: pd.Timestamp) -> float:
    return float((d2 - d1).total_seconds() / 86400.0)


def availability_score(availability_date: pd.Timestamp, target_start: pd.Timestamp) -> float:
    """
    Reward candidates who are available near the target start date.
    1.0 when availability is on or before target start.
    Gradually drops when availability is after target start.
    """
    if pd.isna(availability_date) or pd.isna(target_start):
        return 0.0
    delta = days_between(target_start, availability_date)  # positive means candidate is available after target
    if delta <= 0:
        return 1.0
    # After target start: 0.0 at +90 days
    return clamp01(1.0 - (delta / 90.0))


def freshness_score(last_contacted: pd.Timestamp, today: pd.Timestamp) -> float:
    """
    Recent contact indicates active pipeline.
    1.0 when contacted today, 0.0 at 45 days.
    """
    if pd.isna(last_contacted) or pd.isna(today):
        return 0.0
    delta = days_between(last_contacted, today)
    if delta <= 0:
        return 1.0
    return clamp01(1.0 - (delta / 45.0))


def engagement_score(label: str) -> float:
    m = {"warm": 1.0, "neutral": 0.6, "cold": 0.25}
    if not isinstance(label, str):
        return 0.5
    return float(m.get(label.strip().lower(), 0.5))


def openness_score(label: str) -> float:
    m = {"yes": 1.0, "maybe": 0.6, "no": 0.15}
    if not isinstance(label, str):
        return 0.5
    return float(m.get(label.strip().lower(), 0.5))


def scarcity_multiplier(level: str) -> float:
    """
    For scarce roles, timing and engagement matters more.
    We use this as a small boost to the final score.
    """
    m = {"high": 1.08, "medium": 1.03, "low": 1.00}
    if not isinstance(level, str):
        return 1.0
    return float(m.get(level.strip().lower(), 1.0))


def work_mode_match(candidate_mode: str, role_mode: str) -> float:
    if not isinstance(candidate_mode, str) or not isinstance(role_mode, str):
        return 0.5
    a = candidate_mode.strip().lower()
    b = role_mode.strip().lower()
    if a == b:
        return 1.0
    # Remote candidates can accept hybrid in many cases
    if a == "remote" and b == "hybrid":
        return 0.75
    if a == "hybrid" and b == "on site":
        return 0.6
    if a == "remote" and b == "on site":
        return 0.35
    return 0.55


def compute_candidate_score(
    candidate: pd.Series,
    role: pd.Series,
    role_required_skills: set[str],
    weights: Dict[str, float],
    today: pd.Timestamp,
) -> Tuple[float, Dict[str, float], str]:
    cand_skills = _parse_skills(candidate.get("skills", ""))
    skill = jaccard(cand_skills, role_required_skills)

    availability = availability_score(
        pd.to_datetime(candidate.get("availability_date"), errors="coerce"),
        pd.to_datetime(role.get("target_start_date"), errors="coerce"),
    )
    freshness = freshness_score(
        pd.to_datetime(candidate.get("last_contacted_date"), errors="coerce"),
        today,
    )
    engage = engagement_score(candidate.get("engagement", ""))
    open_ = openness_score(candidate.get("open_to_roles", ""))
    mode = work_mode_match(candidate.get("preferred_work_mode", ""), role.get("office_requirement", ""))

    # Weighted sum
    parts = {
        "skill_match": skill,
        "availability": availability,
        "freshness": freshness,
        "engagement": engage,
        "openness": open_,
        "work_mode_match": mode,
    }
    total = 0.0
    wsum = 0.0
    for k, v in parts.items():
        w = float(weights.get(k, 0.0))
        total += w * v
        wsum += w

    score = 0.0 if wsum == 0 else (total / wsum)

    # Scarcity boost based on role
    score *= scarcity_multiplier(role.get("scarcity_level", "low"))

    score = clamp01(score)

    # Explanation sentence
    expl = []
    expl.append(f"Skill match {skill:.0%}")
    expl.append(f"Availability {availability:.0%}")
    expl.append(f"Engagement {engage:.0%}")
    expl.append(f"Freshness {freshness:.0%}")
    expl.append(f"Openness {open_:.0%}")
    expl_txt = ", ".join(expl)
    return score, parts, expl_txt


def next_touch_recommendation(score: float, last_contacted: pd.Timestamp, today: pd.Timestamp) -> Tuple[str, int]:
    """
    A simple outreach cadence recommendation.
    Returns label and days until next touch.
    """
    if pd.isna(last_contacted):
        last_contacted = today

    days_since = max(0, int((today - last_contacted).total_seconds() / 86400.0))

    if score >= 0.82:
        cadence = 3
        label = "Prioritize"
    elif score >= 0.65:
        cadence = 7
        label = "Warm follow up"
    elif score >= 0.45:
        cadence = 14
        label = "Nurture"
    else:
        cadence = 30
        label = "Light touch"

    # If we contacted very recently, push next touch forward
    cadence = max(cadence, 1 if days_since >= 1 else cadence)
    return label, cadence
