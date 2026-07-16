"""Phase 2 — SPARQL result JSON -> natural-language answer.

Instructs the LLM to (1) rephrase the question, (2) state thoughts, (3) give the answer.
On empty result: say info could not be retrieved and why; never fabricate values.
See references/prompt_templates.md (B).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import llm

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def generate_answer(question: str, sparql: str, result_json: dict[str, Any]) -> str:
    system = (PROMPTS / "answer_gen.system.txt").read_text()
    user = (
        f"QUESTION:\n{question}\n\n"
        f"SPARQL:\n{sparql}\n\n"
        f"RESULT (JSON):\n{json.dumps(result_json, indent=2)[:8000]}"
    )
    return llm.chat(system, user, temperature=0.2)
