"""Turn raw LLM text into validated, grounded recommendations. Never trusts the model."""
from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from zomato_reco.errors import ParseError
from zomato_reco.models import Recommendation, RecommendationResult

log = logging.getLogger(__name__)

MAX_EXPLANATION_CHARS = 600
MAX_SUMMARY_CHARS = 500
_FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


def extract_json(raw: str):
    """Parse JSON from a reply that may have code fences or prose around it."""
    text = _FENCE.sub("", (raw or "").strip()).strip()
    if not text:
        raise ParseError("empty response")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Take the outermost object/array if the model wrapped it in prose.
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = text.find(open_c), text.rfind(close_c)
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ParseError("response is not valid JSON")


def _clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def parse(raw: str, candidate_ids: set[int], top_n: int) -> RecommendationResult:
    """Validate and ground a reply.

    - Entries that are malformed, not in `candidate_ids`, or duplicated are dropped.
    - Remaining entries are ordered by the model's rank, renumbered 1..n and cut to `top_n`.
    - Raises ParseError if the reply is unusable or nothing valid remains.
    """
    data = extract_json(raw)
    if isinstance(data, list):
        data = {"recommendations": data}
    if not isinstance(data, dict) or not isinstance(data.get("recommendations"), list):
        raise ParseError("JSON has no 'recommendations' list")

    kept: list[tuple[int, int, Recommendation]] = []  # (model rank, position, rec)
    seen: set[int] = set()
    dropped = 0
    for pos, item in enumerate(data["recommendations"]):
        try:
            if isinstance(item, dict) and isinstance(item.get("restaurant_id"), bool):
                raise ValueError("bool id")
            rec = Recommendation.model_validate(item)
        except (ValidationError, ValueError):
            dropped += 1
            continue
        if rec.restaurant_id not in candidate_ids or rec.restaurant_id in seen:
            dropped += 1  # hallucinated or duplicate
            continue
        seen.add(rec.restaurant_id)
        kept.append((rec.rank, pos, rec))

    if dropped:
        log.warning("Parser dropped %d invalid/ungrounded/duplicate entries", dropped)
    if not kept:
        raise ParseError("no valid recommendations from the candidate list")

    kept.sort(key=lambda t: (t[0], t[1]))
    recs = [
        Recommendation(rank=i, restaurant_id=r.restaurant_id, explanation=_clip(r.explanation, MAX_EXPLANATION_CHARS))
        for i, (_, _, r) in enumerate(kept[:top_n], start=1)
    ]
    summary = data.get("summary")
    summary = _clip(summary, MAX_SUMMARY_CHARS) if isinstance(summary, str) and summary.strip() else None
    return RecommendationResult(recommendations=recs, summary=summary)
