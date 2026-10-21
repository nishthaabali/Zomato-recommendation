import json

import pytest

from zomato_reco import parser
from zomato_reco.errors import ParseError

IDS = {1, 2, 3, 4, 5}


def reply(*entries, summary="Nice mix."):
    return json.dumps({"recommendations": [
        {"rank": i, "restaurant_id": e, "explanation": f"why {e}"} for i, e in enumerate(entries, 1)
    ], "summary": summary})


def ids(result):
    return [x.restaurant_id for x in result.recommendations]


def test_valid_reply():
    res = parser.parse(reply(2, 1, 3), IDS, 5)
    assert ids(res) == [2, 1, 3] and [x.rank for x in res.recommendations] == [1, 2, 3]
    assert res.summary == "Nice mix." and res.recommendations[0].explanation == "why 2"


@pytest.mark.parametrize("wrap", [
    "```json\n{}\n```", "```\n{}\n```", "Here you go:\n{}\nHope it helps!", "  \n{}\n  ",
])
def test_fenced_or_prose_wrapped(wrap):
    assert ids(parser.parse(wrap.format(reply(1, 2)), IDS, 5)) == [1, 2]


def test_bare_list_accepted():
    raw = json.dumps([{"rank": 1, "restaurant_id": 3, "explanation": "x"}])
    assert ids(parser.parse(raw, IDS, 5)) == [3]


@pytest.mark.parametrize("raw", ["", "   ", "not json at all", "{'recommendations': []}", '{"recommendations": [{"rank": 1,', "null", "42"])
def test_unusable_replies_raise(raw):
    with pytest.raises(ParseError):
        parser.parse(raw, IDS, 5)


def test_missing_recommendations_key_raises():
    with pytest.raises(ParseError, match="recommendations"):
        parser.parse('{"results": []}', IDS, 5)


def test_hallucinated_ids_dropped():
    assert ids(parser.parse(reply(99, 2, 100, 1), IDS, 5)) == [2, 1]


def test_all_hallucinated_raises():
    with pytest.raises(ParseError, match="no valid"):
        parser.parse(reply(98, 99), IDS, 5)


def test_duplicate_ids_keep_first():
    assert ids(parser.parse(reply(2, 2, 1, 2), IDS, 5)) == [2, 1]


def test_truncated_to_top_n():
    res = parser.parse(reply(1, 2, 3, 4, 5), IDS, 3)
    assert ids(res) == [1, 2, 3]


def test_fewer_than_top_n_is_accepted():
    assert len(parser.parse(reply(1, 2), IDS, 5).recommendations) == 2


def test_ranks_reordered_and_renumbered():
    raw = json.dumps({"recommendations": [
        {"rank": 3, "restaurant_id": 1, "explanation": "c"},
        {"rank": 1, "restaurant_id": 2, "explanation": "a"},
        {"rank": 1, "restaurant_id": 3, "explanation": "b"},   # duplicate rank: original order breaks the tie
        {"rank": 7, "restaurant_id": 4, "explanation": "d"},
    ]})
    res = parser.parse(raw, IDS, 5)
    assert ids(res) == [2, 3, 1, 4] and [x.rank for x in res.recommendations] == [1, 2, 3, 4]


@pytest.mark.parametrize("rid", ['"2"', "2.0"])
def test_coercible_ids_accepted(rid):
    raw = '{"recommendations": [{"rank": 1, "restaurant_id": %s, "explanation": "x"}]}' % rid
    assert ids(parser.parse(raw, IDS, 5)) == [2]


@pytest.mark.parametrize("rid", ["2.5", '"abc"', "true", "null", "[2]"])
def test_bad_ids_dropped_but_others_kept(rid):
    raw = ('{"recommendations": [{"rank": 1, "restaurant_id": %s, "explanation": "x"},'
           '{"rank": 2, "restaurant_id": 3, "explanation": "y"}]}') % rid
    assert ids(parser.parse(raw, IDS, 5)) == [3]


def test_non_dict_entries_ignored():
    raw = '{"recommendations": ["junk", 5, null, {"rank": 1, "restaurant_id": 1, "explanation": "ok"}]}'
    assert ids(parser.parse(raw, IDS, 5)) == [1]


def test_null_explanation_becomes_empty_and_missing_rank_sorts_last():
    raw = ('{"recommendations": [{"restaurant_id": 1, "explanation": null},'
           '{"rank": 1, "restaurant_id": 2, "explanation": "x"}]}')
    res = parser.parse(raw, IDS, 5)
    assert ids(res) == [2, 1] and res.recommendations[1].explanation == ""


def test_long_explanation_and_summary_are_clipped():
    raw = json.dumps({"recommendations": [{"rank": 1, "restaurant_id": 1, "explanation": "x " * 1000}],
                      "summary": "s" * 2000})
    res = parser.parse(raw, IDS, 5)
    assert len(res.recommendations[0].explanation) <= parser.MAX_EXPLANATION_CHARS
    assert len(res.summary) <= parser.MAX_SUMMARY_CHARS


def test_missing_or_blank_summary_is_none():
    assert parser.parse(reply(1, summary=""), IDS, 5).summary is None
    assert parser.parse('{"recommendations": [{"rank": 1, "restaurant_id": 1}]}', IDS, 5).summary is None


def test_truncated_json_raises():
    with pytest.raises(ParseError):
        parser.parse(reply(1, 2)[:-30], IDS, 5)
