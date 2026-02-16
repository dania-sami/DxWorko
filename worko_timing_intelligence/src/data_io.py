from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_demo_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    roles = pd.read_csv(data_dir / "sample_roles.csv")
    candidates = pd.read_csv(data_dir / "sample_candidates.csv")
    return roles, candidates
