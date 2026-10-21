import pandas as pd
import pytest

from zomato_reco.ingestion import cleaner
from zomato_reco.ingestion.loader import DataError


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("4.1/5", 4.1), ("4.1 /5", 4.1), (" 4.1 / 5 ", 4.1), ("4.1", 4.1), ("5/5", 5.0), ("0/5", 0.0),
        ("NEW", None), ("-", None), ("", None), (None, None), (float("nan"), None), ("N/A", None),
        ("41", None), ("6.2/5", None), ("-1", None),
    ],
)
def test_parse_rating(raw, expected):
    assert cleaner.parse_rating(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("800", 800), ("1,200", 1200), ("₹1200", 1200), ("1200.0", 1200), (" 800 ", 800),
        ("0", None), ("-5", None), ("abc", None), ("", None), (None, None), (float("nan"), None),
    ],
)
def test_parse_cost(raw, expected):
    assert cleaner.parse_cost(raw) == expected


def test_fix_mojibake_repairs_double_encoding():
    garbled = "Café".encode("utf-8").decode("latin-1").encode("utf-8").decode("latin-1")
    assert cleaner.fix_mojibake(garbled) == "Café"
    assert cleaner.fix_mojibake("Plain Name") == "Plain Name"
    assert cleaner.fix_mojibake("Café") == "Café"  # already correct text is untouched


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("North Indian, Chinese", ["North Indian", "Chinese"]),
        ("  Pizza ,pizza, Italian ", ["Pizza", "Italian"]),
        ("Pizza, Pizza", ["Pizza"]),
        ("", []), (None, []), (", ,", []),
    ],
)
def test_split_list(raw, expected):
    assert cleaner.split_list(raw) == expected


def test_split_list_limit():
    assert cleaner.split_list("a, b, c, d", limit=2) == ["a", "b"]


def test_budget_thresholds_and_tiers():
    costs = pd.Series(range(100, 1000, 100), dtype="Int64")  # 9 values
    low, medium = cleaner.budget_thresholds(costs)
    assert low < medium
    assert cleaner.assign_budget_tier(low, low, medium) == "low"
    assert cleaner.assign_budget_tier(medium, low, medium) == "medium"
    assert cleaner.assign_budget_tier(medium + 1, low, medium) == "high"
    assert cleaner.assign_budget_tier(None, low, medium) is None
    assert cleaner.assign_budget_tier(pd.NA, low, medium) is None


def test_budget_thresholds_with_ties_still_three_valid_values():
    low, medium = cleaner.budget_thresholds(pd.Series([300] * 20 + [900], dtype="Int64"))
    assert low <= medium


def test_budget_thresholds_without_costs_raises():
    with pytest.raises(DataError):
        cleaner.budget_thresholds(pd.Series([pd.NA], dtype="Int64"))


def _raw(**overrides):
    base = {
        "name": "Cafe A", "address": "1 Main Rd", "location": "Indiranagar", "listed_in(city)": "Indiranagar",
        "cuisines": "Cafe, Italian", "approx_cost(for two people)": "600", "rate": "4.2 /5", "votes": 100,
        "rest_type": "Cafe", "online_order": "Yes", "book_table": "No", "dish_liked": "Pasta, Coffee",
    }
    return {**base, **overrides}


def test_clean_end_to_end():
    raw = pd.DataFrame(
        [
            _raw(votes=10),                                   # duplicate listing, fewer votes
            _raw(votes=500, **{"rate": "4.4 /5"}),            # duplicate listing, most votes -> kept
            _raw(name="Cafe B", address="2 Side St", location=None, **{"listed_in(city)": "BTM"}),
            _raw(name="Cafe C", address="3 St", rate="NEW", **{"approx_cost(for two people)": None}),  # dropped: no rating and no cost
            _raw(name="Cafe D", address="4 St", rate="NEW", cuisines=None),
            _raw(name=None, address="5 St"),                  # dropped: no name
        ]
    )
    df, meta = cleaner.clean(raw)

    assert set(df["name"]) == {"Cafe A", "Cafe B", "Cafe D"}  # Cafe C has neither rating nor cost
    a = df[df["name"] == "Cafe A"].iloc[0]
    assert (a["votes"], a["rating"]) == (500, 4.4)
    assert df[df["name"] == "Cafe B"].iloc[0]["location"] == "BTM"  # falls back to area
    assert df[df["name"] == "Cafe D"].iloc[0]["cuisines"] == []
    assert df["id"].is_unique and df["id"].tolist() == sorted(df["id"])
    assert list(df.columns) == cleaner.OUTPUT_COLUMNS
    assert meta["restaurants"] == 3 and meta["raw_rows"] == 6


def test_clean_is_deterministic():
    raw = pd.DataFrame([_raw(), _raw(name="Cafe B", address="2 St")])
    assert cleaner.clean(raw)[0].equals(cleaner.clean(raw.iloc[::-1].reset_index(drop=True))[0])


def test_clean_missing_column_raises():
    with pytest.raises(DataError, match="missing expected columns"):
        cleaner.clean(pd.DataFrame({"name": ["x"]}))
