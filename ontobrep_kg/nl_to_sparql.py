"""Phase 2 — NL question -> SPARQL.

Builds the system prompt from prompts/nl_to_sparql.system.txt by substituting:
  {MODEL_GRAPH_IRI}         the target named graph
  {ONTOBREP_SCHEMA_EXCERPT} references/ontobrep_reference.md section 1
  {CONCEPT_DEFINITIONS}     references/ontobrep_reference.md section 3
prepends few-shot examples from prompts/nl_to_sparql.fewshot.md, calls the LLM at
temperature 0.0, then strips fences/reasoning to return a bare SPARQL string.

See references/prompt_templates.md (A) and references/ontobrep_reference.md.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import llm

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
REFS = Path(__file__).resolve().parent.parent / "references"

_SPARQL_START = re.compile(r"(PREFIX|SELECT|ASK|CONSTRUCT|DESCRIBE)\b", re.IGNORECASE)


def _slice_section(path: Path, number: int) -> str:
    """Extract the markdown body of section `## {number}. ...` up to the next
    `## ` heading (or end of file)."""
    lines = path.read_text().splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith(f"## {number}."):
            start = i + 1
            break
    if start is None:
        return ""
    out = []
    for ln in lines[start:]:
        if ln.startswith("## ") and not ln.startswith(f"## {number}."):
            break
        out.append(ln)
    return "\n".join(out).strip() + "\n"


def _build_system(model_graph_iri: str) -> str:
    tmpl = (PROMPTS / "nl_to_sparql.system.txt").read_text()
    schema = _slice_section(REFS / "ontobrep_reference.md", 1)  # class schema
    concepts = _slice_section(REFS / "ontobrep_reference.md", 3)  # concept defs
    return (
        tmpl.replace("{MODEL_GRAPH_IRI}", model_graph_iri)
        .replace("{ONTOBREP_SCHEMA_EXCERPT}", schema)
        .replace("{CONCEPT_DEFINITIONS}", concepts)
    )


def _clean(raw: str) -> str:
    """Extract just the SPARQL from a model completion.

    Models often wrap the query in ```sparql fences, and may emit chain-of-thought
    BEFORE and/or AFTER the query. We:
      1. prefer a fenced block that actually looks like SPARQL,
      2. cut from the first PREFIX/SELECT/... keyword,
      3. cut at the LAST '}' so any trailing prose is dropped (SPARQL ends in '}').
    """
    raw = raw.replace("```sparql", "```")
    if "```" in raw:
        segments = [s.strip() for s in raw.split("```")]
        sparql_segs = [s for s in segments
                       if _SPARQL_START.search(s)]
        if sparql_segs:
            raw = max(sparql_segs, key=len)  # the SPARQL-bearing fence, not prose
    m = _SPARQL_START.search(raw)
    if m:
        raw = raw[m.start():]
    last_brace = raw.rfind("}")
    if last_brace != -1:
        raw = raw[:last_brace + 1]
    return raw.strip()


def nl_to_sparql(question: str, model_graph_iri: str) -> str:
    system = _build_system(model_graph_iri)
    fewshot = (PROMPTS / "nl_to_sparql.fewshot.md").read_text()
    user = f"{fewshot}\n\n# Now translate this question:\n{question}"
    return _clean(llm.chat(system, user, temperature=0.0))
