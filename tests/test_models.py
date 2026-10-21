import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from zomato_reco import config
from zomato_reco.models import Restaurant, UserPreferences


def prefs(**kw):
    return UserPreferences(**{"location": "BTM", "budget": "low", **kw})


def test_defaults_and_trimming():
    p = prefs(location="  BTM  ")
    assert (p.location, p.cuisine, p.min_rating, p.extra, p.top_n) == ("BTM", None, 0.0, "", 5)


@pytest.mark.parametrize("cuisine", ["", "Any", "  ANY ", "all", None])
def test_any_cuisine_becomes_none(cuisine):
    assert prefs(cuisine=cuisine).cuisine is None


@pytest.mark.parametrize("kw", [
    {"location": ""}, {"location": "   "}, {"budget": "cheap"}, {"min_rating": -0.1}, {"min_rating": 5.1},
    {"min_rating": float("nan")}, {"min_rating": "abc"}, {"top_n": 0}, {"top_n": -1}, {"top_n": 21},
])
def test_invalid_inputs_rejected(kw):
    with pytest.raises(ValidationError):
        prefs(**kw)


def test_rating_bounds_accepted():
    assert prefs(min_rating=0).min_rating == 0 and prefs(min_rating=5).min_rating == 5


def test_extra_whitespace_collapsed():
    p = prefs(extra="  family   friendly\n\nquick  ")
    assert p.extra == "family friendly quick" and not p.extra_truncated


def test_extra_truncated_and_flagged():
    p = prefs(extra="x" * 5000)
    assert len(p.extra) == config.MAX_EXTRA_CHARS and p.extra_truncated


def test_restaurant_from_parquet_style_row():
    row = pd.Series({
        "id": np.int64(7), "name": "A", "address": "x", "location": "BTM", "area": "BTM",
        "cuisines": np.array(["Pizza", "Italian"], dtype=object), "cost_for_two": pd.NA,
        "budget_tier": None, "rating": np.nan, "votes": np.int64(12), "rest_type": None,
        "online_order": np.bool_(True), "book_table": np.bool_(False), "dishes": np.array([], dtype=object),
        "pre_score": 3.2,  # extra column is ignored
    })
    r = Restaurant.from_row(row)
    assert r.id == 7 and r.cuisines == ["Pizza", "Italian"] and r.cost_for_two is None
    assert r.rating is None and r.votes == 12 and r.online_order is True and r.dishes == []
