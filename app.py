"""Streamlit host for the Bangalore restaurant recommender (local development entry point).

The UI is the Google Stitch design (stitch_bangalore_restaurant_recommender_ui/) rendered by a
``st.components.v2`` component: ``frontend/src/app.js`` holds the markup and behaviour and
``assets/app.css`` is the Tailwind build of the Stitch theme (rebuild with ``npm run build`` in frontend/).
The data and search logic live in ``zomato_reco.web``, shared with the JSON API (``api/main.py``) that
backs the Vercel/Railway deployment (see docs/deployment-plan.md).

Run with:  streamlit run app.py
"""
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st  # noqa: E402

from zomato_reco import ui_helpers as ui  # noqa: E402
from zomato_reco import web  # noqa: E402

log = logging.getLogger("zomato_reco.app")

st.set_page_config(page_title="Restaurant Recommender", page_icon="🍽️", layout="wide")

# Streamlit's own chrome is hidden so the page is exactly the Stitch layout (its header, padding, stale fade).
st.html("""<style>
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
#MainMenu, footer { display: none !important; }
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: #0e0e11; }
[data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: none !important; }
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-stale="true"], .stale-element { opacity: 1 !important; transition: none !important; }
</style>""")

recommender_ui = st.components.v2.component(
    "restaurant_recommender",
    css=(ROOT / "assets" / "app.css").read_text(encoding="utf-8"),
    js=(ROOT / "frontend" / "src" / "app.js").read_text(encoding="utf-8"),
    isolate_styles=True,
)


@st.cache_resource(show_spinner="Preparing restaurant data (the first run downloads the dataset)…")
def load_page_data() -> dict:
    return web.page_data()


# --- Search ---------------------------------------------------------------------------------------------
def run_search(request: dict) -> None:
    """Run a page request through the shared pipeline and store the result in session state."""
    ss = st.session_state
    try:
        result = web.recommend(request)
        ss["prefs"], ss["view"], ss["error"] = result["prefs"], result["view"], False
    except Exception:
        log.exception("Recommendation failed")
        ss["error"] = True


# --- Page ---------------------------------------------------------------------------------------------------
try:
    page = load_page_data()
except Exception:
    log.exception("Could not load restaurant data")
    st.error("The restaurant data could not be loaded. Check your internet connection and run "
             "`python scripts/build_dataset.py`, then reload this page.")
    st.stop()

ss = st.session_state
ss.setdefault("prefs", dict(ui.DEFAULT_PREFS))
ss.setdefault("view", None)
ss.setdefault("error", False)
ss.setdefault("served", 0)  # bumps whenever Python finishes handling a page action

result = recommender_ui(
    key="recommender",
    data={**page, "ai": web.ai_info(), "prefs": ss["prefs"], "view": ss["view"], "error": ss["error"],
          "served": ss["served"]},
    on_submit_change=lambda: None,
    on_reset_change=lambda: None,
)

if result.reset:
    ss.update(prefs=dict(ui.DEFAULT_PREFS), view=None, error=False, served=time.time_ns())
    st.rerun()

# `request` lets tests (and future callers) submit a search without the browser.
request = result.submit or ss.pop("request", None)
if request:
    run_search(request)
    ss["served"] = time.time_ns()
    st.rerun()
