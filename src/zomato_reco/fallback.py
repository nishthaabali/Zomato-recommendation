"""Non-LLM ranking and templated explanations, used when the LLM is unavailable."""
from __future__ import annotations

import pandas as pd

from zomato_reco.models import Recommendation, RecommendationResult


def describe(row: pd.Series | dict) -> str:
    """One templated sentence built only from dataset fields; omits missing values."""
    cuisines = [c for c in row["cuisines"]][:3]
    rest_type = row.get("rest_type")
    rest_type = None if pd.isna(rest_type) else rest_type

    what = (rest_type or "restaurant").lower()
    if cuisines:
        what += f" serving {', '.join(cuisines)}"
    parts = [f"{row['name']} is a {what} in {row['location']}."]

    rating = row.get("rating")
    votes = int(row.get("votes") or 0)
    if not pd.isna(rating):
        parts.append(f"Rated {rating:.1f}/5" + (f" from {votes:,} votes." if votes else "."))
    else:
        parts.append("Not rated yet.")

    cost = row.get("cost_for_two")
    if not pd.isna(cost):
        parts.append(f"About ₹{int(cost):,} for two.")
    return " ".join(parts)


def rank(candidates: pd.DataFrame, top_n: int) -> RecommendationResult:
    """Top-N candidates in pre-score order (already sorted by filtering.select)."""
    recs = [
        Recommendation(rank=i, restaurant_id=int(row["id"]), explanation=describe(row))
        for i, (_, row) in enumerate(candidates.head(top_n).iterrows(), start=1)
    ]
    return RecommendationResult(recommendations=recs, summary=None)
