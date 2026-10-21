"""Typed data models shared across the pipeline."""
from __future__ import annotations

import math
import re
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zomato_reco import config

Budget = Literal["low", "medium", "high"]
ANY_CUISINE = {"", "any", "all", "none"}


def _clean_scalar(value: Any) -> Any:
    """Convert pandas/numpy missing values to None and numpy scalars to Python."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value.item() if isinstance(value, np.generic) else value


class UserPreferences(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    location: str = Field(min_length=1)
    budget: Budget
    cuisine: str | None = None            # None = any
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0, allow_inf_nan=False)
    extra: str = ""                       # free text, e.g. "family-friendly, quick service"
    top_n: int = Field(default=config.DEFAULT_TOP_N, ge=1, le=20)
    extra_truncated: bool = False         # set when `extra` exceeded the length cap

    @field_validator("cuisine")
    @classmethod
    def _cuisine_any(cls, v: str | None) -> str | None:
        return None if v is None or v.casefold() in ANY_CUISINE else v

    @model_validator(mode="before")
    @classmethod
    def _normalise_extra(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("extra"), str):
            text = re.sub(r"\s+", " ", data["extra"]).strip()
            data = {
                **data,
                "extra": text[: config.MAX_EXTRA_CHARS],
                "extra_truncated": len(text) > config.MAX_EXTRA_CHARS,
            }
        return data


class Restaurant(BaseModel):
    id: int
    name: str
    address: str = ""
    location: str
    area: str | None = None
    cuisines: list[str] = []
    cost_for_two: int | None = None
    budget_tier: Budget | None = None
    rating: float | None = None
    votes: int = 0
    rest_type: str | None = None
    online_order: bool | None = None
    book_table: bool | None = None
    dishes: list[str] = []

    @classmethod
    def from_row(cls, row: pd.Series | dict) -> "Restaurant":
        data = {k: _clean_scalar(v) for k, v in dict(row).items() if k in cls.model_fields}
        for key in ("cuisines", "dishes"):
            data[key] = list(row[key]) if key in row and row[key] is not None else []
        return cls(**{k: v for k, v in data.items() if v is not None or k in ("cost_for_two", "rating")})


class Recommendation(BaseModel):
    """One LLM-ranked entry; must reference a candidate we sent."""
    rank: int = 10**6                     # a missing rank sorts after explicit ones
    restaurant_id: int
    explanation: str = ""

    @field_validator("explanation", mode="before")
    @classmethod
    def _null_explanation(cls, v: Any) -> Any:
        return "" if v is None else v


class RecommendationResult(BaseModel):
    recommendations: list[Recommendation]
    summary: str | None = None


class RecommendationItem(BaseModel):
    """A recommendation joined with its authoritative dataset row."""
    rank: int
    restaurant: Restaurant
    explanation: str


class RecommendationResponse(BaseModel):
    items: list[RecommendationItem] = []
    summary: str | None = None
    relaxed: list[str] = []               # human-readable notes on relaxed constraints
    notes: list[str] = []                 # other notices, e.g. free text was truncated
    ai_explanations: bool = True          # False when the fallback produced the text
    message: str | None = None            # reason shown when there are no items
    suggestions: list[str] = []           # e.g. close location names

    @classmethod
    def empty(cls, message: str, relaxed: list[str] | None = None, suggestions: list[str] | None = None):
        return cls(message=message, relaxed=relaxed or [], suggestions=suggestions or [], ai_explanations=False)
