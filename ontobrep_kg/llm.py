"""LLM wrapper with primary→fallback failover (OpenAI-compatible endpoints).

Policy: prefer the PRIMARY LLM (e.g. the local vLLM — best privacy, unlimited). If the
primary is unreachable/errors, transparently fall back to the FALLBACK LLM (e.g. free
Gemini) so the pipeline keeps working when the local server is down.

Once the primary fails in a process, it is skipped for the rest of the session (so we
don't pay a connection timeout on every call). Set GRAPHRAG_LLM_* for the primary and
GRAPHRAG_LLM_FALLBACK_* for the fallback (config.py). No fallback configured → primary
only. Clients are built lazily so importing this module needs no env vars.
"""
from __future__ import annotations

import sys

from openai import OpenAI

from .config import CFG

# Fail fast on a dead local server instead of hanging (connection refused is instant;
# this caps a hung/slow primary).
_PRIMARY_TIMEOUT = 20.0
_FALLBACK_TIMEOUT = 60.0

_primary_client = None
_fallback_client = None
_primary_dead = False   # latched True after the primary first fails this session


def _primary() -> OpenAI:
    global _primary_client
    if _primary_client is None:
        _primary_client = OpenAI(base_url=CFG.llm_base_url, api_key=CFG.llm_api_key,
                                 timeout=_PRIMARY_TIMEOUT)
    return _primary_client


def _fallback() -> OpenAI:
    global _fallback_client
    if _fallback_client is None:
        _fallback_client = OpenAI(base_url=CFG.llm_fallback_base_url,
                                  api_key=CFG.llm_fallback_api_key, timeout=_FALLBACK_TIMEOUT)
    return _fallback_client


def _complete(client: OpenAI, model: str, effort: str, system: str, user: str,
              temperature: float, max_tokens: int) -> str:
    kwargs = dict(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    effort = (effort or "").strip()
    if effort:
        try:
            resp = client.chat.completions.create(reasoning_effort=effort, **kwargs)
            return resp.choices[0].message.content or ""
        except Exception:
            pass  # provider rejects reasoning_effort — retry without it
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat(system: str, user: str, temperature: float = 0.0, max_tokens: int = 2048) -> str:
    """Single-turn completion. Try primary, fall back to secondary if primary fails.

    temperature=0.0 for deterministic SPARQL generation.
    """
    global _primary_dead

    if not _primary_dead:
        try:
            return _complete(_primary(), CFG.llm_model, CFG.llm_reasoning_effort,
                             system, user, temperature, max_tokens)
        except Exception as e:
            if not CFG.has_fallback:
                raise
            _primary_dead = True
            print(f"[llm] primary unavailable ({type(e).__name__}); "
                  f"falling back to {CFG.llm_fallback_model}.", file=sys.stderr)

    if not CFG.has_fallback:
        raise RuntimeError("Primary LLM failed and no fallback is configured "
                           "(set GRAPHRAG_LLM_FALLBACK_*).")
    return _complete(_fallback(), CFG.llm_fallback_model, CFG.llm_fallback_reasoning_effort,
                     system, user, temperature, max_tokens)


def active_backend() -> str:
    """Which backend the next call will use — handy for logging/eval."""
    if _primary_dead and CFG.has_fallback:
        return f"fallback:{CFG.llm_fallback_model}"
    return f"primary:{CFG.llm_model}"
