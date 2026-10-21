import pandas as pd
import pytest

from zomato_reco import filtering
from zomato_reco.models import UserPreferences


def make_df(rows):
    base = dict(address="", area="X", rest_type="Cafe", online_order=True, book_table=False, dishes=[])
    df = pd.DataFrame([{**base, **r} for r in rows])
    df["cost_for_two"] = df["cost_for_two"].astype("Int64")
    return df


def r(id, name, loc="BTM", tier="low", cuisines=("Italian",), rating=4.0, votes=100, cost=250):
    return dict(id=id, name=name, location=loc, budget_tier=tier, cuisines=list(cuisines),
                rating=rating, votes=votes, cost_for_two=cost)


@pytest.fixture
def df():
    return make_df([
        r(1, "Pizza Low", cuisines=("Pizza", "Italian"), rating=4.2, votes=500),
        r(2, "Pasta Low Poor", cuisines=("Italian",), rating=3.0, votes=300),
        r(3, "Cafe Medium", tier="medium", cuisines=("Cafe",), rating=4.5, votes=900, cost=450),
        r(4, "Indian High", tier="high", cuisines=("North Indian",), rating=4.7, votes=800, cost=900),
        r(5, "Other Place Low", loc="Indiranagar", rating=4.9, votes=1000),
        r(6, "Unrated Low", cuisines=("Italian",), rating=None, votes=0),
        r(7, "Indian Medium", tier="medium", cuisines=("North Indian",), rating=3.9, votes=200, cost=400),
        r(8, "Nocost", tier=None, cuisines=("Italian",), rating=4.8, votes=700, cost=None),
    ])


def P(**kw):
    return UserPreferences(**{"location": "BTM", "budget": "low", **kw})


def ids(sel):
    return list(sel.candidates["id"])


# --- each filter alone ---------------------------------------------------------
def test_location_filter_case_and_space_insensitive(df):
    assert set(ids(filtering.select(df, P(location="  btm ", budget="medium")))) == {3, 7}


def test_city_alias_means_whole_city(df):
    sel = filtering.select(df, P(location="Bangalore", budget="low"))
    assert {1, 2, 5, 6} <= set(ids(sel))


def test_budget_filter_excludes_other_tiers_and_null_tier(df):
    got = set(ids(filtering.select(df, P(budget="low"))))
    assert got == {1, 2, 6} and 8 not in got


def test_cuisine_filter_is_exact_membership_not_substring(df):
    # "Indian" must not match "North Indian"
    assert filtering.select(df, P(budget="high", cuisine="Indian")).relaxed  # nothing exact -> relaxed
    got = set(ids(filtering.select(df, P(budget="high", cuisine="north indian"))))
    assert got == {4}


def test_min_rating_inclusive_and_excludes_unrated(df):
    assert 1 in ids(filtering.select(df, P(min_rating=4.2)))      # equal to threshold is kept
    assert 6 not in ids(filtering.select(df, P(min_rating=0.5)))  # unrated excluded when min_rating > 0


def test_min_rating_zero_keeps_unrated_ranked_last(df):
    got = ids(filtering.select(df, P(min_rating=0)))
    assert 6 in got and got[-1] == 6


# --- combined / ordering / caps --------------------------------------------------
def test_combined_filters(df):
    sel = filtering.select(df, P(cuisine="Italian", min_rating=3.5))
    assert ids(sel) == [1] and sel.relaxed == []


def test_ranking_by_votes_weighted_score(df):
    sel = filtering.select(df, P(cuisine="Italian"))
    assert ids(sel)[:2] == [1, 2]
    assert sel.candidates["pre_score"].is_monotonic_decreasing


def test_low_vote_perfect_rating_does_not_beat_popular_high_rating():
    # Filler elsewhere gives a realistic global mean (~3.7) for the Bayesian prior.
    filler = [r(10 + i, f"F{i}", loc="Elsewhere", rating=3.3, votes=100) for i in range(8)]
    d = make_df([r(1, "Tiny 5.0", rating=5.0, votes=3), r(2, "Popular 4.5", rating=4.5, votes=2000), *filler])
    assert ids(filtering.select(d, P())) == [2, 1]


def test_limit_caps_results_and_boundaries():
    d = make_df([r(i, f"R{i}", rating=3 + i / 100, votes=100) for i in range(1, 8)])
    assert len(filtering.select(d, P(), limit=5).candidates) == 5
    assert len(filtering.select(d, P(), limit=7).candidates) == 7   # exactly K
    assert len(filtering.select(d, P(), limit=8).candidates) == 7   # K+1 available -> all
    assert len(filtering.select(d, P(), limit=1).candidates) == 1


def test_ties_are_deterministic():
    d = make_df([r(i, f"R{i}", rating=4.0, votes=100) for i in (3, 1, 2)])
    assert ids(filtering.select(d, P())) == [1, 2, 3]
    assert ids(filtering.select(d.iloc[::-1], P())) == [1, 2, 3]


def test_candidate_ids_unique(df):
    got = ids(filtering.select(df, P(budget="medium", min_rating=0)))
    assert len(got) == len(set(got))


def test_input_dataframe_not_mutated(df):
    before = df.copy(deep=True)
    filtering.select(df, P(cuisine="Italian", min_rating=4.9))
    pd.testing.assert_frame_equal(df, before)
    assert "pre_score" not in df.columns


# --- relaxation ladder -------------------------------------------------------------
def test_relax_step1_drops_cuisine(df):
    sel = filtering.select(df, P(cuisine="Martian"))
    assert set(ids(sel)) == {1, 2, 6}
    assert len(sel.relaxed) == 1 and "Cuisine" in sel.relaxed[0]


def test_relax_step2_widens_budget(df):
    # low budget + North Indian: cuisine dropped does not help? it does -> use a case where only widening helps
    d = make_df([r(1, "Med Only", tier="medium", cuisines=("Cafe",), rating=4.0, cost=450)])
    sel = filtering.select(d, P(budget="low"))
    assert ids(sel) == [1]
    assert any("Budget widened" in n for n in sel.relaxed)


def test_budget_widening_directions():
    assert filtering.WIDER_BUDGET["low"] == ("low", "medium")
    assert filtering.WIDER_BUDGET["high"] == ("medium", "high")
    assert filtering.WIDER_BUDGET["medium"] == ("low", "medium", "high")


def test_relax_step3_lowers_rating_stepwise():
    d = make_df([r(1, "Mid", rating=3.2, votes=50)])
    sel = filtering.select(d, P(min_rating=4.0))
    assert ids(sel) == [1]
    # The ladder is cumulative: budget is widened before the rating is lowered.
    assert sel.relaxed == [
        "Budget widened from low to low / medium",
        "Minimum rating lowered from 4 to 3.5",
        "Minimum rating lowered from 3.5 to 3",
    ]


def test_rating_relaxation_is_bounded():
    d = make_df([r(1, "Awful", rating=1.0, votes=50)])
    sel = filtering.select(d, P(min_rating=4.5))
    assert sel.empty and sel.reason and len(sel.relaxed) == filtering.MAX_RATING_RELAXATIONS + 1  # + budget widening


def test_ladder_order_is_cumulative():
    d = make_df([r(1, "Only", tier="medium", cuisines=("Cafe",), rating=3.6, votes=50, cost=450)])
    sel = filtering.select(d, P(budget="low", cuisine="Pizza", min_rating=4.5))
    assert ids(sel) == [1]
    kinds = [n.split()[0] for n in sel.relaxed]
    assert kinds == ["Cuisine", "Budget", "Minimum", "Minimum"]


def test_no_relaxation_when_exact_match_exists(df):
    assert filtering.select(df, P(cuisine="Italian")).relaxed == []


# --- empty / unknown location --------------------------------------------------------
def test_empty_result_has_reason_and_no_candidates():
    d = make_df([r(1, "Low", rating=2.0)])
    sel = filtering.select(d, P(budget="high", min_rating=5.0))
    assert sel.empty
    assert sel.candidates.empty and "No restaurants matched" in sel.reason


def test_unknown_location_suggests_close_matches_without_applying_them(df):
    sel = filtering.select(df, P(location="Indiranagr"))
    assert sel.empty and "not found" in sel.reason
    assert sel.suggestions == ["Indiranagar"]
    assert sel.relaxed == []


def test_unknown_location_no_suggestions_for_garbage(df):
    sel = filtering.select(df, P(location="Zzzzzzz"))
    assert sel.empty and sel.suggestions == []


# --- pre_score ---------------------------------------------------------------------
def test_pre_score_handles_missing_rating_and_votes():
    d = make_df([r(1, "A", rating=None, votes=0), r(2, "B", rating=4.0, votes=0)])
    s = filtering.pre_score(d)
    assert s.iloc[0] == -1.0 and s.iloc[1] == pytest.approx(4.0)  # votes=0 -> prior only
