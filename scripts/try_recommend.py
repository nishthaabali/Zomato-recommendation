"""Run the full recommendation pipeline from the command line.

Examples:
  python scripts/try_recommend.py --location Indiranagar --budget medium --cuisine Italian --min-rating 4 \\
      --extra "family-friendly, quick service"
  python scripts/try_recommend.py --no-llm          # force the non-LLM fallback
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from zomato_reco import config, service  # noqa: E402
from zomato_reco.models import UserPreferences  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--location", default="Indiranagar")
    p.add_argument("--budget", choices=["low", "medium", "high"], default="medium")
    p.add_argument("--cuisine")
    p.add_argument("--min-rating", type=float, default=0.0)
    p.add_argument("--extra", default="")
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--no-llm", action="store_true", help="skip the LLM and use the fallback ranking")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    prefs = UserPreferences(location=args.location, budget=args.budget, cuisine=args.cuisine,
                            min_rating=args.min_rating, extra=args.extra, top_n=args.top_n)
    kwargs = {"llm": None} if args.no_llm else {}
    if not args.no_llm and not config.settings.groq_api_key:
        print("(GROQ_API_KEY not set: using the non-LLM fallback)\n")

    resp = service.recommend(prefs, **kwargs)

    print(f"Preferences: {prefs.location} / {prefs.budget} / {prefs.cuisine or 'any cuisine'} / min rating {prefs.min_rating:g}"
          + (f" / '{prefs.extra}'" if prefs.extra else ""))
    for note in resp.relaxed:
        print(f"  ! relaxed: {note}")
    for note in resp.notes:
        print(f"  ! {note}")
    if not resp.items:
        print(f"\nNo recommendations: {resp.message}")
        if resp.suggestions:
            print(f"Did you mean: {', '.join(resp.suggestions)}")
        return
    print(f"\n{'AI-generated' if resp.ai_explanations else 'Template (AI unavailable)'} explanations\n")
    if resp.summary:
        print(f"Summary: {resp.summary}\n")
    for it in resp.items:
        r = it.restaurant
        rating = f"{r.rating:.1f}" if r.rating is not None else "n/a"
        cost = f"Rs {r.cost_for_two:,} for two" if r.cost_for_two else "cost n/a"
        print(f"{it.rank}. {r.name}  [id {r.id}]")
        print(f"   {', '.join(r.cuisines) or 'n/a'} | rating {rating} | {cost} | {r.location}")
        print(f"   {it.explanation}\n")


if __name__ == "__main__":
    main()
