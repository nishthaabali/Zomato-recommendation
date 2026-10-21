"""Download the raw Zomato dataset from Hugging Face and cache it locally."""
from __future__ import annotations

import logging

import pandas as pd

from zomato_reco import config

log = logging.getLogger(__name__)

RAW_CACHE = config.RAW_DATA_DIR / "zomato_raw.parquet"


class DataError(RuntimeError):
    """Raised when the dataset cannot be loaded or is unusable."""


def load_raw(refresh: bool = False) -> pd.DataFrame:
    """Return the raw dataset as a DataFrame, using the local cache when present."""
    if RAW_CACHE.exists() and not refresh:
        try:
            return pd.read_parquet(RAW_CACHE)
        except Exception:  # corrupt cache: fall through and re-download
            log.warning("Raw cache unreadable, re-downloading")

    try:
        from datasets import load_dataset

        ds = load_dataset(config.HF_DATASET_ID)
    except Exception as exc:
        raise DataError(
            f"Could not download {config.HF_DATASET_ID}: {exc}. "
            f"If you are offline, place the file at {RAW_CACHE}."
        ) from exc

    df = ds[next(iter(ds.keys()))].to_pandas()
    if df.empty:
        raise DataError("Downloaded dataset has zero rows")

    config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = RAW_CACHE.with_suffix(".tmp")
    df.to_parquet(tmp)
    tmp.replace(RAW_CACHE)  # atomic: never leaves a partial cache
    return df
