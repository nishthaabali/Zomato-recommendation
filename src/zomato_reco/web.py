"""Web-facing glue shared by the Streamlit app and the JSON API (no Streamlit/FastAPI imports).

``page_data()`` is everything the page needs that does not depend on a search; ``recommend()`` validates a
request from the page, runs the pipeline and returns the preferences plus the results view. The page itself
(``frontend/src/app.js``) renders exactly this shape, whichever server delivers it.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from zomato_reco import config, llm_client, service, store
from zomato_reco import ui_helpers as ui
from zomato_reco.models import UserPreferences

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _loaded() -> tuple:
    """Load the processed table (building it on first run) plus everything the page needs from it."""
    df = store.get_df()
    meta = store.get_metadata()
    locations, cuisines = store.get_locations(), store.get_cuisines()
    page = {
        "locations": ui.location_choices(locations),
        "cuisines": {"top": ui.top_cuisines(df), "all": cuisines},
        "budgets": ui.budget_options(meta.get("budget_thresholds")),
        "stats": {
            "outlets": ui.round_down_label(len(df), 100),
            "hubs": ui.round_down_label(len(locations), 10),
            "listings": f"{meta.get('raw_rows', len(df)):,}",
        },
        "trending": ui.trending(df),
        "max_extra": config.MAX_EXTRA_CHARS,
        "defaults": dict(ui.DEFAULT_PREFS),
    }
    return df, locations, cuisines, page


@lru_cache(maxsize=1)
def _llm():
    """The Groq client, or None when no API key is configured."""
    return llm_client.get_default_client()


def clear_caches() -> None:
    """Forget the loaded data and LLM client (used by tests)."""
    _loaded.cache_clear()
    _llm.cache_clear()


def ai_info() -> dict:
    llm = _llm()
    if llm is None:
        return {"active": False, "model": "", "engine": "Data-only ranking (no GROQ_API_KEY)"}
    model = str(getattr(llm, "model", "") or config.settings.llm_model).split("/")[-1]
    return {"active": True, "model": f"{model} · Groq", "engine": f"AI ranking: {model}"}


def fallback_reason() -> str:
    if _llm() is None:
        return "No GROQ_API_KEY is configured"
    return "The AI service was unavailable or returned an unusable answer"


def restaurant_count() -> int:
    return len(_loaded()[0])


def page_data() -> dict:
    """The search-independent data for the page. Raises if the dataset cannot be loaded."""
    return {**_loaded()[3], "ai": ai_info()}


def recommend(request: dict) -> dict:
    """Run one search for a request from the page.

    Returns ``{"prefs": <validated preferences>, "view": <results view>}``.
    Raises ValueError for a request the page could not legitimately send.
    """
    df, locations, cuisines, _ = _loaded()
    prefs = ui.parse_request(request, locations, cuisines, config.MAX_EXTRA_CHARS)
    user_prefs = UserPreferences(
        location=ui.location_value(prefs["location"]), budget=prefs["budget"], cuisine=prefs["cuisine"],
        min_rating=prefs["min_rating"], extra=prefs["extra"], top_n=prefs["top_n"],
    )
    resp = service.recommend(user_prefs, df=df, llm=_llm())
    return {"prefs": prefs, "view": ui.response_view(resp, extra=user_prefs.extra, fallback_reason=fallback_reason())}
