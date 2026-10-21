"""Try the filter engine from the command line.

Examples:
  python scripts/try_filter.py --location Indiranagar --budget medium --cuisine Italian --min-rating 4
  python scripts/try_filter.py                      # runs a set of sample queries
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from zomato_reco import filtering, store  # noqa: E402
from zomato_reco.models import UserPreferences  # noqa: E402

SAMPLES = [
    dict(location="Bangalore", budget="medium", cuisine="Italian", min_rating=4.0),
    dict(location="Indiranagar", budget="low", cuisine="North Indian", min_rating=3.5),
    dict(location="Koramangala 5th Block", budget="high", cuisine="Chinese", min_rating=4.0),
    dict(location="BTM", budget="low", cuisine="Italian", min_rating=4.8),     # forces relaxation
    dict(location="Indiranagr", budget="medium"),                               # typo -> suggestions
]


def show(prefs: UserPreferences) -> None:
    sel = filtering.select(store.get_df(), prefs)
    print(f"\n=== {prefs.location} / {prefs.budget} / {prefs.cuisine or 'any'} / min {prefs.min_rating} ===")
    for note in sel.relaxed:
        print(f"  relaxed: {note}")
    if sel.empty:
        print(f"  no candidates: {sel.reason}")
        if sel.suggestions:
            print(f"  did you mean: {', '.join(sel.suggestions)}")
        return
    print(f"  {len(sel.candidates)} candidates (showing top 8)")
    for _, r in sel.candidates.head(8).iterrows():
        rating = "n/a" if r["rating"] != r["rating"] else f"{r['rating']:.1f}"
        print(f"  {r['pre_score']:.2f}  {r['name'][:32]:<32} {', '.join(r['cuisines'])[:34]:<34} "
              f"Rs{r['cost_for_two']:<5} rating {rating:<4} votes {r['votes']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--location")
    p.add_argument("--budget", choices=["low", "medium", "high"], default="medium")
    p.add_argument("--cuisine")
    p.add_argument("--min-rating", type=float, default=0.0)
    args = p.parse_args()

    if args.location:
        show(UserPreferences(location=args.location, budget=args.budget, cuisine=args.cuisine, min_rating=args.min_rating))
    else:
        for s in SAMPLES:
            show(UserPreferences(**s))


if __name__ == "__main__":
    main()
