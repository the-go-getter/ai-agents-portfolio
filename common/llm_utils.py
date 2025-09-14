"""
Small, reusable helper around the OpenAI Chat Completions API.

Why have this?
- So every service calls LLMs the same way (one import, one function).
- Central place to set defaults (model, temperature, timeouts, retries).
- Easy to swap providers later (Anthropic, Azure OpenAI, etc.) without touching callers.

Environment (all optional):
  OPENAI_API_KEY     = sk-...                # required only when not in mock mode
  OPENAI_MODEL       = gpt-4o-mini           # default model
  OPENAI_TIMEOUT_S   = 30                    # request timeout (seconds)
  OPENAI_MAX_RETRIES = 2                     # number of retry attempts on transient errors
  OPENAI_BASE_URL    = https://api.openai.com/v1   # override for Azure/OpenAI proxy etc.
  OPENAI_OFFLINE     = 0/1                  # when "1", return deterministic mock (no network)

Usage (sync):
    from common.llm_utils import complete
    code = complete("Generate a Playwright test")

Usage (async):
    from common.llm_utils import acomplete
    code = await acomplete("Generate a Playwright test")
"""

from __future__ import annotations

import os
from typing import Any, Optional, Dict, List
from pathlib import Path
from dotenv import load_dotenv

# ------------------------------
# Environment & configuration
# ------------------------------

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT / ".env", override=True)

USE_MOCK: bool = os.getenv("OPENAI_OFFLINE", "0") == "1"
# DEFAULT_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_TIMEOUT_S: float = float(os.getenv("OPENAI_TIMEOUT_S", "30"))
DEFAULT_MAX_RETRIES: int = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL") or None

# Cached clients (lazy init). We keep these None until actually needed.
_client = None
_async_client = None

__all__ = ["complete", "acomplete"]


# ------------------------------
# Client constructors (lazy)
# ------------------------------

def _get_client():
    """
    Lazily construct and cache the OpenAI sync client.
    Imported inside the function so module import remains cheap and test-friendly.
    """
    global _client
    if USE_MOCK:
        return None
    if _client is not None:
        return _client

    # Local import to avoid import-time dependency in mock mode
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Put it in .env or set the env var.")

    _client = OpenAI(api_key=api_key, base_url=BASE_URL)
    return _client


def _get_async_client():
    """
    Lazily construct and cache the OpenAI async client.
    """
    global _async_client
    if USE_MOCK:
        return None
    if _async_client is not None:
        return _async_client

    from openai import AsyncOpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Put it in .env or set the env var.")

    _async_client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL)
    return _async_client


# ------------------------------
# Retry helpers (sync + async)
# ------------------------------

def _retryable_exceptions():
    """
    Return tuple of exceptions considered transient (OK to retry).
    Imported lazily to avoid heavy imports at module load.
    """
    from openai import APIConnectionError, APITimeoutError, RateLimitError, APIError
    # AuthenticationError is NOT retryable.
    return (APIConnectionError, APITimeoutError, RateLimitError, APIError)


# ------------------------------
# Offline mock (used by tests)
# ------------------------------

_MOCK_TS_SNIPPET = (
    "import { test, expect } from '@playwright/test';\n\n"
    "test.describe('generated suite', () => {\n"
    "  test('generated', async ({ page }) => {\n"
    "    await page.goto('https://example.com');\n"
    "    await expect(page).toHaveTitle(/Example/);\n"
    "  });\n"
    "});\n"
)


# ------------------------------
# Public APIs
# ------------------------------

def complete(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    *,
    model: str = DEFAULT_MODEL,
    temperature: Optional[float] = 0.2,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_retries: int = DEFAULT_MAX_RETRIES,
    extra_messages: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> str:
    """
    Synchronous completion helper.

    Parameters
    ----------
    user_prompt : str
        Main user instruction/content.
    system_prompt : Optional[str]
        Optional system message (persona/constraints).
    model : str
        Model to use (default from env).
    temperature : Optional[float]
        Temperature to pass; set None to omit.
    timeout_s : float
        Per-request timeout in seconds.
    max_retries : int
        Number of retry attempts on transient errors.
    extra_messages : Optional[List[Dict[str, Any]]]
        Extra messages to prepend/append (advanced).

    Returns
    -------
    str
        The assistant message content.
    """
    if USE_MOCK:
        return _MOCK_TS_SNIPPET

    client = _get_client()
    # Bind timeout per request without mutating the global client
    client_req = client.with_options(timeout=timeout_s)

    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

    @retry(
        reraise=True,
        stop=stop_after_attempt(max_retries + 1),            # attempts = 1 + retries
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(_retryable_exceptions()),
    )
    def _do_request() -> str:
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user_prompt})

        resp = client_req.chat.completions.create(
            model=model,
            messages=messages,
            **{k: v for k, v in kwargs.items() if v is not None},
            **({"temperature": temperature} if temperature is not None else {}),
        )
        return resp.choices[0].message.content

    return _do_request()


async def acomplete(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    *,
    model: str = DEFAULT_MODEL,
    temperature: Optional[float] = 0.2,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_retries: int = DEFAULT_MAX_RETRIES,
    extra_messages: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> str:
    """
    Asynchronous completion helper.

    Mirrors `complete` but uses `AsyncOpenAI` and async tenacity retry.
    """
    if USE_MOCK:
        return _MOCK_TS_SNIPPET

    client = _get_async_client()
    client_req = client.with_options(timeout=timeout_s)

    # Async retry: import inside to avoid top-level dependency
    from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential, retry_if_exception_type

    async for attempt in AsyncRetrying(
        reraise=True,
        stop=stop_after_attempt(max_retries + 1),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(_retryable_exceptions()),
    ):
        with attempt:
            messages: List[Dict[str, Any]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if extra_messages:
                messages.extend(extra_messages)
            messages.append({"role": "user", "content": user_prompt})

            resp = await client_req.chat.completions.create(
                model=model,
                messages=messages,
                **{k: v for k, v in kwargs.items() if v is not None},
                **({"temperature": temperature} if temperature is not None else {}),
            )
            return resp.choices[0].message.content
