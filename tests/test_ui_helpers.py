import pytest

from tests.helpers import sample_df
from zomato_reco import ui_helpers as ui
from zomato_reco.models import RecommendationItem, RecommendationResponse, Restaurant

LOCATIONS = ["BTM", "Indiranagar"]
CUISINES = ["Cafe", "Italian"]


@pytest.mark.parametrize("cost,expected", [(1200, "₹1,200 for two"), (300, "₹300 for two"), (None, "Not available"), (0, "Not available")])
def test_format_cost(cost, expected):
    assert ui.format_cost(cost) == expected


def test_format_cuisines_truncates_long_lists():
    assert ui.format_cuisines([]) == "Not available"
    assert ui.format_cuisines(["A", "B"]) == "A, B"
    assert ui.format_cuisines(list("ABCDEFG")) == "A, B, C, D +3 more"


def test_round_down_label_matches_the_stats_ribbon_style():
    assert ui.round_down_label(12438, 100) == "12,400+"
    assert ui.round_down_label(93, 10) == "90+"
    assert ui.round_down_label(7, 10) == "7"


def test_budget_options_show_rupee_ranges():
    low, med, high = ui.budget_options({"low_max": 300, "medium_max": 500})
    assert [b["value"] for b in (low, med, high)] == ["low", "medium", "high"]
    assert low["range"] == "Up to ₹300" and med["range"] == "₹301 - ₹500" and high["range"] == "₹501+"
    assert med["chip"] == "Budget: ₹301–₹500"
    assert [b["label"] for b in ui.budget_options(None)] == ["Low", "Medium", "High"]


def test_location_and_cuisine_mapping():
    assert ui.location_choices(["BTM"])[0] == ui.ALL_CITY_LABEL
    assert ui.location_value(ui.ALL_CITY_LABEL) == "Bangalore" and ui.location_value("BTM") == "BTM"
    assert ui.cuisine_value(ui.ANY_CUISINE_LABEL) is None and ui.cuisine_value("Italian") == "Italian"
    assert ui.cuisine_value(None) is None and ui.cuisine_value("") is None  # empty selection = optional


def test_top_cuisines_orders_by_frequency():
    assert ui.top_cuisines(sample_df(), 2) == ["Italian", "Cafe"]


def _req(**kw):
    return {**ui.DEFAULT_PREFS, "location": "BTM", **kw}


def test_parse_request_normalises_values():
    out = ui.parse_request(_req(min_rating="4.2", top_n=50, extra="  quiet   place ", cuisine=""), LOCATIONS, CUISINES, 300)
    assert out == {"location": "BTM", "budget": "medium", "cuisine": None, "min_rating": 4.0, "top_n": 10, "extra": "quiet place"}
    assert ui.parse_request(_req(min_rating=-3, top_n=1), LOCATIONS, CUISINES, 300)["top_n"] == 3
    assert ui.parse_request(_req(location=ui.ALL_CITY_LABEL), LOCATIONS, CUISINES, 300)["location"] == ui.ALL_CITY_LABEL
    assert len(ui.parse_request(_req(extra="x" * 500), LOCATIONS, CUISINES, 300)["extra"]) == 300


@pytest.mark.parametrize("bad", [
    {"location": "Atlantis"}, {"budget": "lavish"}, {"cuisine": "Martian"},
    {"min_rating": "high"}, {"min_rating": float("nan")}, {"top_n": None}, {"extra": ["list"]},
])
def test_parse_request_rejects_what_the_page_cannot_send(bad):
    with pytest.raises(ValueError):
        ui.parse_request(_req(**bad), LOCATIONS, CUISINES, 300)
    with pytest.raises(ValueError):
        ui.parse_request("not a dict", LOCATIONS, CUISINES, 300)


def test_image_for_matches_keywords_and_avoids_repeats():
    assert ui.image_for(["South Indian"], "Quick Bites", 1).endswith("/south-indian.jpg")
    assert ui.image_for(["Desserts"], "Dessert Parlor", 1).endswith("/gelato-garden.jpg")
    used: set[str] = set()
    picks = [ui.image_for(["Desserts"], "Dessert Parlor", i, used) for i in range(8)]
    assert len(set(picks)) == 8 and picks[0].endswith("/gelato-garden.jpg")
    assert ui.image_for(["Desserts"], None, 9, used).startswith(ui.IMAGE_BASE)  # all used: still a valid photo


def _item(rank, **kw):
    base = dict(id=rank, name=f"R{rank}", location="BTM", cuisines=["Cafe"], rating=4.0, votes=100, cost_for_two=400)
    return RecommendationItem(rank=rank, restaurant=Restaurant(**{**base, **kw}), explanation=f"Because {rank}")


def test_badges_highlight_clear_winners_only():
    items = [_item(1), _item(2, cost_for_two=200), _item(3, votes=5000), _item(4, rating=4.8), _item(5, book_table=True)]
    b = ui.badges([i.restaurant for i in items])
    assert 1 not in b  # the top pick has its own badge
    assert b[2]["text"] == "Best Value" and b[3]["text"] == "Most Reviewed" and b[4]["text"] == "Highest Rated"
    assert b[5]["text"] == "Table Booking"
    assert ui.badges([i.restaurant for i in [_item(1), _item(2), _item(3)]]) == {}  # ties: nothing stands out


def test_response_view_carries_every_card_field():
    resp = RecommendationResponse(items=[_item(1, dishes=["Dosa", "Vada"], rest_type="Cafe, Bakery"), _item(2, rating=None, votes=0)],
                                  summary="Nice picks", relaxed=["Cuisine dropped"])
    v = ui.response_view(resp, extra="Date night")
    first, second = v["items"]
    assert first["rank"] == 1 and first["cost"] == "₹400 for two" and first["rating"] == "4.0" and first["votes"] == "100"
    assert first["why_label"] == "Why this fits your date night:" and first["explanation"] == "Because 1"
    assert first["types"] == ["Cafe", "Bakery"] and first["footer_left"]["text"] == "Known for: Dosa & Vada"
    assert first["link"].startswith("https://www.google.com/search?q=") and first["image"] != second["image"]
    assert second["rating"] is None and second["votes"] == "" and second["why_label"] == "Why this fits you:"
    assert v["summary"] == "Nice picks" and v["relaxed"] == ["Cuisine dropped"] and v["ai_explanations"] is True


def test_response_view_labels_fallback_text_honestly():
    resp = RecommendationResponse(items=[_item(1)], ai_explanations=False)
    v = ui.response_view(resp, fallback_reason="No GROQ_API_KEY is configured")
    assert v["items"][0]["why_label"] == "About this pick:" and v["fallback_reason"].startswith("No GROQ_API_KEY")


def test_response_view_keeps_hostile_text_as_plain_data():
    """The page escapes every string; the view must pass text through unchanged, never pre-rendered HTML."""
    resp = RecommendationResponse(items=[_item(1, name="<img src=x onerror=alert(1)>")])
    assert ui.response_view(resp)["items"][0]["name"] == "<img src=x onerror=alert(1)>"


def test_trending_lists_top_rated_per_location():
    t = ui.trending(sample_df())
    city = t[ui.ALL_CITY_LABEL]
    assert [c["name"] for c in city] == ["Zeta Medium", "Alpha Pizzeria", "Beta Bistro"]
    assert city[0]["rating"] == "4.9" and city[0]["votes"] == "2,000 Zomato votes" and city[0]["cost"] == "₹450 for two"
    assert "Margherita" in city[1]["blurb"] and len({c["image"] for c in city}) == 3
    assert set(t) == {ui.ALL_CITY_LABEL, "BTM"}
