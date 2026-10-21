"""Turn the raw Zomato dataframe into a clean, query-ready restaurant table.

Findings from profiling the raw data (see architecture.md section 5.1):
- Bangalore only. `location` is a neighbourhood (93 values); `listed_in(city)` is a
  coarser area (30 values) and is used as a fallback when `location` is missing.
- The same restaurant is repeated once per listing type, so rows are de-duplicated
  on (name, address), keeping the row with the most votes.
- Ratings look like "4.1 /5", "NEW" or "-"; costs like "1,200".
- Some names carry double-encoded text ("CafÃ©"), repaired by `fix_mojibake`.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from zomato_reco import config
from zomato_reco.ingestion.loader import DataError

SCHEMA_VERSION = 1

RAW_COLUMNS = {
    "name": "name",
    "address": "address",
    "location": "location",
    "listed_in(city)": "area",
    "cuisines": "cuisines",
    "approx_cost(for two people)": "cost_for_two",
    "rate": "rating",
    "votes": "votes",
    "rest_type": "rest_type",
    "online_order": "online_order",
    "book_table": "book_table",
    "dish_liked": "dishes",
}

OUTPUT_COLUMNS = [
    "id", "name", "address", "location", "area", "cuisines", "cost_for_two",
    "budget_tier", "rating", "votes", "rest_type", "online_order", "book_table", "dishes",
]

_RATING_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*/\s*5\s*$")
_MAX_DISHES = 5


# --- Value parsers ------------------------------------------------------------
def parse_rating(value) -> float | None:
    """'4.1/5' or '4.1 /5' -> 4.1. 'NEW', '-', blanks and out-of-range -> None."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    m = _RATING_RE.match(text)
    if m:
        number = float(m.group(1))
    else:
        try:
            number = float(text)
        except ValueError:
            return None
    return number if 0 <= number <= 5 else None


def parse_cost(value) -> int | None:
    """'1,200' -> 1200. Non-numeric, zero and negative -> None."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = re.sub(r"[,\s₹]|rs\.?", "", str(value), flags=re.IGNORECASE)
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    number = int(float(text))
    return number if number > 0 else None


def fix_mojibake(text: str) -> str:
    """Repair text that was UTF-8 decoded as latin-1 one or more times."""
    for _ in range(8):
        try:
            repaired = text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if repaired == text:
            break
        text = repaired
    return text


def clean_text(value) -> str | None:
    """Repair encoding, collapse whitespace; blank -> None."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = re.sub(r"\s+", " ", fix_mojibake(str(value))).strip()
    return text or None


def split_list(value, limit: int | None = None) -> list[str]:
    """'North Indian, Chinese, north indian' -> ['North Indian', 'Chinese'].

    Items are trimmed and de-duplicated case-insensitively; original casing is kept
    for display (matching is done case-insensitively downstream).
    """
    text = clean_text(value)
    if not text:
        return []
    seen, out = set(), []
    for part in text.split(","):
        item = part.strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            out.append(item)
    return out[:limit] if limit else out


def parse_yes_no(value) -> bool | None:
    text = str(value).strip().lower() if value is not None else ""
    return True if text == "yes" else False if text == "no" else None


# --- Budget tiers -----------------------------------------------------------------
def budget_thresholds(costs: pd.Series, quantiles=config.BUDGET_QUANTILES) -> tuple[int, int]:
    """Upper cost bounds for the 'low' and 'medium' tiers, from data quantiles."""
    valid = costs.dropna()
    if valid.empty:
        raise DataError("No valid costs available to derive budget tiers")
    low, medium = (int(valid.quantile(q)) for q in quantiles)
    return low, medium


def assign_budget_tier(cost, low_max: int, medium_max: int) -> str | None:
    if cost is None or pd.isna(cost):
        return None
    if cost <= low_max:
        return "low"
    return "medium" if cost <= medium_max else "high"


# --- Main pipeline ------------------------------------------------------------------
def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean the raw dataframe. Returns (table, metadata)."""
    missing = [c for c in RAW_COLUMNS if c not in raw.columns]
    if missing:
        raise DataError(f"Raw dataset is missing expected columns: {missing}")

    df = raw[list(RAW_COLUMNS)].rename(columns=RAW_COLUMNS).copy()
    stats = {"raw_rows": len(df)}

    df["name"] = df["name"].map(clean_text)
    df["address"] = df["address"].map(clean_text)
    df["area"] = df["area"].map(clean_text)
    df["location"] = df["location"].map(clean_text).fillna(df["area"])
    df["rating"] = df["rating"].map(parse_rating)
    df["cost_for_two"] = df["cost_for_two"].map(parse_cost).astype("Int64")
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    df["cuisines"] = df["cuisines"].map(split_list)
    df["dishes"] = df["dishes"].map(lambda v: split_list(v, limit=_MAX_DISHES))
    df["rest_type"] = df["rest_type"].map(clean_text)
    df["online_order"] = df["online_order"].map(parse_yes_no)
    df["book_table"] = df["book_table"].map(parse_yes_no)

    # Drop unusable rows.
    df = df[df["name"].notna() & df["location"].notna()]
    df = df[df["rating"].notna() | df["cost_for_two"].notna()]
    stats["after_drop_unusable"] = len(df)

    # The same restaurant is listed once per listing type: keep the most-voted row.
    df["address"] = df["address"].fillna("")
    df = (
        df.sort_values(["votes", "rating"], ascending=False, na_position="last")
        .drop_duplicates(["name", "address"], keep="first")
        .sort_values(["name", "address"])
        .reset_index(drop=True)
    )
    stats["restaurants"] = len(df)
    if df.empty:
        raise DataError("No rows left after cleaning")

    df["id"] = np.arange(1, len(df) + 1)  # stable: ordered by (name, address)

    low_max, medium_max = budget_thresholds(df["cost_for_two"])
    df["budget_tier"] = df["cost_for_two"].map(lambda c: assign_budget_tier(c, low_max, medium_max))

    df = df[OUTPUT_COLUMNS]
    meta = {
        "schema_version": SCHEMA_VERSION,
        "dataset": config.HF_DATASET_ID,
        "budget_thresholds": {"low_max": low_max, "medium_max": medium_max},
        **stats,
    }
    return df, meta
