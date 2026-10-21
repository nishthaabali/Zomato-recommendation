# Deployment Plan: Backend on Railway, Frontend on Vercel

Companion to [architecture.md](architecture.md) and [implementation-plan.md](implementation-plan.md). This document describes how to take the restaurant recommender from a local Streamlit app to a public deployment with the **backend on Railway** and the **frontend on Vercel**.

---

## 1. Summary

| | Today (local) | After deployment |
|---|---|---|
| UI | Stitch page rendered as a Streamlit v2 component (`frontend/src/app.js`) | Same `app.js`, served as a static site on **Vercel** |
| Server | Streamlit (`app.py`) holds data + calls the recommender | Small JSON API (FastAPI) on **Railway**, reusing the same Python modules |
| Browser ↔ server | Streamlit websocket (data in, trigger values out) | HTTPS `fetch` to `GET /api/meta` and `POST /api/recommend` |
| Secrets | `.env` on the developer's machine | `GROQ_API_KEY` set only on Railway |

**Why code changes are needed first:** the current frontend is not a standalone website. It is mounted by Streamlit and talks to Python through Streamlit's websocket. Vercel hosts static files and short-lived serverless functions; it cannot run a long-lived Streamlit server. So the deployment requires:

1. A **JSON API** on Railway exposing what Streamlit currently passes to the page.
2. A **static build** of the page for Vercel, with a ~60-line bootstrap that calls the API instead of Streamlit.

The recommender pipeline (`filtering`, `prompting`, `llm_client`, `service`, `ui_helpers`) is reused unchanged. `frontend/src/app.js` is reused unchanged: the bootstrap calls the same default-exported function Streamlit calls, with the same `data` shape.

> **Simpler alternative (not the requested setup):** deploy the existing Streamlit app as a single service on Railway (`streamlit run app.py --server.port $PORT --server.address 0.0.0.0`). It needs no code changes, but gives no Vercel frontend. Section 10 covers it as a fallback.

---

## Implementation Status

All code for Phases 1 and 2 is written and tested locally. What remains is manual: Phase 0 (git/GitHub) and Phase 3 (the dashboards).

| Phase | Status | Notes |
|---|---|---|
| 0. Repository setup | **Not done** (needs you) | `.python-version` is added. `git init`, the first commit and the GitHub push are left for you, since they publish the code |
| 1. Backend API | Done | `src/zomato_reco/web.py`, `api/main.py`, `railway.json`, split requirements, `tests/test_api.py` (21 tests) |
| 2. Static frontend | Done | `frontend/web/{index.html,main.js}`, `frontend/scripts/{build-web,serve-web}.mjs`, `frontend/vercel.json` |
| 3. Go live | Not done (needs you) | Follow section 7 |

Verified locally (API on :8000, static site on :3000, a different origin, as in production): the page loads and shows the AI pill, all 94 locations and 3 photos with none broken; a search returns 5 cards with no broken images; Shuffle and Reset work; with the API stopped the page shows "Waking up the server…" and then a "Try again" screen; a search that fails mid-session keeps the earlier results and shows the red banner. The home screen differs from the Streamlit render in 0.1% of pixels. All 238 tests pass.

**Run it locally** (two terminals):

```bash
uvicorn api.main:app --reload --port 8000                          # API (repo root)
cd frontend && npm install && npm run build:web && npm run serve:web   # site at http://localhost:3000
```

`streamlit run app.py` still works for local development and shares the same `web.py`.

**Deviations from the original plan:**
- `X-Forwarded-For` handling uses a `TRUSTED_PROXY_HOPS` setting (default 1): the rate limiter counts the entry added by the trusted proxy, not the leftmost one, which a caller could forge.
- The API disables `/docs` and `/openapi.json`, and refuses request bodies over 8 KB (413).
- `/api/meta` is cached for 5 minutes (`Cache-Control`); `/api/recommend` is `no-store`.
- `vercel.json` also sets `X-Content-Type-Options`, `Referrer-Policy` and `X-Frame-Options`. Photos are cached for 1 day, not a year, because their file names do not change when an image is replaced.
- `build:web` fails fast on Vercel if `API_BASE_URL` is missing or not `https://`, so a site pointing at `localhost` can never be published by accident. It fails before touching `dist/`.
- `requirements-dev.txt` pins `streamlit>=1.66`, the version `st.components.v2` was verified on.

---

## 2. Target Architecture

```
 Browser
   │  1. GET https://<app>.vercel.app          (static: index.html, app.js, app.css, images)
   ▼
┌──────────────────────────┐
│  Vercel (static site)    │  frontend/dist/
│  index.html + main.js    │  main.js mounts app.js and talks to the API
└───────────┬──────────────┘
            │  2. GET  /api/meta        (locations, cuisines, budgets, stats, top-rated shelf)
            │  3. POST /api/recommend   (preferences → ranked restaurants)
            ▼  HTTPS + CORS
┌──────────────────────────┐        ┌──────────────────┐
│  Railway (FastAPI)       │ ─────▶ │  Groq LLM API    │
│  api/main.py             │        └──────────────────┘
│  data/processed/*.parquet│
└──────────────────────────┘
```

The browser calls Railway directly over HTTPS. The Groq key never leaves Railway.

---

## 3. Current State and Gaps

| Item | State | Action |
|---|---|---|
| Git repository | **Not initialised** | Create a repo and push to GitHub (both platforms deploy from GitHub) |
| Processed dataset (`data/processed/restaurants.parquet`, 736 KB + `metadata.json`) | Present, not ignored | **Commit it**, so the server does not download the 148 MB raw dataset on boot |
| Raw dataset (`data/raw/`, 148 MB) | Ignored by `.gitignore` | Keep ignored |
| `.env` | Ignored | Keep ignored; set variables in Railway instead |
| `frontend/node_modules/` | Ignored | Keep ignored |
| Python version | 3.12 locally | Pin with `.python-version` |
| HTTP API | None (Streamlit only) | Add `api/main.py` (Phase 1) |
| Standalone page | None (Streamlit component only) | Add `frontend/web/` + build script (Phase 2) |
| Rate limiting | None | Add before going public (each search can cost a Groq call) |

---

## 4. Phase 0: Repository Setup

1. `git init`, commit the project. Confirm `data/processed/restaurants.parquet` and `metadata.json` are included and `.env`, `.venv/`, `data/raw/`, `frontend/node_modules/` are not.
2. Push to a GitHub repository (private is fine for both Railway and Vercel).
3. Add `.python-version` containing `3.12`.

**Exit check:** `git ls-files | grep -E "parquet|metadata.json|\.env$"` lists the two processed files and no `.env`.

---

## 5. Phase 1: Backend API (Railway)

### 5.1 Share the page logic between Streamlit and the API

`app.py` currently builds the page data (`load_store`, `ai_info`) and runs searches (`run_search`). Move that logic into a Streamlit-free module so both entry points use it:

- New `src/zomato_reco/web.py`:
  - `page_data() -> dict`: locations, cuisines, budgets, stats, trending, AI info, `max_extra`, `defaults` (the static part of the component's `data`).
  - `recommend(request: dict) -> dict`: `ui.parse_request` → `service.recommend` → `ui.response_view`; returns `{"prefs": ..., "view": ...}` and raises `ValueError` for invalid input.
- `app.py` keeps working by calling these functions, so local development with `streamlit run app.py` is unchanged.

### 5.2 API endpoints (`api/main.py`)

| Method | Path | Returns | Errors |
|---|---|---|---|
| GET | `/api/health` | `{"status": "ok", "restaurants": 12438, "ai": true}` | 503 if data failed to load |
| GET | `/api/meta` | `web.page_data()` | 503 if data failed to load |
| POST | `/api/recommend` | `{"prefs": {...}, "view": {...}}` | 422 invalid request, 429 rate limited, 500 generic message (no internal details) |

Sketch:

```python
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=settings_origins(), allow_origin_regex=preview_regex(),
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

@app.on_event("startup")          # or a lifespan handler
def warm():                       # load the parquet + build the top-rated shelf once
    web.page_data()

@app.get("/api/health")
def health(): ...

@app.get("/api/meta")
def meta(): return web.page_data()

@app.post("/api/recommend")
def recommend(request: dict):
    try:
        return web.recommend(request)
    except ValueError:
        raise HTTPException(422, "Invalid preferences")
    except Exception:
        log.exception("Recommendation failed")
        raise HTTPException(500, "We could not find restaurants just now.")
```

Notes:
- `service.recommend` is synchronous and may wait up to `LLM_TOTAL_BUDGET_S` (45 s) on Groq. Declare the endpoint with plain `def` (not `async def`) so FastAPI runs it in its thread pool and other requests are not blocked.
- **Rate limiting:** add a per-IP limit on `/api/recommend` (e.g. `slowapi`, ~10 requests/minute). Railway sits behind a proxy, so read the client IP from `X-Forwarded-For`.
- **Request size:** reject bodies over a few KB; `parse_request` already caps `extra` at 300 characters.

### 5.3 Dependencies

Split requirements so the server installs only what it needs:

- `requirements.txt` (what Railway installs): `pandas`, `pyarrow`, `pydantic`, `groq`, `python-dotenv`, `fastapi`, `uvicorn[standard]`, `slowapi`, `datasets` (only needed if the parquet must be rebuilt; can be dropped later once the committed parquet is relied on).
- `requirements-dev.txt`: `-r requirements.txt` plus `streamlit` and `pytest`.

### 5.4 Railway configuration

`railway.json` at the repo root:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "deploy": {
    "startCommand": "uvicorn api.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/health",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

Railway detects the Python project from `requirements.txt` and `.python-version`, and provides `$PORT`.

### 5.5 Environment variables (Railway)

| Variable | Required | Value |
|---|---|---|
| `GROQ_API_KEY` | Yes, for AI explanations | Your Groq key. Without it the API still works and returns data-based explanations |
| `LLM_MODEL` | No | Default `openai/gpt-oss-120b` |
| `CANDIDATE_LIMIT`, `LLM_TEMPERATURE`, `LLM_TIMEOUT_S` | No | Defaults from `.env.example` |
| `ALLOWED_ORIGINS` | Yes | The Vercel production URL, e.g. `https://restaurant-recommender.vercel.app` (comma-separated if several) |
| `ALLOWED_ORIGIN_REGEX` | Optional | e.g. `https://restaurant-recommender-.*\.vercel\.app` to allow Vercel preview deployments |
| `RATE_LIMIT` | No | Per-client limit on `/api/recommend`, default `10/minute` |
| `TRUSTED_PROXY_HOPS` | No | Proxies in front of the app that append to `X-Forwarded-For`; default `1` (Railway). Leave as is unless the network layout changes |

If `ALLOWED_ORIGINS` and `ALLOWED_ORIGIN_REGEX` are both unset, the API only accepts `localhost` origins, so **a production deploy without `ALLOWED_ORIGINS` will not work from the Vercel site**.

### 5.6 Tests

- Move the search/view assertions from `tests/test_app.py` to the shared `web` module.
- Add `tests/test_api.py` using FastAPI's `TestClient` (LLM patched out, as today): health, meta shape, a valid search, 422 on invalid input, 500 without leaking details, CORS headers for an allowed origin and none for others.

**Exit check:** `uvicorn api.main:app` runs locally; `curl localhost:8000/api/meta` returns locations; a `POST /api/recommend` returns 5 ranked items; all tests pass.

---

## 6. Phase 2: Static Frontend (Vercel)

### 6.1 Standalone bootstrap

`frontend/src/app.js` stays as is. Add:

- `frontend/web/index.html`: page shell (title, favicon, Google Fonts links, `<div id="app">`, loads `config.js` then `main.js` as a module).
- `frontend/web/main.js`: creates a shadow root on `#app` (the same isolation Streamlit uses), adds `<link rel="stylesheet" href="app.css">` inside it, and mounts the page:

```js
import mount from './app.js';

const API = window.RR_CONFIG.apiBase;
const host = document.getElementById('app').attachShadow({ mode: 'open' });
host.innerHTML = '<link rel="stylesheet" href="app.css">';

let state = { view: null, error: false, served: 0 };
let meta;

function render() {
  mount({ data: { ...meta, ...state }, parentElement: host, setTriggerValue: onTrigger });
}

async function onTrigger(name, payload) {
  if (name === 'reset') { state = { ...state, prefs: meta.defaults, view: null, error: false, served: Date.now() }; return render(); }
  if (name !== 'submit') return;
  try {
    const res = await fetch(`${API}/api/recommend`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    if (!res.ok) throw new Error(res.status);
    const { prefs, view } = await res.json();
    state = { prefs, view, error: false, served: payload.nonce };
  } catch {
    state = { ...state, error: true, served: payload.nonce };
  }
  render();
}

meta = await (await fetch(`${API}/api/meta`)).json();
state.prefs = meta.defaults;
render();
```

The bootstrap needs a loading state while `/api/meta` is fetched (Railway may cold-start) and an error message if it fails.

### 6.2 Build

Add a `build:web` script to `frontend/package.json` (a small Node script, no new dependencies) that produces `frontend/dist/`:

```
dist/
  index.html
  main.js
  app.js              ← copied from src/app.js
  app.css             ← Tailwind build (same command as today)
  config.js           ← window.RR_CONFIG = { apiBase: process.env.API_BASE_URL }
  app/static/img/*.jpg ← copied from ../static/img (keeps the image paths the API returns unchanged)
```

`config.js` is generated at build time from Vercel's `API_BASE_URL` variable, so the same code works locally (`http://localhost:8000`) and in production.

### 6.3 Vercel configuration

- Import the GitHub repo in Vercel and set **Root Directory** to `frontend`.
- Framework preset: **Other**.
- `frontend/vercel.json` (already in the repo) sets the build command (`npm run build:web`), the output directory (`dist`), security headers and a 1-day cache for the photos.
- The build copies `../static/img`, which is outside the root directory. In the Vercel project, confirm **Settings > General > "Include source files outside of the Root Directory in the Build Step"** is enabled. If it is not, the build stops with a message saying exactly this (it never publishes a site without photos).
- Environment variable: `API_BASE_URL` = the Railway public URL (e.g. `https://restaurant-recommender-production.up.railway.app`). Set it for Production, and for Preview if previews should work.

**Exit check:** `API_BASE_URL=http://localhost:8000 npm run build:web` then serving `dist/` locally (e.g. `npx serve dist`) shows the home page, a search returns results, and the page looks the same as the Streamlit version.

---

## 7. Phase 3: Go Live (order matters)

0. **Do Phase 0 first:** `git init`, commit (check `git ls-files` includes `data/processed/` and no `.env`), and push to GitHub.
1. **Deploy the backend.** Create a Railway project from the GitHub repo and set the variables from 5.5 (use a placeholder for `ALLOWED_ORIGINS` for now, e.g. `https://example.com`). Generate a public domain under the service's networking settings. Wait for the health check to pass.
2. **Smoke-test the API:**
   ```bash
   curl https://<railway-domain>/api/health
   curl https://<railway-domain>/api/meta | head -c 300
   curl -X POST https://<railway-domain>/api/recommend -H "Content-Type: application/json" \
     -d '{"location":"Indiranagar","budget":"medium","cuisine":null,"min_rating":3.5,"top_n":5,"extra":"date night"}'
   ```
3. **Deploy the frontend.** Create the Vercel project (6.3) with `API_BASE_URL` set to the Railway domain. Note the production URL.
4. **Lock down CORS.** Set `ALLOWED_ORIGINS` on Railway to the Vercel production URL (plus the preview regex if wanted) and redeploy the backend.
5. **Verify end to end** (section 8).

---

## 8. Verification Checklist

- [ ] Home page loads on the Vercel URL with fonts, icons, photos and the "Top Rated Around Bangalore" shelf.
- [ ] Header pill shows "Zomato AI Active" (it shows "AI Offline · Data Mode" if `GROQ_API_KEY` is missing on Railway).
- [ ] A search (Indiranagar, Medium, Date night) shows ranked cards and the green "AI Dining Insight" banner.
- [ ] Edit Preferences modal, Apply Filters, Shuffle Picks, Reset and Share Shortlist all work. Share uses the clipboard, which needs HTTPS (Vercel provides it).
- [ ] Phone width (390 px) and tablet width (820 px) render correctly.
- [ ] Stopping the Railway service shows the red "Something went wrong" banner instead of a broken page.
- [ ] Browser devtools: no CORS errors, no console errors, no failed image requests.
- [ ] Requests from an origin not in `ALLOWED_ORIGINS` are refused by the browser.
- [ ] Rate limit: repeated searches beyond the limit return 429 and the page shows an error.
- [ ] The Groq key is not in the frontend: `grep -r "gsk_" frontend/dist` finds nothing.

---

## 9. Operations

| Topic | Plan |
|---|---|
| Deploys | Both platforms redeploy automatically on push to the main branch. Vercel also builds a preview per pull request |
| Rollback | Railway: redeploy the previous successful deployment. Vercel: promote the previous production deployment |
| Logs | Railway service logs (startup, `Recommendation failed` errors); Vercel build logs |
| Health | Railway health check on `/api/health` restarts the service if it stops responding |
| Cost | Railway bills by usage, and the API keeps the dataset in memory (low hundreds of MB). Groq bills per token, so the rate limit is the main cost control. Check current pricing for both before launch |
| Timeouts | One search can take up to `LLM_TOTAL_BUDGET_S` (45 s) when Groq retries. Confirm Railway's current HTTP request timeout is above that |
| Dataset updates | Rebuild locally with `python scripts/build_dataset.py`, commit the new `data/processed/` files, push |
| Secrets rotation | Change `GROQ_API_KEY` in Railway and redeploy; nothing to change on Vercel |

---

## 10. Fallback: Streamlit on Railway Only

If the split is not worth the work right now, the current app deploys as one Railway service with no code changes:

- Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
- Variables: `GROQ_API_KEY` (and the optional LLM settings).
- Keep `requirements.txt` as it is today (it includes Streamlit).

The UI is identical. The cost is losing Vercel's CDN and preview deployments, and a websocket connection per visitor.

---

## 11. Decisions to Confirm

1. **Rate limit value** for `/api/recommend` (suggested: 10/minute per IP).
2. **Preview deployments:** allow Vercel preview URLs to call the production API (regex CORS), or production only.
3. **Custom domains** for the site and API (both platforms support them; CORS must list the final site domain).
4. **Keep the Streamlit entry point** (`app.py`) for local development after the split. Suggested: yes, since it shares `web.py` and costs nothing to keep.

---

## 12. Work Breakdown

| # | Task | Files |
|---|---|---|
| 0 | Git repo, `.python-version`, commit processed data | repo root |
| 1 | Extract shared page/search logic | `src/zomato_reco/web.py`, `app.py` |
| 2 | FastAPI app with CORS, rate limit, health | `api/main.py` |
| 3 | Split requirements | `requirements.txt`, `requirements-dev.txt` |
| 4 | API tests, adjust app tests | `tests/test_api.py`, `tests/test_app.py` |
| 5 | Standalone page + bootstrap | `frontend/web/index.html`, `frontend/web/main.js` |
| 6 | Static build script | `frontend/scripts/build-web.mjs`, `frontend/package.json` |
| 7 | Platform config | `railway.json`, `frontend/vercel.json` |
| 8 | Deploy backend, then frontend, then lock CORS | Railway + Vercel dashboards |
| 9 | Run the verification checklist | n/a |
