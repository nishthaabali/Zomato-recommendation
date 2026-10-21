"""Shared test builders."""
import pandas as pd


def make_df(rows):
    base = dict(address="", area="X", rest_type="Cafe", online_order=True, book_table=False, dishes=[])
    df = pd.DataFrame([{**base, **r} for r in rows])
    df["cost_for_two"] = df["cost_for_two"].astype("Int64")
    return df


def r(id, name, loc="BTM", tier="low", cuisines=("Italian",), rating=4.0, votes=100, cost=250, **extra):
    return dict(id=id, name=name, location=loc, budget_tier=tier, cuisines=list(cuisines),
                rating=rating, votes=votes, cost_for_two=cost, **extra)


def sample_df():
    """Six BTM restaurants, five low-budget, with distinct ratings."""
    return make_df([
        r(1, "Alpha Pizzeria", cuisines=("Pizza", "Italian"), rating=4.5, votes=900, dishes=["Margherita", "Tiramisu"]),
        r(2, "Beta Bistro", cuisines=("Italian", "Continental"), rating=4.2, votes=500, rest_type="Casual Dining"),
        r(3, "Gamma Grill", cuisines=("Italian",), rating=4.0, votes=300),
        r(4, "Delta Deli", cuisines=("Italian", "Cafe"), rating=3.8, votes=200),
        r(5, "Epsilon Eats", cuisines=("Italian",), rating=None, votes=0, cost=None, tier="low"),
        r(6, "Zeta Medium", tier="medium", cuisines=("Cafe",), rating=4.9, votes=2000, cost=450),
    ])
