"""Headless app tests using Streamlit's AppTest. The LLM and network are always patched out.

The page is a v2 component that AppTest cannot click, so searches are submitted the same way the page's
trigger does, through ``session_state["request"]``, and assertions read the view model the page renders.
"""
import json
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from zomato_reco import llm_client, service, store, web
from zomato_reco import ui_helpers as ui
from zomato_reco.models import RecommendationItem, RecommendationResponse, Restaurant

APP = str(Path(__file__).resolve().parents[1] / "app.py")


class EchoLLM:
    """Ranks the first candidate ids found in the prompt, with a recognisable explanation."""
    model = "openai/test-model"

    def complete(self, system, user, max_tokens=None):
        line = next(l for l in user.splitlines() if l.startswith("[{"))
        cands = json.loads(line)
        recs = [{"rank": i, "restaurant_id": c["id"], "explanation": f"Because {c['name']} fits."}
                for i, c in enumerate(cands, 1)]
        return json.dumps({"recommendations": recs, "summary": "A fine selection."})


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    st.cache_resource.clear()
    web.clear_caches()
    monkeypatch.setattr(llm_client, "get_default_client", lambda: EchoLLM())
    yield
    st.cache_resource.clear()
    web.clear_caches()


def run():
    return AppTest.from_file(APP, default_timeout=120).run()


def search(at=None, **prefs):
    at = at or run()
    at.session_state["request"] = {**ui.DEFAULT_PREFS, "location": "Indiranagar", **prefs}
    return at.run()


def view(at):
    return at.session_state["view"]


def spy(monkeypatch):
    seen = []
    real = service.recommend
    monkeypatch.setattr(service, "recommend", lambda prefs, **k: (seen.append(prefs), real(prefs, **k))[1])
    return seen


def test_initial_render_shows_home_with_defaults():
    at = run()
    assert not at.exception
    assert at.session_state["view"] is None and at.session_state["error"] is False
    assert at.session_state["prefs"] == ui.DEFAULT_PREFS


def test_rendering_alone_does_not_run_the_pipeline(monkeypatch):
    calls = []
    monkeypatch.setattr(service, "recommend", lambda *a, **k: calls.append(1))
    at = run()
    at.run()
    assert calls == [] and not at.exception


def test_search_builds_ranked_cards_with_ai_explanations():
    at = search(cuisine="Italian", min_rating=4.0, top_n=3)
    assert not at.exception
    v = view(at)
    assert 1 <= len(v["items"]) <= 3 and [i["rank"] for i in v["items"]] == list(range(1, len(v["items"]) + 1))
    first = v["items"][0]
    for field in ("name", "location", "cuisines", "rating", "cost", "explanation", "image", "link"):
        assert first[field] is not None, field
    assert first["explanation"].startswith("Because") and "₹" in first["cost"]
    assert v["summary"] == "A fine selection." and v["ai_explanations"] is True and not at.session_state["error"]
    assert at.session_state["prefs"]["cuisine"] == "Italian"   # the page shows what was searched


def test_cuisine_is_optional_and_search_runs_without_it(monkeypatch):
    seen = spy(monkeypatch)
    at = search(cuisine=None)
    assert not at.exception and seen[0].cuisine is None and view(at)["items"]


def test_selected_preferences_are_passed_through(monkeypatch):
    seen = spy(monkeypatch)
    search(cuisine="Italian", budget="high", min_rating=4.0, top_n=7, extra="  rooftop  ")
    p = seen[0]
    assert (p.location, p.cuisine, p.budget, p.min_rating, p.top_n, p.extra) == ("Indiranagar", "Italian", "high", 4.0, 7, "rooftop")


def test_all_bangalore_maps_to_the_whole_city(monkeypatch):
    seen = spy(monkeypatch)
    search(location=ui.ALL_CITY_LABEL)
    assert seen[0].location == "Bangalore"


def test_page_data_comes_from_the_dataset():
    at = run()
    assert not at.exception
    locations = store.get_locations()
    assert "Indiranagar" in locations and "Italian" in store.get_cuisines()
    trending = ui.trending(store.get_df())
    assert trending[ui.ALL_CITY_LABEL] and trending[ui.ALL_CITY_LABEL][0]["rating"]


def test_no_api_key_shows_data_based_notice(monkeypatch):
    monkeypatch.setattr(llm_client, "get_default_client", lambda: None)
    at = search()
    v = view(at)
    assert not at.exception and v["items"]  # still shows results
    assert v["ai_explanations"] is False and "GROQ_API_KEY" in v["fallback_reason"]
    assert v["items"][0]["why_label"] == "About this pick:"


def _fake_response(**kw):
    r = Restaurant(id=1, name="Test **Bold** $Cafe$", location="BTM", cuisines=["Cafe"], rating=None, cost_for_two=None)
    return RecommendationResponse(
        items=[RecommendationItem(rank=1, restaurant=r, explanation="Plain <b>html</b> & [link](http://x)")], **kw)


def test_missing_rating_and_cost_render_safely(monkeypatch):
    monkeypatch.setattr(service, "recommend", lambda *a, **k: _fake_response())
    item = view(search())["items"][0]
    assert item["rating"] is None and item["cost"] == "Not available" and item["votes"] == ""
    assert item["name"] == "Test **Bold** $Cafe$" and item["explanation"] == "Plain <b>html</b> & [link](http://x)"


def test_relaxation_and_fallback_notices_are_passed_to_the_page(monkeypatch):
    monkeypatch.setattr(service, "recommend", lambda *a, **k: _fake_response(relaxed=["Cuisine filter 'X' dropped"], ai_explanations=False))
    v = view(search())
    assert v["relaxed"] == ["Cuisine filter 'X' dropped"]
    assert v["ai_explanations"] is False and v["fallback_reason"].startswith("The AI service was unavailable")


def test_empty_result_message_and_suggestions(monkeypatch):
    resp = RecommendationResponse.empty("Location 'Indiranagr' was not found in the data.", suggestions=["Indiranagar"])
    monkeypatch.setattr(service, "recommend", lambda *a, **k: resp)
    v = view(search())
    assert v["items"] == [] and "not found" in v["message"] and v["suggestions"] == ["Indiranagar"]


def test_unexpected_error_sets_error_flag_without_leaking_details(monkeypatch):
    at = search()
    previous = view(at)

    def boom(*a, **k):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(service, "recommend", boom)
    at = search(at)
    assert not at.exception  # handled, not raised to the page
    assert at.session_state["error"] is True
    assert view(at) == previous  # earlier results stay on screen
    assert "secret internal detail" not in json.dumps(view(at))


def test_invalid_request_is_rejected_before_the_pipeline(monkeypatch):
    calls = []
    monkeypatch.setattr(service, "recommend", lambda *a, **k: calls.append(1))
    at = search(location="Atlantis")
    assert not at.exception and calls == [] and at.session_state["error"] is True


def test_each_handled_request_bumps_served_id():
    at = run()
    before = at.session_state["served"]
    at = search(at)
    assert at.session_state["served"] != before


def test_results_persist_across_reruns():
    at = search()
    first = view(at)
    at.run()  # e.g. a widget-free rerun
    assert view(at) == first and first["items"]
