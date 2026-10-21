"""Pure view-model helpers for the UI (no Streamlit import, so they are unit-testable).

The page itself is the Stitch design rendered by ``frontend/src/app.js``; these functions turn the dataset,
the user's request and the recommendation response into the plain JSON that the page renders.
"""
from __future__ import annotations

import math
from urllib.parse import quote_plus

import pandas as pd

from zomato_reco.models import RecommendationResponse, Restaurant

ALL_CITY_LABEL = "All Bangalore"
ANY_CUISINE_LABEL = "Any cuisine"
NOT_AVAILABLE = "Not available"
MAX_CUISINES_SHOWN = 4
TOP_CUISINE_PILLS = 6          # pills shown next to "Any Cuisine"; the rest sit behind "+ N more"
TRENDING_PER_LOCATION = 3
TRENDING_MIN_VOTES = 20        # ignore barely-reviewed places in the "Top rated around" shelf
IMAGE_BASE = "app/static/img"  # Streamlit static serving (server.enableStaticServing)

DEFAULT_PREFS = {"location": ALL_CITY_LABEL, "budget": "medium", "cuisine": None,
                 "min_rating": 3.5, "top_n": 5, "extra": ""}

# Representative photos from the Stitch design, chosen by cuisine / restaurant type keywords (first match wins).
_IMAGE_RULES = [
    ("brewpub-rooftop", ("microbrewery", "pub", "bar", "lounge", "club")),
    ("gelato-garden", ("ice cream", "desserts", "dessert parlor", "juices")),
    ("woodfired-pizza", ("pizza", "italian")),
    ("south-indian", ("south indian", "kerala", "andhra", "chettinad", "udupi", "mangalorean")),
    ("pan-asian", ("chinese", "asian", "thai", "japanese", "momos", "korean", "sushi", "tibetan", "burmese", "vietnamese")),
    ("colonial-bakery", ("bakery", "cafe", "beverages")),
    ("candlelit-deli", ("continental", "european", "mediterranean", "french", "american", "fine dining")),
]
_FALLBACK_IMAGES = ["brewpub-interior", "candlelit-deli", "colonial-bakery"]


# --- Formatting --------------------------------------------------------------------------------------------
def format_cost(cost: int | None) -> str:
    return f"₹{cost:,} for two" if cost else NOT_AVAILABLE


def format_cuisines(cuisines: list[str]) -> str:
    if not cuisines:
        return NOT_AVAILABLE
    shown = ", ".join(cuisines[:MAX_CUISINES_SHOWN])
    extra = len(cuisines) - MAX_CUISINES_SHOWN
    return shown + (f" +{extra} more" if extra > 0 else "")


def round_down_label(n: int, step: int) -> str:
    """12,438 -> '12,400+' (the Stitch stats ribbon style); small numbers are shown exactly."""
    if n < step:
        return f"{n:,}"
    return f"{n // step * step:,}+"


def location_choices(locations: list[str]) -> list[str]:
    return [ALL_CITY_LABEL, *locations]


def location_value(choice: str) -> str:
    return "Bangalore" if choice == ALL_CITY_LABEL else choice


def cuisine_value(choice: str | None) -> str | None:
    """An empty selection (None) or the 'Any cuisine' label both mean no cuisine filter."""
    return None if not choice or choice == ANY_CUISINE_LABEL else choice


def budget_options(thresholds: dict | None) -> list[dict]:
    """The three budget tiers with the rupee ranges shown on the segmented control and filter chip."""
    if not thresholds:
        return [{"value": v, "label": v.title(), "range": "", "chip": f"Budget: {v.title()}"} for v in ("low", "medium", "high")]
    low, med = thresholds["low_max"], thresholds["medium_max"]
    return [
        {"value": "low", "label": "Low", "range": f"Up to ₹{low:,}", "chip": f"Budget: ≤₹{low:,}"},
        {"value": "medium", "label": "Medium", "range": f"₹{low + 1:,} - ₹{med:,}", "chip": f"Budget: ₹{low + 1:,}–₹{med:,}"},
        {"value": "high", "label": "High", "range": f"₹{med + 1:,}+", "chip": f"Budget: ₹{med + 1:,}+"},
    ]


def top_cuisines(df: pd.DataFrame, n: int = TOP_CUISINE_PILLS) -> list[str]:
    """The n most common cuisines in the data, for the quick-pick pills."""
    return df["cuisines"].explode().dropna().value_counts().head(n).index.tolist()


# --- Requests from the page -----------------------------------------------------------------------------------
def parse_request(payload: dict, locations: list[str], cuisines: list[str], max_extra: int) -> dict:
    """Validate a search request sent by the page and return clean UI preferences.

    Raises ValueError for anything the page could not legitimately send.
    """
    if not isinstance(payload, dict):
        raise ValueError("request must be an object")
    location = payload.get("location")
    if location not in location_choices(locations):
        raise ValueError(f"unknown location: {location!r}")
    budget = payload.get("budget")
    if budget not in ("low", "medium", "high"):
        raise ValueError(f"unknown budget: {budget!r}")
    cuisine = cuisine_value(payload.get("cuisine"))
    if cuisine is not None and cuisine not in cuisines:
        raise ValueError(f"unknown cuisine: {cuisine!r}")
    try:
        min_rating = float(payload.get("min_rating", DEFAULT_PREFS["min_rating"]))
        top_n = int(payload.get("top_n", DEFAULT_PREFS["top_n"]))
    except (TypeError, ValueError) as exc:
        raise ValueError("rating and result count must be numbers") from exc
    if not math.isfinite(min_rating):
        raise ValueError("rating must be finite")
    extra = payload.get("extra") or ""
    if not isinstance(extra, str):
        raise ValueError("extra must be text")
    return {
        "location": location, "budget": budget, "cuisine": cuisine,
        "min_rating": min(max(round(min_rating * 2) / 2, 0.0), 5.0),
        "top_n": min(max(top_n, 3), 10),
        "extra": " ".join(extra.split())[:max_extra],
    }


# --- Restaurants ---------------------------------------------------------------------------------------------
def _image_candidates(cuisines: list[str], rest_type: str | None, rid: int) -> list[str]:
    """All Stitch photos, best keyword match first."""
    text = " ".join([*(c.lower() for c in cuisines), (rest_type or "").lower()])
    matched = [name for name, words in _IMAGE_RULES if any(w in text for w in words)]
    start = rid % len(_FALLBACK_IMAGES)
    fallback = _FALLBACK_IMAGES[start:] + _FALLBACK_IMAGES[:start]
    others = [name for name, _ in _IMAGE_RULES]
    return list(dict.fromkeys(matched + fallback + others))


def image_for(cuisines: list[str], rest_type: str | None, rid: int, used: set[str] | None = None) -> str:
    """A representative Stitch photo for a restaurant, picked by cuisine/type keywords.

    With `used`, photos already shown in the same list are skipped while unused ones remain.
    """
    candidates = _image_candidates(cuisines, rest_type, rid)
    name = next((c for c in candidates if c not in (used or ())), candidates[0])
    if used is not None:
        used.add(name)
    return f"{IMAGE_BASE}/{name}.jpg"


def search_link(r: Restaurant) -> str:
    return "https://www.google.com/search?q=" + quote_plus(f"{r.name} {r.location} Bangalore site:zomato.com")


def _types(r: Restaurant) -> list[str]:
    return [t.strip() for t in (r.rest_type or "").split(",") if t.strip()][:2]


def _feature(r: Restaurant) -> dict | None:
    if r.book_table:
        return {"icon": "table_bar", "text": "Table booking"}
    if r.online_order:
        return {"icon": "delivery_dining", "text": "Online ordering"}
    return None


def _footer_left(r: Restaurant) -> dict:
    if r.dishes:
        return {"icon": "restaurant", "text": "Known for: " + " & ".join(r.dishes[:2])}
    if r.book_table:
        return {"icon": "table_bar", "text": "Table booking available"}
    if r.online_order:
        return {"icon": "delivery_dining", "text": "Online ordering available"}
    if r.votes:
        return {"icon": "check_circle", "text": f"Rated by {r.votes:,} Zomato diners"}
    return {"icon": "check_circle", "text": "Listed on Zomato"}


def _footer_right(r: Restaurant, left: dict) -> str:
    """A second, different fact for the card's footer line."""
    options = []
    if r.book_table and left["icon"] != "table_bar":
        options.append("Table booking available")
    if r.online_order and left["icon"] != "delivery_dining":
        options.append("Online ordering available")
    if r.area and r.area != r.location:
        options.append(f"Area: {r.area}")
    if r.rest_type and len(_types(r)) < len([t for t in r.rest_type.split(",") if t.strip()]):
        options.append(r.rest_type)
    return options[0] if options else ""


def badges(restaurants: list[Restaurant]) -> dict[int, dict]:
    """Data-backed highlight badges for the non-top picks: best value, most reviewed, highest rated."""
    rest = restaurants[1:]
    out: dict[int, dict] = {}

    def award(key, text, tone, candidates):
        candidates = [r for r in candidates if r.id not in out]
        if not candidates:
            return
        best = max(candidates, key=key)
        if sum(1 for r in candidates if key(r) == key(best)) == 1:   # only when it clearly stands out
            out[best.id] = {"text": text, "tone": tone}

    award(lambda r: -r.cost_for_two, "Best Value", "tertiary", [r for r in rest if r.cost_for_two])
    award(lambda r: r.votes, "Most Reviewed", "secondary", [r for r in rest if r.votes])
    award(lambda r: r.rating, "Highest Rated", "secondary", [r for r in rest if r.rating is not None])
    for r in rest:
        if r.id not in out and r.book_table:
            out[r.id] = {"text": "Table Booking", "tone": "neutral"}
    return out


def _why_label(rank: int, ai: bool, extra: str) -> str:
    if not ai:
        return "About this pick:"
    if rank == 1 and extra and "," not in extra and len(extra) <= 28:
        return f"Why this fits your {extra.lower()}:"
    return "Why this fits you:"


def response_view(resp: RecommendationResponse, extra: str = "", fallback_reason: str = "") -> dict:
    """Everything the results screen shows, as plain JSON-able data."""
    restaurants = [i.restaurant for i in resp.items]
    badge_map = badges(restaurants)
    used_images: set[str] = set()
    items = []
    for item in resp.items:
        r = item.restaurant
        left = _footer_left(r)
        items.append({
            "id": r.id, "rank": item.rank, "name": r.name, "location": r.location,
            "types": _types(r), "feature": _feature(r),
            "cuisines": format_cuisines(r.cuisines), "cost": format_cost(r.cost_for_two),
            "rating": None if r.rating is None else f"{r.rating:.1f}",
            "votes": f"{r.votes:,}" if r.votes else "",
            "badge": badge_map.get(r.id), "image": image_for(r.cuisines, r.rest_type, r.id, used_images),
            "link": search_link(r),
            "why_label": _why_label(item.rank, resp.ai_explanations, extra), "explanation": item.explanation,
            "footer_left": left, "footer_right": _footer_right(r, left),
        })
    return {
        "items": items, "summary": resp.summary, "ai_explanations": resp.ai_explanations,
        "relaxed": list(resp.relaxed), "notes": list(resp.notes), "message": resp.message,
        "suggestions": list(resp.suggestions), "fallback_reason": fallback_reason,
    }


def _trending_card(row, index: int, used: set[str]) -> dict:
    cuisines = [str(c) for c in row.cuisines]
    dishes = [str(d) for d in row.dishes][:3]
    kind = row.rest_type or "Restaurant"
    blurb = f"{kind} known for {', '.join(dishes)}." if dishes else f"{kind} serving {format_cuisines(cuisines)}."
    return {
        "name": row.name, "rating": f"{row.rating:.1f}", "cost": format_cost(None if pd.isna(row.cost_for_two) else int(row.cost_for_two)),
        "tag": cuisines[0] if cuisines else kind, "tag_tone": "secondary" if index == 1 else "primary",
        "blurb": blurb, "votes": f"{int(row.votes):,} Zomato votes", "location": row.location,
        "image": image_for(cuisines, row.rest_type, int(row.id), used),
    }


def trending(df: pd.DataFrame) -> dict[str, list[dict]]:
    """Top-rated, well-reviewed restaurants per location (plus city-wide), for the home screen shelf."""
    rated = df[df["rating"].notna() & (df["votes"] >= TRENDING_MIN_VOTES)]
    rated = rated.sort_values(["rating", "votes"], ascending=False)

    def top(frame: pd.DataFrame) -> list[dict]:
        frame = frame.drop_duplicates("name").head(TRENDING_PER_LOCATION)
        used: set[str] = set()
        return [_trending_card(row, i, used) for i, row in enumerate(frame.itertuples())]

    out = {ALL_CITY_LABEL: top(rated)}
    for loc, group in rated.groupby("location", sort=False):
        out[str(loc)] = top(group)
    return out
