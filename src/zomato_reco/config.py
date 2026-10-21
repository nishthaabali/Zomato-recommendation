"""Central configuration: paths, environment settings and constants.

Importing this module never fails because of a missing API key, so data-only
features keep working without one. Use `require_api_key()` where it is needed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# --- Paths (anchored to the project root, not the working directory) ---------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESTAURANTS_PARQUET = PROCESSED_DATA_DIR / "restaurants.parquet"

load_dotenv(PROJECT_ROOT / ".env")

# --- Dataset -----------------------------------------------------------------
HF_DATASET_ID = "ManikaSaini/zomato-restaurant-recommendation"

# --- Budget tiers -------------------------------------------------------------
BUDGET_TIERS = ("low", "medium", "high")
# Quantile cut points on cost-for-two (bottom third / middle third / top third).
# The resulting rupee thresholds are computed at build time and stored with the data.
BUDGET_QUANTILES = (1 / 3, 2 / 3)

# --- Input limits --------------------------------------------------------------
MAX_EXTRA_CHARS = 300
DEFAULT_TOP_N = 5

# --- LLM call behaviour ---------------------------------------------------------
LLM_MAX_ATTEMPTS = 3          # per call: first try + retries on transient errors
LLM_TOTAL_BUDGET_S = 45.0     # hard cap on one call including retries and backoff
LLM_MAX_RETRY_WAIT_S = 8.0    # longest single backoff / retry-after honoured
LLM_REASONING_HEADROOM = 3000  # extra max_tokens for reasoning models (hidden thinking tokens)

DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"  # Groq model id; override with LLM_MODEL


class ConfigError(ValueError):
    """Raised when an environment setting is missing or invalid."""


def _get_number(name: str, default: float, lo: float, hi: float, cast=float):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = cast(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from None
    if not lo <= value <= hi:
        raise ConfigError(f"{name} must be between {lo} and {hi}, got {value}")
    return value


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None
    llm_model: str
    candidate_limit: int
    llm_temperature: float
    llm_timeout_s: float


def load_settings() -> Settings:
    """Read and validate settings from the environment."""
    key = (os.getenv("GROQ_API_KEY") or "").strip() or None
    model = (os.getenv("LLM_MODEL") or "").strip() or DEFAULT_LLM_MODEL
    return Settings(
        groq_api_key=key,
        llm_model=model,
        candidate_limit=_get_number("CANDIDATE_LIMIT", 20, 1, 100, cast=int),
        llm_temperature=_get_number("LLM_TEMPERATURE", 0.3, 0.0, 1.0),
        llm_timeout_s=_get_number("LLM_TIMEOUT_S", 30, 1, 300),
    )


settings = load_settings()


def require_api_key() -> str:
    """Return the API key or raise a clear error if it is not configured."""
    if not settings.groq_api_key:
        raise ConfigError("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
    return settings.groq_api_key
