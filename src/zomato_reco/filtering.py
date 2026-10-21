"""Deterministic candidate selection: hard filters, pre-scoring and relaxation.

The LLM only ever sees the (at most K) candidates returned here.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from zomato_reco import config
from zomato_reco.models import UserPreferences

# The whole dataset is Bangalore, so these mean "no location filter".
CITY_ALIASES = {"bangalore", "bengaluru", "bengalooru"}

# Budget tiers allowed after "widen budget": low->low+medium, medium->all, high->medium+high.
WIDER_BUDGET = {
    "low": ("low", "medium"),
    "medium": ("low", "medium", "high"),
    "high": ("medium", "high"),
}

RATING_STEP = 0.5
MAX_RATING_RELAXATIONS = 2
BAYES_MIN_VOTES = 50  # votes needed before a restaurant's own rating outweighs the global mean


@dataclass
class Selection:
    candidates: pd.DataFrame
    relaxed: list[str] = field(default_factory=list)
    reason: str | None = None            # why the result is empty
    suggestions: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return self.candidates.empty


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().casefold()


def pre_score(df: pd.DataFrame, prior: float | None = None, min_votes: int = BAYES_MIN_VOTES) -> pd.Series:
    """Votes-weighted rating (Bayesian average). Unrated restaurants score lowest.

    A 5.0 with 3 votes is pulled toward the prior (the mean rating, by default of
    `df` itself), so it does not outrank a 4.5 with 2,000 votes.
    """
    if prior is None:
        rated = df["rating"].dropna()
        prior = rated.mean() if not rated.empty else 0.0
    votes = df["votes"].fillna(0).clip(lower=0)
    score = (votes / (votes + min_votes)) * df["rating"] + (min_votes / (votes + min_votes)) * prior
    return score.fillna(-1.0)


def _location_mask(df: pd.DataFrame, location: str) -> pd.Series:
    if norm(location) in CITY_ALIASES:
        return pd.Series(True, index=df.index)
    return df["location"].map(norm) == norm(location)


def _hard_filter(df, location_mask, budgets, cuisine, min_rating) -> pd.DataFrame:
    mask = location_mask & df["budget_tier"].isin(budgets)
    if cuisine:
        wanted = norm(cuisine)
        mask &= df["cuisines"].map(lambda cs: any(norm(c) == wanted for c in cs))
    if min_rating > 0:
        mask &= df["rating"] >= min_rating  # NaN compares False, so unrated are excluded
    return df[mask]


def _rank(df: pd.DataFrame, limit: int, prior: float) -> pd.DataFrame:
    out = df.assign(pre_score=pre_score(df, prior))
    return out.sort_values(["pre_score", "votes", "id"], ascending=[False, False, True]).head(limit)


def select(df: pd.DataFrame, prefs: UserPreferences, limit: int | None = None) -> Selection:
    """Return up to `limit` ranked candidates, relaxing constraints if none match.

    Relaxation order (cumulative): drop cuisine -> widen budget -> lower min rating
    (at most MAX_RATING_RELAXATIONS steps). The input frame is never mutated.
    """
    limit = limit or config.settings.candidate_limit
    location_mask = _location_mask(df, prefs.location)

    if not location_mask.any():
        names = {norm(loc): loc for loc in df["location"].dropna().unique()}
        close = difflib.get_close_matches(norm(prefs.location), names, n=3, cutoff=0.6)
        return Selection(
            candidates=df.iloc[0:0],
            reason=f"Location '{prefs.location}' was not found in the data.",
            suggestions=[names[c] for c in close],
        )

    budgets = (prefs.budget,)
    cuisine = prefs.cuisine
    min_rating = prefs.min_rating
    relaxed: list[str] = []

    def attempt() -> pd.DataFrame:
        return _hard_filter(df, location_mask, budgets, cuisine, min_rating)

    found = attempt()

    if found.empty and cuisine:
        relaxed.append(f"Cuisine filter '{cuisine}' dropped (no exact matches)")
        cuisine = None
        found = attempt()

    if found.empty:
        budgets = WIDER_BUDGET[prefs.budget]
        relaxed.append(f"Budget widened from {prefs.budget} to {' / '.join(budgets)}")
        found = attempt()

    steps = 0
    while found.empty and min_rating > 0 and steps < MAX_RATING_RELAXATIONS:
        new_rating = max(0.0, round(min_rating - RATING_STEP, 1))
        relaxed.append(f"Minimum rating lowered from {min_rating:g} to {new_rating:g}")
        min_rating = new_rating
        steps += 1
        found = attempt()

    if found.empty:
        return Selection(
            candidates=found,
            relaxed=relaxed,
            reason="No restaurants matched your preferences, even after relaxing them.",
        )
    # The prior comes from the whole table so a score doesn't depend on which filters ran.
    prior = df["rating"].mean()
    return Selection(candidates=_rank(found, limit, prior).reset_index(drop=True), relaxed=relaxed)
