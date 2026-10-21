"""Typed exceptions for the recommendation pipeline."""


class LLMError(RuntimeError):
    """The LLM call failed (network, auth, rate limit, timeout, bad request)."""


class ParseError(ValueError):
    """The LLM answered, but not with usable, grounded recommendations."""
