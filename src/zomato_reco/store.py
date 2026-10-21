"""Access to the processed restaurant table (built on first use if missing)."""
from __future__ import annotations

import json
import logging
from functools import lru_cache

import pandas as pd

from zomato_reco import config
from zomato_reco.ingestion import cleaner
from zomato_reco.ingestion.loader import DataError, load_raw

log = logging.getLogger(__name__)

METADATA_JSON = config.PROCESSED_DATA_DIR / "metadata.json"


def build_dataset(refresh_raw: bool = False) -> tuple[pd.DataFrame, dict]:
    """Run load -> clean and write the parquet and metadata atomically."""
    df, meta = cleaner.clean(load_raw(refresh=refresh_raw))
    config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    tmp = config.RESTAURANTS_PARQUET.with_suffix(".tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(config.RESTAURANTS_PARQUET)
    METADATA_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return df, meta


def _read_metadata() -> dict:
    try:
        return json.loads(METADATA_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=1)
def get_df() -> pd.DataFrame:
    """Return the processed table; build it if missing, stale or unreadable."""
    fresh = (
        config.RESTAURANTS_PARQUET.exists()
        and _read_metadata().get("schema_version") == cleaner.SCHEMA_VERSION
    )
    if fresh:
        try:
            return pd.read_parquet(config.RESTAURANTS_PARQUET)
        except Exception:
            log.warning("Processed parquet unreadable, rebuilding")
    log.info("Building processed dataset")
    return build_dataset()[0]


def get_metadata() -> dict:
    get_df()
    return _read_metadata()


def get_locations() -> list[str]:
    """Sorted, de-duplicated neighbourhood names present in the data."""
    return sorted(get_df()["location"].dropna().unique().tolist())


def get_cuisines() -> list[str]:
    """Sorted, de-duplicated cuisine names present in the data."""
    seen: dict[str, str] = {}
    for cuisines in get_df()["cuisines"]:
        for c in cuisines:
            seen.setdefault(c.lower(), c)
    return sorted(seen.values(), key=str.lower)


__all__ = ["DataError", "build_dataset", "get_df", "get_metadata", "get_locations", "get_cuisines"]
