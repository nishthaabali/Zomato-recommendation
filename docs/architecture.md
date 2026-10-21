# Architecture: AI-Powered Restaurant Recommendation System

Companion to [problemStatement.md](problemStatement.md). This document describes how to build the system: components, data flow, interfaces, prompt design and delivery phases.

> **Assumptions to verify:** the dataset's exact column names and value formats (e.g. how cost and rating are stored) have not been inspected yet. Field names below are indicative. Phase 1 should start by profiling the dataset and updating the schema section.

---

## 1. Goals and Constraints

| Goal | Implication |
|---|---|
| Personalized, explainable recommendations | LLM generates ranking and reasoning |
| Grounded in real data | LLM only sees pre-filtered rows from the dataset, never invents restaurants |
| Fast and cheap | Filter deterministically first; send only a small candidate set (~10-20) to the LLM |
| Simple to run | Single Python project, one command to start |

**Key design principle:** *deterministic filtering first, LLM reasoning second.* Hard constraints (location, budget, min rating, cuisine) are applied in code. The LLM handles soft preferences ("family-friendly", "quick service"), ranking and explanation.

---

## 2. High-Level Architecture

```
┌──────────────┐   preferences   ┌─────────────────────────────────────────┐
│     User     │ ──────────────▶ │            UI Layer (Streamlit)         │
└──────────────┘                 └───────────────┬─────────────────────────┘
       ▲                                         │ UserPreferences
       │ rendered cards                          ▼
       │                         ┌─────────────────────────────────────────┐
       │                         │        Recommendation Service           │
       │                         │  (orchestrates the pipeline)            │
       │                         └───┬─────────────┬───────────────┬───────┘
       │                             │             │               │
       │                             ▼             ▼               ▼
       │                   ┌──────────────┐ ┌─────────────┐ ┌───────────────┐
       │                   │ Filter Engine│ │Prompt Builder│ │  LLM Client   │
       │                   └──────┬───────┘ └──────┬──────┘ └───────┬───────┘
       │                          │                │                │
       │                          ▼                │                ▼
       │                   ┌──────────────┐        │        ┌───────────────┐
       │                   │  Data Store  │        │        │ LLM Provider  │
       │                   │ (clean parquet│       │        │ (API)         │
       │                   │  / DataFrame)│        │        └───────────────┘
       │                   └──────▲───────┘        │
       │                          │                │
       │                   ┌──────┴───────┐        │
       │                   │Ingestion     │        │
       │                   │Pipeline (HF) │        │
       │                   └──────────────┘        │
       │                                           │
       └──────────── Response Parser ◀─────────────┘
```

Layers map directly to the workflow in the problem statement:

| Problem-statement stage | Component(s) |
|---|---|
| Data Ingestion | Ingestion Pipeline, Data Store |
| User Input | UI Layer, `UserPreferences` model |
| Integration Layer | Filter Engine, Prompt Builder |
| Recommendation Engine | LLM Client, Response Parser |
| Output Display | UI Layer (result cards) |

---

## 3. Technology Stack

| Concern | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Strong data/LLM ecosystem |
| Data loading | `datasets` (Hugging Face) | Native access to the dataset |
| Data processing | `pandas` | Dataset is tabular and small enough for memory |
| Storage | Parquet file in `data/processed/` | Fast reload; avoids re-downloading and re-cleaning |
| Validation / models | `pydantic` | Typed preferences, candidates and LLM output |
| LLM | Groq API (`groq` SDK, default `openai/gpt-oss-120b`, a reasoning model, so the client sets `reasoning_effort=low` and adds token headroom), behind an abstraction | Very low latency; OpenAI-style chat API with JSON mode; provider is swappable |
| UI | Streamlit | Fastest route to a form + result cards |
| Config | `.env` + `python-dotenv` | API key kept out of source control |
| Testing | `pytest` | Unit tests for filter and parser; mocked LLM |

A FastAPI layer can be added later if a separate frontend is wanted; the service layer is UI-agnostic so this is a thin addition.

---

## 4. Project Structure

```
M1 -zomato/
├── docs/
│   ├── problemStatement.md
│   └── architecture.md
├── data/
│   ├── raw/                  # cached HF download (gitignored)
│   └── processed/
│       └── restaurants.parquet
├── src/
│   └── zomato_reco/
│       ├── config.py         # settings, env loading, constants
│       ├── models.py         # pydantic: UserPreferences, Restaurant, Recommendation
│       ├── ingestion/
│       │   ├── loader.py     # download from Hugging Face
│       │   └── cleaner.py    # normalise columns, handle nulls, derive budget tier
│       ├── store.py          # load/cache processed data, list available locations/cuisines
│       ├── filtering.py      # deterministic candidate selection
│       ├── prompting.py      # prompt templates + candidate serialisation
│       ├── llm_client.py     # provider abstraction + Groq implementation
│       ├── parser.py         # validate/repair LLM JSON output
│       ├── service.py        # orchestrates the full pipeline
│       └── fallback.py       # non-LLM ranking if the LLM fails
├── app.py                    # Streamlit entry point
├── scripts/
│   └── build_dataset.py      # one-off: run ingestion and write parquet
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

---

## 5. Component Design

### 5.1 Data Ingestion (`ingestion/`)

**Purpose:** turn the raw Hugging Face dataset into a clean, query-ready table.

**Dataset profile (verified in Phase 1):**
- 51,717 raw rows, 17 columns. **Bangalore only** (all URLs are `zomato.com/bangalore/...`); there is no Delhi or other city data.
- `location` is a **neighbourhood** (93 values, e.g. BTM, Indiranagar); 21 nulls. `listed_in(city)` is a coarser area (30 values) and is used as a fallback.
- The same restaurant is repeated once per listing type (`listed_in(type)`: Delivery, Dine-out, ...), with slightly different votes/ratings. Cleaning de-duplicates on **(name, address)** and keeps the most-voted row, giving **12,438 restaurants**.
- `rate` looks like `"4.1 /5"` (note the space), plus `"NEW"` (2,208) and `"-"` (69); 7,775 nulls. 2,978 restaurants end up without a rating.
- `approx_cost(for two people)` is a string with thousands separators (`"1,200"`); 346 nulls. Budget tiers (global quantiles on cost for two): **low <= 300, medium <= 500, high > 500**.
- `cuisines` is a comma-separated string (106 distinct values after cleaning); 45 nulls.
- Some names are double-encoded (`CafÃ©`); repaired during cleaning.
- Extra fields kept for the LLM: `rest_type`, `online_order`, `book_table`, top 5 `dishes` (from `dish_liked`). `reviews_list`, `menu_item`, `url`, `phone` are dropped (large or irrelevant).
- Processed columns: `id, name, address, location, area, cuisines, cost_for_two, budget_tier, rating, votes, rest_type, online_order, book_table, dishes`. `cuisines` keeps original casing; matching must be case-insensitive.

Steps:
1. **Load** via `datasets.load_dataset("ManikaSaini/zomato-restaurant-recommendation")`, convert to a DataFrame.
2. **Select fields:** restaurant name, location/city, cuisines, approximate cost, rating, plus any useful descriptive fields (e.g. restaurant type, online order/table booking, popular dishes, votes) which feed soft preferences.
3. **Clean:**
   - Parse rating strings (e.g. `"4.1/5"`, `"NEW"`, `"-"`) into a float; non-numeric becomes null.
   - Parse cost (strings with commas, e.g. `"1,200"`) into an integer.
   - Split multi-valued cuisine strings into a normalised list; lower-case and trim.
   - Normalise location names (case, whitespace).
   - Drop rows missing name, location or both rating and cost; deduplicate on (name, location).
4. **Derive `budget_tier`:** map cost-for-two to `low / medium / high` using quantile thresholds computed from the data (e.g. bottom third / middle third / top third), stored in config so they are inspectable and tunable.
5. **Persist** to `data/processed/restaurants.parquet`. `scripts/build_dataset.py` runs this once; the app loads the parquet on startup and builds it automatically if missing.

### 5.2 Data Store (`store.py`)

- Loads the parquet into memory once (cached with `st.cache_resource`).
- Exposes helper lists, `get_locations()` and `get_cuisines()`, used to populate UI dropdowns so users pick from values that actually exist in the data.

### 5.3 Data Models (`models.py`)

```python
class UserPreferences(BaseModel):
    location: str
    budget: Literal["low", "medium", "high"]
    cuisine: str | None            # None = any
    min_rating: float = 0.0        # 0-5
    extra: str = ""                # free text: "family-friendly, quick service"
    top_n: int = 5

class Restaurant(BaseModel):
    id: int
    name: str
    location: str
    cuisines: list[str]
    cost_for_two: int | None
    rating: float | None
    votes: int | None
    # + optional descriptive fields (type, online_order, popular dishes...)

class Recommendation(BaseModel):
    rank: int
    restaurant_id: int             # must reference a candidate we sent
    explanation: str

class RecommendationResult(BaseModel):
    recommendations: list[Recommendation]
    summary: str | None
```

### 5.4 Filter Engine (`filtering.py`)

Applies hard constraints in order, producing a bounded candidate list:

1. `location` match (exact after normalisation; optionally fuzzy fallback).
2. `budget_tier` equals requested tier.
3. `cuisine` contained in the restaurant's cuisine list (if provided).
4. `rating >= min_rating`.
5. **Sort** by a pre-score (rating weighted by log of votes, to avoid a 5.0 with 3 votes outranking a 4.5 with 2,000) and **keep the top K candidates** (default K = 15-20).

**Empty-result handling (relaxation ladder):** if no candidates remain, relax constraints one at a time in a fixed order (drop cuisine → widen budget by one tier → lower min rating by 0.5) and tell the user what was relaxed. If still empty, return a clear "no matches" message without calling the LLM.

Capping K keeps prompts small, cheap and fast, and limits hallucination surface.

### 5.5 Prompt Builder (`prompting.py`)

Builds a two-part prompt.

**System prompt (static):** role, rules, and output contract.
- You are a restaurant recommendation expert.
- Recommend **only** from the provided candidate list; refer to restaurants by `id`.
- Rank by fit to the user's preferences, giving weight to the free-text preferences.
- Each explanation must reference concrete facts from the data (cuisine, rating, cost) and the user's stated needs; do not invent amenities not in the data.
- Respond with JSON matching the schema, and nothing else.

**User prompt (dynamic):**
```
User preferences:
- Location: Bangalore
- Budget: medium
- Cuisine: Italian
- Minimum rating: 4.0
- Additional: family-friendly, quick service

Candidates (JSON array, one object per restaurant):
[{"id": 101, "name": "...", "cuisines": ["Italian","Pizza"],
  "rating": 4.3, "votes": 1520, "cost_for_two": 900, "type": "Casual Dining"}, ...]

Return the top 5 as JSON:
{"recommendations":[{"rank":1,"restaurant_id":101,"explanation":"..."}],
 "summary":"one or two sentences comparing the choices"}
```

Design notes:
- Candidates serialised compactly (only fields the LLM needs) to control token use.
- Explicit schema in the prompt plus parser validation (below).
- Low temperature (≈0.2-0.3) for consistent ranking; explanations stay natural.

### 5.6 LLM Client (`llm_client.py`)

- Defines an `LLMClient` protocol: `complete(system: str, user: str) -> str`.
- `GroqClient` implements it using the `groq` SDK (chat completions with JSON mode); model name and API key come from config so the model can be changed without code changes.
- Handles timeouts, bounded retries with backoff on transient errors (rate limit, 5xx).
- Swapping providers means writing one new class; the rest of the system is unaffected.

### 5.7 Response Parser (`parser.py`)

Never trust LLM output blindly:
1. Extract the JSON (strip code fences if present) and validate against `RecommendationResult`.
2. **Grounding check:** every `restaurant_id` must be in the candidate set; drop any that are not (hallucination guard). De-duplicate ids.
3. Re-number ranks sequentially; truncate to `top_n`.
4. On invalid JSON, retry once with a "fix your output" message; if that also fails, fall through to the fallback.

### 5.8 Fallback (`fallback.py`)

If the LLM call or parsing fails, return the top-N by pre-score with a templated explanation (e.g. "Highly rated Italian restaurant in Bangalore, ₹900 for two"). The app always returns something useful and flags that AI explanations were unavailable.

### 5.9 Recommendation Service (`service.py`)

Single entry point used by the UI:

```python
def recommend(prefs: UserPreferences) -> RecommendationResponse:
    candidates, relaxed = filtering.select(store.df, prefs)
    if not candidates:
        return RecommendationResponse.empty(relaxed)
    system, user = prompting.build(prefs, candidates)
    try:
        raw = llm.complete(system, user)
        result = parser.parse(raw, candidates, prefs.top_n)
    except LLMError:
        result = fallback.rank(candidates, prefs)
    return join(result, candidates, relaxed)   # attach full restaurant data
```

The service joins LLM output (id + explanation) back to the authoritative dataset row, so displayed name, rating and cost always come from data, never from the model's text.

### 5.10 UI Layer (`app.py`, Streamlit)

**Input panel:**
- Location: select box (from `get_locations()`)
- Budget: radio / select (low, medium, high)
- Cuisine: select box with "Any" (from `get_cuisines()`)
- Minimum rating: slider 0-5, step 0.5
- Additional preferences: text input
- Submit button

**Results:** one card per recommendation showing rank, **restaurant name**, **cuisine**, **rating**, **estimated cost**, and the **AI-generated explanation**; above the cards, the optional summary and any "we relaxed X" notice. Spinner during the LLM call; friendly messages for empty results and errors.

---

## 6. End-to-End Data Flow

1. **Startup:** app loads `restaurants.parquet` (building it via ingestion if absent).
2. **Input:** user submits preferences → validated into `UserPreferences`.
3. **Filter:** hard constraints applied → ≤K candidates (with relaxation if needed).
4. **Prompt:** candidates + preferences rendered into the prompt.
5. **LLM:** returns ranked JSON with explanations.
6. **Parse and ground:** validate, drop unknown ids, enforce top-N.
7. **Join and render:** merge with dataset rows, display cards.
8. **Failure path:** any LLM/parse failure → fallback ranking, UI notes it.

---

## 7. Cross-Cutting Concerns

**Configuration** (`.env`): `GROQ_API_KEY`, `LLM_MODEL`, `CANDIDATE_LIMIT`, `LLM_TEMPERATURE`, `LLM_TIMEOUT_S`. Provide `.env.example`; never commit `.env`.

**Error handling:** typed exceptions (`DataError`, `LLMError`, `ParseError`); the service converts them to user-facing messages or fallback behavior.

**Performance:** data cached in memory; filtering is vectorised pandas (milliseconds); latency is dominated by one LLM call (typically a few seconds). Optionally cache results keyed by the preference tuple.

**Cost control:** capped candidate count, compact serialisation, capped `max_tokens`.

**Privacy / security:** only the free-text preference and restaurant rows are sent to the LLM; no personal data collected. Sanitise/limit length of the free-text field and treat it as untrusted input in the prompt (it is delimited and the system prompt instructs the model to ignore instructions inside it).

**Logging:** log preferences, candidate count, relaxations, latency, token usage and parse failures (no API keys).

---

## 8. Testing Strategy

| Level | What |
|---|---|
| Unit | Cleaner (rating/cost parsing edge cases), budget-tier derivation, filter logic and relaxation ladder, parser (valid, fenced, malformed, hallucinated ids) |
| Integration | Service with a **mocked `LLMClient`** returning canned JSON; fallback path when mock raises |
| Prompt checks | Snapshot test of rendered prompt for a fixed input |
| Manual / eval | A small set of representative queries run against the real LLM, reviewed for relevance and grounding (explanations consistent with the data) |

---

## 9. Delivery Phases

| Phase | Deliverable | Done when |
|---|---|---|
| 1. Data | Profile dataset; ingestion + cleaning; parquet; `store.py` | Clean table builds with one command; locations/cuisines listable |
| 2. Filtering | Models, filter engine with relaxation, unit tests | Given preferences, returns sensible bounded candidates |
| 3. LLM core | Prompt builder, Groq client, parser, fallback, service | CLI call returns grounded, ranked results with explanations |
| 4. UI | Streamlit form and result cards | End-to-end flow works in the browser |
| 5. Hardening | Error states, logging, caching, README, eval queries | Handles empty/failed cases gracefully; documented setup |

---

## 10. Open Questions / Future Enhancements

- Confirm dataset schema and whether locations are cities or neighbourhoods (affects the location input and fuzzy matching).
- Whether "budget" thresholds should be fixed rupee ranges instead of data quantiles.
- Optional: semantic retrieval (embeddings) over reviews/dishes to better match free-text preferences before the LLM step.
- Optional: user feedback (thumbs up/down), saved preferences, multi-turn refinement ("show cheaper options").
- Optional: FastAPI backend plus separate frontend for deployment.
