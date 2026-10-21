import pandas as pd
import pytest

from zomato_reco import config, store


@pytest.fixture
def tiny_store(tmp_path, monkeypatch):
    """Point the store at a temp dir with a small processed table."""
    parquet = tmp_path / "restaurants.parquet"
    pd.DataFrame(
        {
            "location": ["BTM", "Indiranagar", "BTM", None],
            "cuisines": [["Pizza", "Italian"], ["pizza"], [], ["Cafe"]],
        }
    ).to_parquet(parquet)
    monkeypatch.setattr(config, "RESTAURANTS_PARQUET", parquet)
    monkeypatch.setattr(store, "METADATA_JSON", tmp_path / "metadata.json")
    monkeypatch.setattr(store.cleaner, "SCHEMA_VERSION", 1)
    (tmp_path / "metadata.json").write_text('{"schema_version": 1}')
    store.get_df.cache_clear()
    yield
    store.get_df.cache_clear()


def test_locations_sorted_unique_no_blanks(tiny_store):
    assert store.get_locations() == ["BTM", "Indiranagar"]


def test_cuisines_sorted_case_insensitively_deduped(tiny_store):
    assert store.get_cuisines() == ["Cafe", "Italian", "Pizza"]
