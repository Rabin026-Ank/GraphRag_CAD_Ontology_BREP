"""OpenAI-compatible chat wrapper (works with a local vLLM or any OpenAI-compatible API).

Model + endpoint + key come from env (config.py). Swap models by changing env vars only.
The OpenAI client is constructed lazily (on first chat()) so importing this module does
not require the LLM env vars to be set — useful for CLI paths that don't call the LLM.
"""
from __future__ import annotations

from openai import OpenAI

from .config import CFG

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=CFG.llm_base_url, api_key=CFG.llm_api_key)
    return _client


def chat(system: str, user: str, temperature: float = 0.0, max_tokens: int = 2048) -> str:
    """Single-turn chat completion. temperature=0.0 for deterministic SPARQL generation."""
    resp = _get_client().chat.completions.create(
        model=CFG.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""
