"""LLM provider abstraction with a Groq implementation."""
from __future__ import annotations

import logging
import time
from typing import Callable, Protocol

from zomato_reco import config
from zomato_reco.errors import LLMError

log = logging.getLogger(__name__)


class LLMClient(Protocol):
    def complete(self, system: str, user: str, max_tokens: int | None = None) -> str:
        """Return the model's text reply. Raise LLMError on failure."""
        ...


class GroqClient:
    """Chat-completions client for Groq using JSON mode.

    Retries only transient failures (429, 5xx, connection/timeout) with backoff,
    inside an overall time budget. Auth and bad-request errors fail immediately.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        timeout_s: float | None = None,
        *,
        sdk_client=None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        s = config.settings
        self.model = model or s.llm_model
        self.temperature = s.llm_temperature if temperature is None else temperature
        self.timeout_s = timeout_s or s.llm_timeout_s
        self._sleep, self._clock = sleep, clock
        if sdk_client is not None:
            self._sdk = sdk_client
        else:
            from groq import Groq

            # max_retries=0: retries are handled here so the total time stays bounded.
            self._sdk = Groq(api_key=api_key or config.require_api_key(), timeout=self.timeout_s, max_retries=0)

    # -- public ---------------------------------------------------------------
    def complete(self, system: str, user: str, max_tokens: int | None = None) -> str:
        import groq

        started = self._clock()
        last: Exception | None = None
        for attempt in range(1, config.LLM_MAX_ATTEMPTS + 1):
            try:
                return self._call(system, user, max_tokens)
            except (groq.AuthenticationError, groq.PermissionDeniedError) as exc:
                raise LLMError(f"Groq rejected the API key ({exc.status_code}). Check GROQ_API_KEY.") from exc
            except groq.NotFoundError as exc:
                raise LLMError(f"Groq model '{self.model}' not found. Check LLM_MODEL.") from exc
            except groq.BadRequestError as exc:
                raise LLMError(f"Groq rejected the request: {exc}") from exc
            except (groq.RateLimitError, groq.InternalServerError, groq.APIConnectionError) as exc:
                last = exc  # APITimeoutError is a subclass of APIConnectionError
            except groq.APIStatusError as exc:
                if exc.status_code < 500:
                    raise LLMError(f"Groq error {exc.status_code}: {exc}") from exc
                last = exc
            except groq.GroqError as exc:
                raise LLMError(f"Groq client error: {exc}") from exc

            wait = self._backoff(attempt, last)
            elapsed = self._clock() - started
            if attempt == config.LLM_MAX_ATTEMPTS or elapsed + wait >= config.LLM_TOTAL_BUDGET_S:
                break
            log.warning("Groq call failed (%s); retry %d in %.1fs", type(last).__name__, attempt, wait)
            self._sleep(wait)

        raise LLMError(f"Groq call failed after retries: {type(last).__name__}: {last}") from last

    # -- internals ------------------------------------------------------------
    @property
    def _is_reasoning_model(self) -> bool:
        return "gpt-oss" in self.model or "qwen3" in self.model

    def _call(self, system: str, user: str, max_tokens: int | None) -> str:
        extra: dict = {}
        if self._is_reasoning_model:
            # Hidden reasoning tokens count toward max_tokens; without headroom the
            # visible answer comes back empty. Keep reasoning short for this task.
            if "gpt-oss" in self.model:
                extra["reasoning_effort"] = "low"
            if max_tokens is not None:
                max_tokens += config.LLM_REASONING_HEADROOM
        resp = self._sdk.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self.temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            **extra,
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            log.info("Groq usage: prompt=%s completion=%s", getattr(usage, "prompt_tokens", "?"),
                     getattr(usage, "completion_tokens", "?"))
        if not resp.choices:
            return ""
        return resp.choices[0].message.content or ""

    @staticmethod
    def _retry_after(exc: Exception) -> float | None:
        response = getattr(exc, "response", None)
        raw = response.headers.get("retry-after") if response is not None else None
        try:
            return float(raw) if raw is not None else None
        except ValueError:
            return None

    def _backoff(self, attempt: int, exc: Exception) -> float:
        hinted = self._retry_after(exc)
        wait = hinted if hinted is not None else 1.0 * 2 ** (attempt - 1)
        return min(max(wait, 0.0), config.LLM_MAX_RETRY_WAIT_S)


def get_default_client() -> LLMClient | None:
    """A GroqClient if an API key is configured, else None (callers fall back)."""
    if not config.settings.groq_api_key:
        return None
    return GroqClient()
