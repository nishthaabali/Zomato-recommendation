import pytest

from zomato_reco import config


def test_paths_anchored_to_project_root():
    assert (config.PROJECT_ROOT / "src" / "zomato_reco").is_dir()
    assert config.RESTAURANTS_PARQUET.parent == config.PROCESSED_DATA_DIR


def test_defaults(monkeypatch):
    for name in ("GROQ_API_KEY", "LLM_MODEL", "CANDIDATE_LIMIT", "LLM_TEMPERATURE", "LLM_TIMEOUT_S"):
        monkeypatch.delenv(name, raising=False)
    s = config.load_settings()
    assert s.groq_api_key is None
    assert s.llm_model == config.DEFAULT_LLM_MODEL
    assert (s.candidate_limit, s.llm_temperature, s.llm_timeout_s) == (20, 0.3, 30)


@pytest.mark.parametrize(
    "name,value",
    [("LLM_TEMPERATURE", "abc"), ("LLM_TIMEOUT_S", "-5"), ("CANDIDATE_LIMIT", "0"), ("CANDIDATE_LIMIT", "1000")],
)
def test_invalid_env_rejected(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(config.ConfigError):
        config.load_settings()


def test_missing_api_key_raises_only_when_required(monkeypatch):
    monkeypatch.setattr(config, "settings", config.Settings(None, "m", 20, 0.3, 30))
    with pytest.raises(config.ConfigError):
        config.require_api_key()
