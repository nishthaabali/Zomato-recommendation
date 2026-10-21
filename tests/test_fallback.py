import pandas as pd

from tests.helpers import make_df, r, sample_df
from zomato_reco import fallback


def test_describe_full_row():
    row = sample_df().iloc[0]
    text = fallback.describe(row)
    assert "Alpha Pizzeria" in text and "Pizza, Italian" in text and "BTM" in text
    assert "4.5/5" in text and "900 votes" in text and "₹250" in text


def test_describe_missing_rating_and_cost_never_prints_nan_or_none():
    row = sample_df().iloc[4]  # no rating, no cost
    text = fallback.describe(row)
    assert "Not rated yet" in text and "for two" not in text
    assert "nan" not in text.lower() and "none" not in text.lower() and "<NA>" not in text


def test_describe_no_cuisines_or_type():
    df = make_df([r(1, "Mystery", cuisines=(), rest_type=None)])
    assert fallback.describe(df.iloc[0]).startswith("Mystery is a restaurant in BTM.")


def test_rank_takes_top_n_in_order():
    df = sample_df()
    res = fallback.rank(df, 3)
    assert [x.restaurant_id for x in res.recommendations] == [1, 2, 3]
    assert [x.rank for x in res.recommendations] == [1, 2, 3]
    assert all(x.explanation for x in res.recommendations) and res.summary is None


def test_rank_with_fewer_candidates_than_top_n():
    assert len(fallback.rank(sample_df().head(2), 5).recommendations) == 2
