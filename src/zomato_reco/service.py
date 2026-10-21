"""Orchestrates the pipeline: filter -> prompt -> LLM -> parse/ground -> join."""
from __future__ import annotations

import logging
import time

import pandas as pd

from zomato_reco import fallback, filtering, parser, prompting, store
from zomato_reco.errors import LLMError, ParseError
from zomato_reco.llm_client import LLMClient, get_default_client
from zomato_reco.models import (
    RecommendationItem,
    RecommendationResponse,
    RecommendationResult,
    Restaurant,
    UserPreferences,
)

log = logging.getLogger(__name__)

_UNSET = object()


def _ask(llm: LLMClient, system: str, user: str, candidate_ids: set[int], top_n: int) -> RecommendationResult:
    """Call the LLM and parse. One repair retry if the reply is unusable."""
    max_tokens = prompting.max_tokens_for(top_n)
    raw = llm.complete(system, user, max_tokens=max_tokens)
    try:
        return parser.parse(raw, candidate_ids, top_n)
    except ParseError as first:
        log.warning("LLM reply unusable (%s); asking once for a corrected reply", first)
        repair = prompting.build_repair(user, raw, str(first))
        return parser.parse(llm.complete(system, repair, max_tokens=max_tokens), candidate_ids, top_n)


def _join(result: RecommendationResult, candidates: pd.DataFrame, ai: bool, relaxed, notes) -> RecommendationResponse:
    """Attach authoritative dataset rows; displayed facts never come from LLM text."""
    by_id = {int(r["id"]): r for _, r in candidates.iterrows()}
    items = []
    for rec in result.recommendations:
        row = by_id.get(rec.restaurant_id)
        if row is None:
            continue
        explanation = rec.explanation.strip() or fallback.describe(row)
        items.append(RecommendationItem(rank=len(items) + 1, restaurant=Restaurant.from_row(row), explanation=explanation))
    return RecommendationResponse(
        items=items, summary=result.summary if ai else None, relaxed=list(relaxed), notes=notes, ai_explanations=ai,
    )


def recommend(
    prefs: UserPreferences,
    *,
    df: pd.DataFrame | None = None,
    llm: LLMClient | None | object = _UNSET,
) -> RecommendationResponse:
    """Return recommendations for `prefs`.

    `llm=None` forces the non-LLM fallback; omit it to use Groq when a key is configured.
    """
    started = time.perf_counter()
    df = store.get_df() if df is None else df
    llm = get_default_client() if llm is _UNSET else llm

    sel = filtering.select(df, prefs)
    notes = ["Your additional request was shortened to fit the length limit."] if prefs.extra_truncated else []
    if sel.empty:
        resp = RecommendationResponse.empty(sel.reason or "No matches.", sel.relaxed, sel.suggestions)
        resp.notes = notes
        return resp

    candidates = sel.candidates
    top_n = min(prefs.top_n, len(candidates))
    ai = False
    result: RecommendationResult | None = None

    if llm is not None:
        system, user = prompting.build(prefs, candidates, sel.relaxed, top_n)
        try:
            result = _ask(llm, system, user, set(candidates["id"].astype(int)), top_n)
            ai = True
        except (LLMError, ParseError) as exc:
            log.warning("Falling back to non-LLM ranking: %s", exc)
    else:
        log.info("No LLM configured; using non-LLM ranking")

    if result is None:
        result = fallback.rank(candidates, top_n)

    resp = _join(result, candidates, ai, sel.relaxed, notes)
    log.info("recommend: candidates=%d returned=%d ai=%s relaxed=%d %.2fs",
             len(candidates), len(resp.items), ai, len(sel.relaxed), time.perf_counter() - started)
    return resp
