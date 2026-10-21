"""JSON API for the restaurant recommender (deployed on Railway; the static page on Vercel calls it).

Run locally with:  uvicorn api.main:app --reload --port 8000

Endpoints
    GET  /api/health     liveness + whether the dataset is loaded
    GET  /api/meta       search-independent page data (locations, cuisines, budgets, stats, top-rated shelf)
    POST /api/recommend  one search -> {"prefs": ..., "view": ...}

Environment (see .env.example)
    ALLOWED_ORIGINS        comma-separated site origins allowed by CORS (e.g. https://my-app.vercel.app).
                           When unset, only localhost origins are allowed (development).
    ALLOWED_ORIGIN_REGEX   optional extra regex, e.g. for Vercel preview URLs
    RATE_LIMIT             per-client limit for /api/recommend (default "10/minute")
    TRUSTED_PROXY_HOPS     proxies in front of the app that append to X-Forwarded-For (default 1, as on Railway)
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi import Body, FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from slowapi import Limiter  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from zomato_reco import web  # noqa: E402

log = logging.getLogger("zomato_reco.api")

MAX_BODY_BYTES = 8 * 1024
DEV_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
META_CACHE_SECONDS = 300


def _csv(name: str) -> list[str]:
    return [v.strip().rstrip("/") for v in os.getenv(name, "").split(",") if v.strip()]


def cors_settings() -> dict:
    """CORS options from the environment; localhost-only unless ALLOWED_ORIGINS is set."""
    origins = _csv("ALLOWED_ORIGINS")
    regex = os.getenv("ALLOWED_ORIGIN_REGEX", "").strip() or None
    if not origins and not regex:
        regex = DEV_ORIGIN_REGEX
    return {"allow_origins": origins, "allow_origin_regex": regex,
            "allow_methods": ["GET", "POST"], "allow_headers": ["Content-Type"], "max_age": 600}


def client_ip(request: Request) -> str:
    """The caller's IP, honouring X-Forwarded-For only for the configured number of trusted proxy hops.

    Each trusted proxy appends the address it saw, so the entry `hops` from the right is the real client;
    anything further left can be forged by the caller.
    """
    try:
        hops = max(int(os.getenv("TRUSTED_PROXY_HOPS", "1")), 0)
    except ValueError:
        hops = 1
    forwarded = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if hops and len(forwarded) >= hops:
        return forwarded[-hops]
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        web.page_data()  # load the parquet and build the top-rated shelf once, before the first request
        log.info("Dataset loaded: %s restaurants", f"{web.restaurant_count():,}")
    except Exception:
        log.exception("Dataset failed to load; /api/health will report 503")
    yield


app = FastAPI(title="Restaurant Recommender API", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_middleware(CORSMiddleware, **cors_settings())


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "Request too large"}, status_code=413)
    return await call_next(request)


@app.exception_handler(RateLimitExceeded)
async def too_many_requests(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"detail": "Too many searches. Please wait a moment and try again."}, status_code=429)


def _page_data() -> dict:
    try:
        return web.page_data()
    except Exception:
        log.exception("Dataset unavailable")
        raise HTTPException(503, "The restaurant data is not available right now.") from None


@app.get("/api/health")
def health() -> dict:
    data = _page_data()
    return {"status": "ok", "restaurants": web.restaurant_count(), "ai": data["ai"]["active"]}


@app.get("/api/meta")
def meta() -> JSONResponse:
    return JSONResponse(_page_data(), headers={"Cache-Control": f"public, max-age={META_CACHE_SECONDS}"})


# A plain `def` endpoint runs in FastAPI's thread pool, so a slow LLM call never blocks other requests.
@app.post("/api/recommend")
@limiter.limit(lambda: os.getenv("RATE_LIMIT", "10/minute"))
def recommend(request: Request, payload: dict = Body(...)) -> JSONResponse:
    _page_data()  # 503 when the dataset is unavailable
    try:
        result = web.recommend(payload)
    except ValueError:
        raise HTTPException(422, "Invalid preferences") from None
    except Exception:
        log.exception("Recommendation failed")
        raise HTTPException(500, "We could not find restaurants just now.") from None
    return JSONResponse(result, headers={"Cache-Control": "no-store"})
