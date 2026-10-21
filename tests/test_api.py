"""API tests (FastAPI TestClient). The LLM is patched out; the dataset is the real processed parquet."""
import importlib
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_app import EchoLLM
from zomato_reco import llm_client, service, web
from zomato_reco import ui_helpers as ui
from zomato_reco.models import RecommendationResponse

SITE = "https://restaurant-recommender.vercel.app"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    for var in ("ALLOWED_ORIGINS", "ALLOWED_ORIGIN_REGEX", "RATE_LIMIT", "TRUSTED_PROXY_HOPS"):
        monkeypatch.delenv(var, raising=False)
    web.clear_caches()
    monkeypatch.setattr(llm_client, "get_default_client", lambda: EchoLLM())
    yield
    web.clear_caches()


def make_client(monkeypatch, **env) -> TestClient:
    """A fresh app (CORS settings are read at import time) with the given environment."""
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import api.main as main
    main = importlib.reload(main)
    main.limiter.reset()
    return TestClient(main.app)


def body(**kw):
    return {**ui.DEFAULT_PREFS, "location": "Indiranagar", **kw}


def test_health_reports_dataset_and_ai(monkeypatch):
    with make_client(monkeypatch) as c:
        r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "restaurants": web.restaurant_count(), "ai": True}


def test_health_says_ai_is_off_without_a_key(monkeypatch):
    monkeypatch.setattr(llm_client, "get_default_client", lambda: None)
    with make_client(monkeypatch) as c:
        assert c.get("/api/health").json()["ai"] is False


def test_meta_has_everything_the_page_needs(monkeypatch):
    with make_client(monkeypatch) as c:
        r = c.get("/api/meta")
    d = r.json()
    assert r.status_code == 200 and "max-age" in r.headers["cache-control"]
    assert d["locations"][0] == ui.ALL_CITY_LABEL and "Indiranagar" in d["locations"]
    assert d["cuisines"]["top"] and "Italian" in d["cuisines"]["all"]
    assert [b["value"] for b in d["budgets"]] == ["low", "medium", "high"]
    assert d["stats"]["outlets"].endswith("+") and d["defaults"] == ui.DEFAULT_PREFS and d["max_extra"] == 300
    assert d["trending"][ui.ALL_CITY_LABEL] and d["ai"]["active"] is True
    assert "gsk_" not in json.dumps(d)


def test_recommend_returns_ranked_items(monkeypatch):
    with make_client(monkeypatch) as c:
        r = c.post("/api/recommend", json=body(cuisine="Italian", top_n=3))
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    out = r.json()
    assert out["prefs"]["cuisine"] == "Italian"
    items = out["view"]["items"]
    assert 1 <= len(items) <= 3 and [i["rank"] for i in items] == list(range(1, len(items) + 1))
    assert items[0]["explanation"].startswith("Because") and out["view"]["summary"] == "A fine selection."


@pytest.mark.parametrize("bad", [
    {"location": "Atlantis"}, {"budget": "lavish"}, {"cuisine": "Martian"}, {"min_rating": "high"}, {"extra": ["x"]},
])
def test_invalid_preferences_get_422(monkeypatch, bad):
    with make_client(monkeypatch) as c:
        r = c.post("/api/recommend", json=body(**bad))
    assert r.status_code == 422 and r.json() == {"detail": "Invalid preferences"}


def test_non_object_body_is_rejected(monkeypatch):
    with make_client(monkeypatch) as c:
        assert c.post("/api/recommend", json=["not", "an", "object"]).status_code == 422
        assert c.post("/api/recommend", content=b"nope", headers={"content-type": "application/json"}).status_code == 422


def test_unexpected_error_is_a_generic_500(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(service, "recommend", boom)
    with make_client(monkeypatch) as c:
        r = c.post("/api/recommend", json=body())
    assert r.status_code == 500 and "secret" not in r.text
    assert r.json() == {"detail": "We could not find restaurants just now."}


def test_oversized_body_is_refused(monkeypatch):
    with make_client(monkeypatch) as c:
        r = c.post("/api/recommend", json=body(extra="x" * 20000))
    assert r.status_code == 413


def test_missing_dataset_gives_503_not_a_crash(monkeypatch):
    def broken():
        raise RuntimeError("no parquet")
    monkeypatch.setattr(web, "page_data", broken)
    with make_client(monkeypatch) as c:
        assert c.get("/api/health").status_code == 503
        assert c.get("/api/meta").status_code == 503
        assert c.post("/api/recommend", json=body()).status_code == 503


def test_rate_limit_returns_429_with_a_friendly_message(monkeypatch):
    monkeypatch.setattr(service, "recommend", lambda *a, **k: RecommendationResponse.empty("none"))
    with make_client(monkeypatch, RATE_LIMIT="2/minute") as c:
        codes = [c.post("/api/recommend", json=body()).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_rate_limit_message_is_friendly(monkeypatch):
    monkeypatch.setattr(service, "recommend", lambda *a, **k: RecommendationResponse.empty("none"))
    with make_client(monkeypatch, RATE_LIMIT="1/minute") as c:
        c.post("/api/recommend", json=body())
        limited = c.post("/api/recommend", json=body())
    assert limited.status_code == 429 and "Too many searches" in limited.json()["detail"]


def test_rate_limit_is_per_client_using_the_trusted_forwarded_ip(monkeypatch):
    monkeypatch.setattr(service, "recommend", lambda *a, **k: RecommendationResponse.empty("none"))
    with make_client(monkeypatch, RATE_LIMIT="1/minute") as c:
        def post(xff):
            return c.post("/api/recommend", json=body(), headers={"X-Forwarded-For": xff}).status_code
        assert post("1.1.1.1") == 200 and post("1.1.1.1") == 429
        assert post("2.2.2.2") == 200            # a different client is unaffected
        # a forged leading entry does not buy a fresh allowance: the rightmost (proxy-appended) entry counts
        assert post("9.9.9.9, 1.1.1.1") == 429


def test_cors_allows_only_the_configured_origin(monkeypatch):
    with make_client(monkeypatch, ALLOWED_ORIGINS=f"{SITE}/") as c:
        ok = c.get("/api/meta", headers={"Origin": SITE})
        other = c.get("/api/meta", headers={"Origin": "https://evil.example"})
        local = c.get("/api/meta", headers={"Origin": "http://localhost:3000"})
        pre = c.options("/api/recommend", headers={"Origin": SITE, "Access-Control-Request-Method": "POST",
                                                   "Access-Control-Request-Headers": "content-type"})
    assert ok.headers["access-control-allow-origin"] == SITE
    assert "access-control-allow-origin" not in other.headers and "access-control-allow-origin" not in local.headers
    assert pre.status_code == 200 and pre.headers["access-control-allow-origin"] == SITE


def test_cors_defaults_to_localhost_only(monkeypatch):
    with make_client(monkeypatch) as c:
        local = c.get("/api/meta", headers={"Origin": "http://localhost:5173"})
        remote = c.get("/api/meta", headers={"Origin": SITE})
    assert local.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in remote.headers


def test_cors_regex_allows_preview_deployments(monkeypatch):
    preview = "https://restaurant-recommender-git-feature-me.vercel.app"
    env = {"ALLOWED_ORIGINS": SITE, "ALLOWED_ORIGIN_REGEX": r"https://restaurant-recommender-.*\.vercel\.app"}
    with make_client(monkeypatch, **env) as c:
        assert c.get("/api/meta", headers={"Origin": preview}).headers["access-control-allow-origin"] == preview


def test_rate_limited_responses_still_carry_cors_headers(monkeypatch):
    monkeypatch.setattr(service, "recommend", lambda *a, **k: RecommendationResponse.empty("none"))
    with make_client(monkeypatch, ALLOWED_ORIGINS=SITE, RATE_LIMIT="1/minute") as c:
        h = {"Origin": SITE}
        c.post("/api/recommend", json=body(), headers=h)
        r = c.post("/api/recommend", json=body(), headers=h)
    assert r.status_code == 429 and r.headers["access-control-allow-origin"] == SITE  # the page can read the error


def test_docs_endpoints_are_not_exposed(monkeypatch):
    with make_client(monkeypatch) as c:
        assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404
