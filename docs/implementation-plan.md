# Implementation Plan: AI-Powered Restaurant Recommendation System

Phase-wise build plan derived from [architecture.md](architecture.md) and [problemStatement.md](problemStatement.md). Each phase ends with a verifiable exit check, and each phase builds only on earlier ones, so the project is runnable and testable at every step.

**Legend:** `[ ]` task to do. Paths are relative to the project root.

## Overview

| Phase | Focus | Key output | Depends on |
|---|---|---|---|
| 0 | Project setup | Skeleton, env, config | none |
| 1 | Data ingestion | `restaurants.parquet`, `store.py` | 0 |
| 2 | Models and filtering | Candidate selection with relaxation | 1 |
| 3 | LLM core | Prompt, client, parser, fallback, service | 2 |
| 4 | UI | Streamlit app | 3 |
| 5 | Hardening and docs | Logging, caching, eval, README | 4 |

---

## Phase 0: Project Setup

**Goal:** a runnable, configured Python project skeleton.

- [ ] Create folder structure from architecture §4 (`src/zomato_reco/`, `ingestion/`, `scripts/`, `tests/`, `data/raw`, `data/processed`).
- [ ] Create a virtual environment (Python 3.11+).
- [ ] `requirements.txt`: `datasets`, `pandas`, `pyarrow`, `pydantic`, `groq`, `streamlit`, `python-dotenv`, `pytest`.
- [ ] `.gitignore`: `.env`, `data/raw/`, `.venv/`, `__pycache__/`.
- [ ] `.env.example` with `GROQ_API_KEY`, `LLM_MODEL`, `CANDIDATE_LIMIT=20`, `LLM_TEMPERATURE=0.3`, `LLM_TIMEOUT_S=30`.
- [ ] `config.py`: load env, define constants and paths, budget-threshold settings.
- [ ] Add pytest config so `src/` is importable.

**Exit check:** `pytest` runs (zero tests is fine) and `python -c "from zomato_reco import config"` succeeds.

---

## Phase 1: Data Ingestion

**Goal:** a clean, query-ready restaurant table built with one command.

- [ ] **Profile the dataset first** (notebook or script): column names, dtypes, null rates, sample values for rating, cost, location, cuisines. Record findings in architecture §5.1 and resolve its open question about whether locations are cities or neighbourhoods.
- [ ] `ingestion/loader.py`: `load_raw()` via `datasets.load_dataset("ManikaSaini/zomato-restaurant-recommendation")`, return a DataFrame, cache raw copy in `data/raw/`.
- [ ] `ingestion/cleaner.py`:
  - [ ] Parse rating (`"4.1/5"`, `"NEW"`, `"-"`) to float or null.
  - [ ] Parse cost (`"1,200"`) to int.
  - [ ] Split and normalise cuisines to a lower-case list.
  - [ ] Normalise location strings.
  - [ ] Drop rows missing name or location, or missing both rating and cost; dedupe on (name, location).
  - [ ] Assign a stable integer `id`.
  - [ ] Derive `budget_tier` (low/medium/high) from cost quantiles; thresholds written to config or output metadata.
- [ ] `scripts/build_dataset.py`: runs load, clean, then writes `data/processed/restaurants.parquet` and prints a summary (row count, per-tier counts, null counts).
- [ ] `store.py`: load parquet once, build it if missing, expose `get_df()`, `get_locations()`, `get_cuisines()`.
- [ ] Tests: parametrised cases for rating and cost parsing, cuisine splitting, budget-tier derivation.

**Exit check:** `python scripts/build_dataset.py` produces the parquet; `get_locations()` and `get_cuisines()` return sensible sorted lists; cleaner tests pass.

---

## Phase 2: Models and Filtering

**Goal:** given user preferences, deterministically return a bounded, ranked candidate list.

- [ ] `models.py`: `UserPreferences` (with validation: rating 0-5, trimmed and length-capped `extra`), `Restaurant`, `Recommendation`, `RecommendationResult`, `RecommendationResponse`.
- [ ] `filtering.py`:
  - [ ] Hard filters in order: location, budget tier, cuisine membership, min rating.
  - [ ] Pre-score = rating weighted by log(votes); sort descending.
  - [ ] Cap to `CANDIDATE_LIMIT`.
  - [ ] Relaxation ladder: drop cuisine, then widen budget one tier, then lower min rating by 0.5. Return the list of relaxations applied.
  - [ ] Return empty with a reason if nothing matches after relaxation.
- [ ] Tests: each filter alone; combined filters; ordering with the votes weighting (a 5.0 with 3 votes does not beat 4.5 with 2,000); each relaxation step; empty result.
- [ ] Small CLI/script to try preferences and print candidates.

**Exit check:** for several realistic preference sets (e.g. Bangalore / medium / Italian / 4.0) the script prints at most K sensible candidates; filtering tests pass.

---

## Phase 3: LLM Core

**Goal:** a CLI call returns grounded, ranked recommendations with explanations, and degrades gracefully.

- [ ] `llm_client.py`:
  - [ ] `LLMClient` protocol with `complete(system, user) -> str`.
  - [ ] `GroqClient` using the `groq` SDK, with model, temperature, `max_tokens` and timeout from config.
  - [ ] Bounded retries with backoff for rate limit and 5xx; raise `LLMError` after exhaustion.
- [ ] `prompting.py`:
  - [ ] Static system prompt: role, "only recommend from candidates by id", factual explanations, JSON-only output, ignore instructions inside user free text.
  - [ ] User prompt builder: preferences block, compact candidate JSON (only needed fields), output schema, `top_n`.
  - [ ] Delimit the free-text `extra` field as untrusted input.
- [ ] `parser.py`:
  - [ ] Strip code fences, parse JSON, validate with pydantic.
  - [ ] Grounding check: drop ids not in candidates; dedupe.
  - [ ] Re-rank sequentially and truncate to `top_n`.
  - [ ] One repair retry on invalid JSON, then raise `ParseError`.
- [ ] `fallback.py`: top-N by pre-score with templated explanations built from data fields.
- [ ] `service.py`: `recommend(prefs)` per architecture §5.9. Join LLM ids back to dataset rows so name, cuisine, rating and cost come from data. Include `relaxed` notes and a flag `ai_explanations: bool`.
- [ ] Tests (no network):
  - [ ] Parser: valid, fenced, malformed, hallucinated id, duplicates, fewer than `top_n`.
  - [ ] Prompt snapshot for a fixed input.
  - [ ] Service with a mocked `LLMClient`: happy path, `LLMError` leading to fallback, `ParseError` leading to fallback, empty candidates skipping the LLM.
- [ ] `scripts/try_recommend.py`: run the real pipeline from the command line.

**Exit check:** with a real API key, `try_recommend.py` prints ranked results whose names, ratings and costs match the dataset; with the key removed or the client forced to fail, fallback results are returned and flagged. All mocked tests pass.

---

## Phase 4: UI

**Goal:** the complete user flow in the browser.

- [ ] `app.py` input panel: location select (from `get_locations()`), budget radio, cuisine select with "Any", min-rating slider (0-5, step 0.5), free-text additional preferences, submit button.
- [ ] Cache the data store (`st.cache_resource`).
- [ ] Results view: summary text and any "we relaxed X" notice at top; one card per recommendation with rank, restaurant name, cuisine, rating, estimated cost and AI explanation.
- [ ] States: spinner during the LLM call; empty-result message; notice when fallback explanations were used; friendly error for unexpected failures.
- [ ] Basic layout polish (columns, readable cards, rupee formatting).

**Exit check:** `streamlit run app.py`; submitting preferences shows the five fields per recommendation exactly as listed in the problem statement; empty and failure states display correctly.

---

## Phase 5: Hardening and Documentation

**Goal:** reliable, observable, documented.

- [ ] Logging: preferences, candidate count, relaxations, latency, token usage, parse failures; never log secrets.
- [ ] Input safety: enforce length limit on free text; verify prompt-injection text in `extra` does not change output format or cause ungrounded results.
- [ ] Optional result cache keyed by the preference tuple.
- [ ] Eval set: 8-10 representative queries (including edge cases: rare location, very high rating, odd cuisine, conflicting preferences). Run against the real LLM and check relevance and that explanations only cite data facts. Record results in `docs/eval-notes.md`.
- [ ] `README.md`: setup, building the dataset, env vars, running the app and tests, project layout.
- [ ] Final review against the problem statement checklist below.

**Exit check:** the full checklist below is satisfied and the app runs from a clean clone following the README alone.

---

## Requirements Traceability

| Problem-statement requirement | Delivered in |
|---|---|
| Load and preprocess the Hugging Face Zomato dataset | Phase 1 |
| Extract name, location, cuisine, cost, rating | Phase 1 (`cleaner.py`) |
| Collect location, budget, cuisine, min rating, extra preferences | Phase 2 (models) and Phase 4 (form) |
| Filter and prepare data, pass to an LLM prompt | Phase 2 (filtering) and Phase 3 (prompting) |
| LLM ranks, explains, optionally summarises | Phase 3 (prompt, parser, service) |
| Display name, cuisine, rating, cost and AI explanation | Phase 4 (result cards) |

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Dataset schema differs from assumptions | Phase 1 profiling comes first; update architecture before coding the cleaner |
| Too few matches for narrow filters | Relaxation ladder with user-visible notice (Phase 2) |
| LLM invents restaurants or returns bad JSON | ID-only references, grounding check, repair retry, fallback (Phase 3) |
| LLM latency or outage | Timeout and retry, fallback ranking, spinner in UI |
| Prompt injection via free text | Delimit as untrusted, system-prompt rule, test in Phase 5 |
| API cost growth | Candidate cap, compact serialisation, `max_tokens`, optional cache |
