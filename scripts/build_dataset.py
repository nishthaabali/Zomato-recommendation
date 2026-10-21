"""Download, clean and write data/processed/restaurants.parquet."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from zomato_reco import config  # noqa: E402
from zomato_reco.store import build_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-download the raw dataset")
    args = parser.parse_args()

    df, meta = build_dataset(refresh_raw=args.refresh)
    th = meta["budget_thresholds"]
    print(f"Wrote {config.RESTAURANTS_PARQUET}")
    print(f"raw rows: {meta['raw_rows']}  usable: {meta['after_drop_unusable']}  restaurants: {meta['restaurants']}")
    print(f"budget tiers: low <= {th['low_max']}, medium <= {th['medium_max']}, high above")
    print("\nrestaurants per tier:")
    print(df["budget_tier"].value_counts(dropna=False).to_string())
    print("\nnull counts:")
    print(df.isna().sum().to_string())
    print(f"\nempty cuisine lists: {(df['cuisines'].str.len() == 0).sum()}")
    print(f"locations: {df['location'].nunique()}  distinct cuisines: {df['cuisines'].explode().nunique()}")


if __name__ == "__main__":
    main()
