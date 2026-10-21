from types import SimpleNamespace

import groq
import httpx
import pytest

from zomato_reco import config
from zomato_reco.errors import LLMError
from zomato_reco.llm_client import GroqClient, get_default_client

REQ = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


def http_error(cls, status, headers=None):
    return cls("boom", response=httpx.Response(status, request=REQ, headers=headers or {}), body=None)


def ok(text='{"recommendations": []}'):
    msg = SimpleNamespace(content=text)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))


class FakeSDK:
    """Plays back a list of results; exceptions in the list are raised."""

    def __init__(self, *script):
        self.script, self.calls = list(script), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def client(sdk, **kw):
    sleeps = []
    c = GroqClient(model="m", temperature=0.2, timeout_s=5, sdk_client=sdk, sleep=sleeps.append, **kw)
    return c, sleeps


def test_success_sends_json_mode_and_messages():
    sdk = FakeSDK(ok("hello"))
    c, _ = client(sdk)
    assert c.complete("SYS", "USER", max_tokens=123) == "hello"
    call = sdk.calls[0]
    assert call["model"] == "m" and call["temperature"] == 0.2 and call["max_tokens"] == 123
    assert call["response_format"] == {"type": "json_object"}
    assert call["messages"] == [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]


def test_reasoning_model_gets_low_effort_and_token_headroom():
    sdk = FakeSDK(ok("x"))
    c = GroqClient(model="openai/gpt-oss-120b", temperature=0.2, timeout_s=5, sdk_client=sdk)
    c.complete("s", "u", max_tokens=1000)
    call = sdk.calls[0]
    assert call["reasoning_effort"] == "low" and call["max_tokens"] == 1000 + config.LLM_REASONING_HEADROOM


def test_regular_model_gets_no_reasoning_params():
    sdk = FakeSDK(ok("x"))
    c, _ = client(sdk)  # model "m"
    c.complete("s", "u", max_tokens=1000)
    assert "reasoning_effort" not in sdk.calls[0] and sdk.calls[0]["max_tokens"] == 1000


@pytest.mark.parametrize("resp", [SimpleNamespace(choices=[], usage=None),
                                  SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None))], usage=None)])
def test_empty_reply_returns_empty_string(resp):
    c, _ = client(FakeSDK(resp))
    assert c.complete("s", "u") == ""


def test_rate_limit_retried_honouring_retry_after():
    sdk = FakeSDK(http_error(groq.RateLimitError, 429, {"retry-after": "2"}), ok("fine"))
    c, sleeps = client(sdk)
    assert c.complete("s", "u") == "fine"
    assert sleeps == [2.0] and len(sdk.calls) == 2


def test_retry_after_is_capped():
    sdk = FakeSDK(http_error(groq.RateLimitError, 429, {"retry-after": "600"}), ok("fine"))
    c, sleeps = client(sdk)
    c.complete("s", "u")
    assert sleeps == [config.LLM_MAX_RETRY_WAIT_S]


def test_server_errors_retried_with_backoff_then_succeed():
    sdk = FakeSDK(http_error(groq.InternalServerError, 503), http_error(groq.InternalServerError, 500), ok("fine"))
    c, sleeps = client(sdk)
    assert c.complete("s", "u") == "fine"
    assert sleeps == [1.0, 2.0]


def test_persistent_server_error_raises_after_bounded_attempts():
    sdk = FakeSDK(*[http_error(groq.InternalServerError, 500) for _ in range(10)])
    c, sleeps = client(sdk)
    with pytest.raises(LLMError, match="after retries"):
        c.complete("s", "u")
    assert len(sdk.calls) == config.LLM_MAX_ATTEMPTS and len(sleeps) == config.LLM_MAX_ATTEMPTS - 1


@pytest.mark.parametrize("exc", [groq.APIConnectionError(request=REQ), groq.APITimeoutError(request=REQ)])
def test_network_errors_and_timeouts_are_retried(exc):
    sdk = FakeSDK(exc, ok("fine"))
    c, _ = client(sdk)
    assert c.complete("s", "u") == "fine"


@pytest.mark.parametrize("cls,status,message", [
    (groq.AuthenticationError, 401, "API key"),
    (groq.PermissionDeniedError, 403, "API key"),
    (groq.NotFoundError, 404, "not found"),
    (groq.BadRequestError, 400, "rejected the request"),
])
def test_non_transient_errors_fail_immediately(cls, status, message):
    sdk = FakeSDK(http_error(cls, status), ok("never reached"))
    c, sleeps = client(sdk)
    with pytest.raises(LLMError, match=message):
        c.complete("s", "u")
    assert len(sdk.calls) == 1 and sleeps == []


def test_error_message_never_leaks_api_key():
    sdk = FakeSDK(http_error(groq.AuthenticationError, 401))
    c, _ = client(sdk)
    with pytest.raises(LLMError) as e:
        c.complete("s", "u")
    assert "gsk_" not in str(e.value)


def test_total_time_budget_stops_retries():
    ticks = iter([0.0, 44.5, 90.0, 130.0])  # after the first failure, 44.5s + 1s backoff exceeds 45s
    sdk = FakeSDK(*[http_error(groq.InternalServerError, 500) for _ in range(5)])
    c, sleeps = client(sdk, clock=lambda: next(ticks))
    with pytest.raises(LLMError):
        c.complete("s", "u")
    assert len(sdk.calls) == 1 and sleeps == []

def test_get_default_client_none_without_key(monkeypatch):
    monkeypatch.setattr(config, "settings", config.Settings(None, "m", 20, 0.3, 30))
    assert get_default_client() is None


def test_constructing_without_key_raises_config_error(monkeypatch):
    monkeypatch.setattr(config, "settings", config.Settings(None, "m", 20, 0.3, 30))
    with pytest.raises(config.ConfigError):
        GroqClient()
