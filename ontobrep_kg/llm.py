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

# Timeouts. "Thinking" models (Qwen3, Gemini 2.5) reason before answering and can take
# 40-60s on a big prompt, so the primary timeout must be generous — a truly dead server
# still fails instantly (connection refused), this only caps a slow/hung one.
_PRIMARY_TIMEOUT = 150.0
_FALLBACK_TIMEOUT = 120.0

_primary_client = None
_fallback_client = None
_primary_dead = False   # latched True after the primary first fails this session
_last_used = "none"     # which backend served the most recent chat() call


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
              temperature: float, max_tokens: int, think_prefill: str = "") -> str:
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    # Prefill an (empty) reasoning block so a "thinking" model continues AFTER it and
    # skips the expensive reasoning phase — ~20x faster for Qwen3-style local models.
    if think_prefill.strip():
        messages.append({"role": "assistant", "content": think_prefill})
    kwargs = dict(
        model=model,
        messages=messages,
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


def chat(system: str, user: str, temperature: float = 0.0, max_tokens: int = 4096) -> str:
    """Single-turn completion. Try primary, fall back to secondary if primary fails.

    temperature=0.0 for deterministic SPARQL generation. max_tokens defaults high (4096)
    because "thinking" models spend ~2000 tokens reasoning BEFORE the answer — too small
    a budget and the query is empty/truncated (all tokens consumed by thinking).
    """
    global _primary_dead, _last_used

    if not _primary_dead:
        try:
            out = _complete(_primary(), CFG.llm_model, CFG.llm_reasoning_effort,
                            system, user, temperature, max_tokens, CFG.llm_think_prefill)
            _last_used = f"primary:{CFG.llm_model}"
            return out
        except Exception as e:
            if not CFG.has_fallback:
                raise
            _primary_dead = True
            print(f"[llm] primary unavailable ({type(e).__name__}); "
                  f"falling back to {CFG.llm_fallback_model}.", file=sys.stderr)

    if not CFG.has_fallback:
        raise RuntimeError("Primary LLM failed and no fallback is configured "
                           "(set GRAPHRAG_LLM_FALLBACK_*).")
    out = _complete(_fallback(), CFG.llm_fallback_model, CFG.llm_fallback_reasoning_effort,
                    system, user, temperature, max_tokens, CFG.llm_fallback_think_prefill)
    _last_used = f"fallback:{CFG.llm_fallback_model}"
    return out


def last_backend() -> str:
    """Backend that served the MOST RECENT chat() call (e.g. 'primary:<model>')."""
    return _last_used


def active_backend() -> str:
    """Which backend the next call will use — handy for logging/eval."""
    if _primary_dead and CFG.has_fallback:
        return f"fallback:{CFG.llm_fallback_model}"
    return f"primary:{CFG.llm_model}"
